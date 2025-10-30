"""
Contract generation service.
Handles placeholder replacement and document generation from templates.
"""
from .google_drive import GoogleDriveService
from googleapiclient.discovery import build
from google.oauth2 import service_account
from decouple import config
import tempfile
import os
import re
from datetime import date


class ContractGeneratorService:
    """
    Service for generating contracts from templates with placeholder replacement.
    """

    def __init__(self):
        self.drive_service = GoogleDriveService()

        # Initialize Google Docs API for document manipulation
        service_account_file = config('GOOGLE_SERVICE_ACCOUNT_FILE', default='service-account.json')
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=[
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/documents'
            ]
        )
        self.docs_service = build('docs', 'v1', credentials=credentials)

    def analyze_commission_patterns(self, commission_by_year, enabled_rights):
        """
        Analyze year-by-year commission data to detect uniform vs split patterns.

        For each rights category, determines if commissions are:
        - UNIFORM: Same rate all years → sets category_uniform=1
        - SPLIT: Different rates → groups into first_years and last_years

        Args:
            commission_by_year: Dict of {year_str: {category: rate_str}}
                Example: {"1": {"concert": "20", "rights": "25"}, "2": {...}, ...}
            enabled_rights: Dict of {category: boolean}
                Example: {"concert": True, "rights": False, ...}

        Returns:
            Dict of placeholder values:
                - has_{category}_rights: 1 if enabled, 0 if disabled
                - {category}_uniform: 1 if uniform, 0 if split
                - {category}_first_years: number of years in first period (0 if uniform)
                - {category}_last_years: number of years in last period (0 if uniform)
                - commission.{category}.uniform: rate if uniform
                - commission.{category}.first_years: rate for first period if split
                - commission.{category}.last_years: rate for last period if split
        """
        import logging
        logger = logging.getLogger(__name__)

        placeholders = {}

        # Get all years sorted
        years = sorted([int(y) for y in commission_by_year.keys()])
        total_years = len(years)

        logger.info(f"Analyzing commission patterns for {total_years} years: {years}")

        # Categories to analyze
        categories = ['concert', 'image_rights', 'rights', 'merchandising', 'ppd', 'emd', 'sync']

        for category in categories:
            # Check if this rights category is enabled
            if not enabled_rights.get(category, True):
                placeholders[f'has_{category}_rights'] = 0
                logger.info(f"Category '{category}' is disabled")
                continue

            placeholders[f'has_{category}_rights'] = 1

            # Get all rates for this category across years
            try:
                rates = [float(commission_by_year[str(year)].get(category, 0)) for year in years]
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Error parsing rates for category '{category}': {e}. Using defaults.")
                rates = [0.0] * total_years

            logger.info(f"Category '{category}' rates by year: {rates}")

            # Check if all rates are identical (uniform)
            unique_rates = set(rates)
            if len(unique_rates) == 1:
                # UNIFORM MODE - all years have same rate
                placeholders[f'{category}_uniform'] = 1
                placeholders[f'{category}_first_years'] = 0
                placeholders[f'{category}_last_years'] = 0
                placeholders[f'commission.{category}.uniform'] = rates[0]
                logger.info(f"  → UNIFORM: {rates[0]}% for all {total_years} years")

            else:
                # SPLIT MODE - find where rate changes
                placeholders[f'{category}_uniform'] = 0

                first_rate = rates[0]
                split_index = 1

                # Find where first rate ends (consecutive years with same rate)
                for i in range(1, len(rates)):
                    if rates[i] != first_rate:
                        split_index = i
                        break

                # First period: years 1 to split_index
                first_years_count = split_index
                first_years_rate = first_rate

                # Last period: remaining years (use rate from split point)
                last_years_count = total_years - split_index
                last_years_rate = rates[split_index]

                placeholders[f'{category}_first_years'] = first_years_count
                placeholders[f'{category}_last_years'] = last_years_count
                placeholders[f'commission.{category}.first_years'] = first_years_rate
                placeholders[f'commission.{category}.last_years'] = last_years_rate

                logger.info(f"  → SPLIT: First {first_years_count} years @ {first_years_rate}%, Last {last_years_count} years @ {last_years_rate}%")

        return placeholders

    def _process_conditional_sections(self, document_text, placeholder_values):
        """
        Process conditional sections marked with {{BEGIN:name}}...{{END:name}}.

        If the referenced placeholder value is 0, False, empty string, or None,
        the entire section (including markers) is removed from the document.
        Otherwise, the section content is kept and only the markers are removed.

        Args:
            document_text: The full document text
            placeholder_values: Dict of all placeholder values

        Returns:
            Document text with conditional sections processed
        """
        import logging
        logger = logging.getLogger(__name__)

        # Pattern: {{BEGIN:variable_name}} ... {{END:variable_name}}
        # DOTALL makes . match newlines, so we can capture multi-line sections
        section_pattern = re.compile(
            r'\{\{\s*BEGIN\s*:\s*([a-zA-Z0-9_]+)\s*\}\}(.*?)\{\{\s*END\s*:\s*\1\s*\}\}',
            re.DOTALL | re.IGNORECASE
        )

        def replace_section(match):
            variable_name = match.group(1)
            section_content = match.group(2)

            # Get the value of the variable
            value = placeholder_values.get(variable_name, 0)

            # Convert to number to check if it's 0
            try:
                if isinstance(value, str):
                    numeric_value = float(value) if value else 0
                else:
                    numeric_value = float(value) if value is not None else 0
            except (ValueError, TypeError):
                # If can't convert, treat as boolean
                numeric_value = 1 if value else 0

            # If value is 0, False, empty, or None → hide section (return empty string)
            if numeric_value == 0 or value is None or value == '' or value is False:
                logger.info(f"Hiding conditional section '{variable_name}' (value={value})")
                return ''

            # Otherwise, show section but remove BEGIN/END markers
            logger.info(f"Showing conditional section '{variable_name}' (value={value})")
            return section_content

        # Replace all conditional sections
        result = section_pattern.sub(replace_section, document_text)

        # Check for unclosed sections (debugging aid)
        open_sections = re.findall(r'\{\{\s*BEGIN\s*:\s*([a-zA-Z0-9_]+)\s*\}\}', result)
        closed_sections = re.findall(r'\{\{\s*END\s*:\s*([a-zA-Z0-9_]+)\s*\}\}', result)

        for section in open_sections:
            if section not in closed_sections or open_sections.count(section) != closed_sections.count(section):
                logger.warning(f"Potentially unclosed section: BEGIN:{section}")

        return result

    def generate_contract(
        self,
        template_file_id,
        output_folder_id,
        output_file_name,
        placeholder_values
    ):
        """
        Generate a contract from a template by replacing placeholders.

        Supports advanced features:
        - Commission pattern analysis (year-by-year rates → uniform/split detection)
        - Conditional sections ({{BEGIN:name}}...{{END:name}})
        - Gender placeholders ({{entity.gender:masculine:feminine}})
        - Phrase placeholders with pluralization ({{var.phrase:singular {n}:plural {n}}})
        - Date placeholders ({{today}}, {{today.iso}}, {{today.long}})

        Args:
            template_file_id: Google Drive file ID of the template
            output_folder_id: Google Drive folder ID where contract will be saved
            output_file_name: Name for the generated contract
            placeholder_values: Dict of placeholder key-value pairs
                Special keys:
                - commission_by_year: Dict of {year: {category: rate}}
                - enabled_rights: Dict of {category: boolean}

        Returns:
            Dict with file_id and web_view_link of the generated contract
        """
        import logging
        logger = logging.getLogger(__name__)

        # Step 1: Copy the template to create a new document
        copy_result = self.drive_service.copy_file(
            file_id=template_file_id,
            new_name=output_file_name,
            folder_id=output_folder_id
        )

        new_file_id = copy_result['file_id']

        # Step 2: Read document content (needed for pattern analysis)
        logger.info("Reading document content...")
        doc_text = self.get_document_text(new_file_id)

        # Step 3: Analyze commission patterns if year-by-year data provided
        all_placeholders = placeholder_values.copy()

        if 'commission_by_year' in placeholder_values:
            commission_by_year = placeholder_values.get('commission_by_year', {})
            enabled_rights = placeholder_values.get('enabled_rights', {})

            logger.info("Analyzing commission patterns from year-by-year data...")
            analyzed_placeholders = self.analyze_commission_patterns(
                commission_by_year,
                enabled_rights
            )

            # Merge analyzed placeholders into main placeholder dict
            all_placeholders.update(analyzed_placeholders)
            logger.info(f"Added {len(analyzed_placeholders)} analyzed placeholders")

        # Step 4: Process conditional sections (BEGIN/END)
        logger.info("Processing conditional sections...")
        doc_text_after_sections = self._process_conditional_sections(doc_text, all_placeholders)

        # Step 5: Process special placeholders (gender, dates, phrases)
        logger.info("Processing special placeholders (gender, dates, phrases)...")
        final_placeholders = self._process_special_placeholders(doc_text_after_sections, all_placeholders)

        # Step 6: Replace all standard placeholders in the document
        logger.info(f"Replacing {len(final_placeholders)} placeholders...")
        self._replace_placeholders(new_file_id, final_placeholders)

        # Step 7: Return the new document details
        logger.info("Contract generation completed successfully")
        return copy_result

    def _process_special_placeholders(self, document_text, placeholder_values):
        """
        Process special placeholders like gender placeholders and date placeholders.

        Args:
            document_text: The full text content of the document
            placeholder_values: Original placeholder dict

        Returns:
            Updated placeholder dict with gender placeholders resolved
        """
        import logging
        logger = logging.getLogger(__name__)

        # Make a copy to avoid modifying original
        processed = placeholder_values.copy()

        # Add today's date placeholder
        today = date.today()
        processed['today'] = today.strftime('%d.%m.%Y')  # Romanian format: 30.10.2025
        processed['today.iso'] = today.strftime('%Y-%m-%d')  # ISO format: 2025-10-30
        processed['today.long'] = today.strftime('%d %B %Y')  # Long format with month name

        # Get entity gender from placeholder values
        entity_gender = placeholder_values.get('entity.gender') or placeholder_values.get('gender')

        if not entity_gender:
            logger.warning("No entity gender found in placeholders, gender placeholders may not work correctly")
            return processed

        # Gender placeholder pattern: {{entity.gender:masculine:feminine}} or {{entity.gender:masculine:feminine:neuter}}
        # Pattern supports both with and without spaces
        gender_pattern = re.compile(
            r'\{\{\s*entity\.gender\s*:\s*([^:}]+)\s*:\s*([^:}]+)\s*(?::\s*([^}]+))?\s*\}\}',
            re.IGNORECASE
        )

        # Find all gender placeholders in document
        matches = gender_pattern.findall(document_text)

        logger.info(f"Found {len(matches)} gender placeholders in document")

        for match in matches:
            masculine = match[0].strip()
            feminine = match[1].strip()
            neuter = match[2].strip() if match[2] else masculine  # Default to masculine if neuter not provided

            # Select word based on gender
            if entity_gender == 'M':
                selected_word = masculine
            elif entity_gender == 'F':
                selected_word = feminine
            else:  # 'O' or missing -> use neuter (or masculine if only 2 forms)
                selected_word = neuter

            # Create placeholder key for this specific gender placeholder
            # We need to reconstruct the exact placeholder to replace it
            if match[2]:  # 3 forms
                placeholder_key = f"entity.gender:{masculine}:{feminine}:{neuter}"
            else:  # 2 forms
                placeholder_key = f"entity.gender:{masculine}:{feminine}"

            processed[placeholder_key] = selected_word

            logger.info(f"Gender placeholder '{placeholder_key}' -> '{selected_word}' (gender={entity_gender})")

        # Process phrase placeholders with pluralization
        # Pattern: {{variable.phrase:singular {n}:plural {n}}}
        # The {n} will be replaced with the actual number value
        phrase_pattern = re.compile(
            r'\{\{\s*([a-zA-Z0-9_]+)\.phrase\s*:\s*([^:}]+)\s*:\s*([^}]+)\s*\}\}',
            re.IGNORECASE
        )

        phrase_matches = phrase_pattern.findall(document_text)

        logger.info(f"Found {len(phrase_matches)} phrase placeholders in document")

        for match in phrase_matches:
            variable_name = match[0].strip()
            singular_phrase = match[1].strip()
            plural_phrase = match[2].strip()

            # Get the numeric value
            value = placeholder_values.get(variable_name, 0)
            try:
                numeric_value = int(float(value)) if value else 0
            except (ValueError, TypeError):
                logger.warning(f"Could not convert '{variable_name}' value '{value}' to number, using 0")
                numeric_value = 0

            # Select phrase based on value (1 = singular, anything else = plural)
            if numeric_value == 1:
                selected_phrase = singular_phrase
            else:
                selected_phrase = plural_phrase

            # Replace {n} with actual number in the selected phrase
            selected_phrase = selected_phrase.replace('{n}', str(numeric_value))

            # Create placeholder key for this specific phrase placeholder
            # We need to match the exact pattern in the document
            placeholder_key = f"{variable_name}.phrase:{singular_phrase}:{plural_phrase}"
            processed[placeholder_key] = selected_phrase

            logger.info(f"Phrase placeholder '{variable_name}.phrase' -> '{selected_phrase}' (value={numeric_value})")

        return processed

    def _replace_placeholders(self, document_id, placeholder_values):
        """
        Replace placeholders in a Google Docs document.

        Args:
            document_id: Google Docs document ID
            placeholder_values: Dict of placeholder key-value pairs
        """
        import logging
        logger = logging.getLogger(__name__)

        requests = []

        # Build replacement requests for each placeholder
        for key, value in placeholder_values.items():
            replacement_value = str(value) if value is not None else ''

            # Strip braces from key if they were included (handle incorrect template definitions)
            clean_key = key.strip('{}').strip()

            # Try multiple placeholder formats to handle different spacing
            # Format 1: {{key}} (no spaces)
            placeholder_no_space = f"{{{{{clean_key}}}}}"

            # Format 2: {{ key }} (with spaces)
            placeholder_with_space = f"{{{{ {clean_key} }}}}"

            logger.info(f"Replacing placeholder '{placeholder_no_space}' (and variants) with value '{replacement_value}'")

            # Add replacement for both formats
            for placeholder_format in [placeholder_no_space, placeholder_with_space]:
                requests.append({
                    'replaceAllText': {
                        'containsText': {
                            'text': placeholder_format,
                            'matchCase': False
                        },
                        'replaceText': replacement_value
                    }
                })

        # Log the requests being sent
        logger.info(f"Sending {len(requests)} replacement requests to Google Docs API")
        logger.debug(f"Replacement requests: {requests}")

        # Execute all replacements in a single batch
        if requests:
            try:
                result = self.docs_service.documents().batchUpdate(
                    documentId=document_id,
                    body={'requests': requests}
                ).execute()
                logger.info(f"Successfully replaced placeholders. Result: {result}")
                logger.info(f"Replies from API: {result.get('replies', [])}")
            except Exception as e:
                logger.error(f"Error replacing placeholders: {str(e)}")
                raise

    def get_document_text(self, document_id):
        """
        Retrieve all text content from a Google Docs document.
        Useful for debugging placeholder issues.

        Args:
            document_id: Google Docs document ID

        Returns:
            String containing all document text
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            document = self.docs_service.documents().get(documentId=document_id).execute()
            doc_content = document.get('body', {}).get('content', [])

            text_parts = []
            for element in doc_content:
                if 'paragraph' in element:
                    for text_run in element['paragraph'].get('elements', []):
                        if 'textRun' in text_run:
                            text_parts.append(text_run['textRun'].get('content', ''))

            full_text = ''.join(text_parts)
            logger.info(f"Document text preview (first 500 chars): {full_text[:500]}")
            return full_text
        except Exception as e:
            logger.error(f"Error reading document text: {str(e)}")
            return ""

    def export_as_pdf(self, document_id, output_path=None):
        """
        Export a Google Docs document as PDF.

        Args:
            document_id: Google Docs document ID
            output_path: Optional local path to save PDF

        Returns:
            PDF content as bytes
        """
        # Export document as PDF
        pdf_content = self.drive_service.service.files().export(
            fileId=document_id,
            mimeType='application/pdf'
        ).execute()

        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_content)

        return pdf_content

    def generate_contract_with_pdf(
        self,
        template_file_id,
        output_folder_id,
        output_file_name,
        placeholder_values
    ):
        """
        Generate a contract and also create a PDF version.

        Args:
            template_file_id: Google Drive file ID of the template
            output_folder_id: Google Drive folder ID where contract will be saved
            output_file_name: Name for the generated contract
            placeholder_values: Dict of placeholder key-value pairs

        Returns:
            Dict with docs_file_id, docs_web_link, pdf_file_id, pdf_web_link
        """
        # Generate the contract (Google Docs)
        docs_result = self.generate_contract(
            template_file_id=template_file_id,
            output_folder_id=output_folder_id,
            output_file_name=output_file_name,
            placeholder_values=placeholder_values
        )

        # Export as PDF
        pdf_content = self.export_as_pdf(docs_result['file_id'])

        # Upload PDF to Google Drive
        pdf_result = self.drive_service.upload_file_content(
            content=pdf_content,
            file_name=f"{output_file_name}.pdf",
            folder_id=output_folder_id,
            mime_type='application/pdf'
        )

        return {
            'docs_file_id': docs_result['file_id'],
            'docs_web_link': docs_result['web_view_link'],
            'pdf_file_id': pdf_result['file_id'],
            'pdf_web_link': pdf_result['web_view_link']
        }
