"""
ONE-TIME SCRIPT: Add placeholders to contract template

This script reads a Google Doc contract template and creates a copy with placeholders.
After use, this file can be safely deleted.

Usage:
    python contracts/TEMP_add_placeholders_to_contract.py

Author: Claude Code
Date: 2025-10-30
"""

import os
import sys
import django

# Setup Django environment
sys.path.append('/home/ioan/projects/HaOS/stack/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from contracts.services.google_drive import GoogleDriveService
from google.oauth2 import service_account
from googleapiclient.discovery import build
from decouple import config
import re


class ContractPlaceholderAdder:
    """Analyzes contract text and adds appropriate placeholders."""

    def __init__(self):
        self.drive_service = GoogleDriveService()

        # Build Docs API service
        service_account_file = config('GOOGLE_SERVICE_ACCOUNT_FILE', default='service-account.json')
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
        )
        self.docs_service = build('docs', 'v1', credentials=credentials)

    def get_document_text(self, doc_id):
        """Read full document text from Google Docs."""
        try:
            doc = self.docs_service.documents().get(documentId=doc_id).execute()
            content = doc.get('body').get('content')

            full_text = []
            for element in content:
                if 'paragraph' in element:
                    for elem in element['paragraph'].get('elements', []):
                        if 'textRun' in elem:
                            full_text.append(elem['textRun']['content'])

            return ''.join(full_text)
        except Exception as e:
            raise Exception(f'Error reading document: {e}')

    def analyze_and_add_placeholders(self, text):
        """
        Analyze contract text and replace hardcoded values with placeholders.

        This uses intelligent pattern matching to identify:
        - Entity names
        - Addresses
        - CNP/CI numbers
        - Dates
        - Commission rates with conditional sections
        - Contract terms
        """
        modified = text

        # Track changes for reporting
        changes = []

        # 1. Replace gender-specific words with gender placeholders
        gender_replacements = [
            (r'\bSubsemnatul\b', '{{entity.gender:Subsemnatul:Subsemnata}}', 'Gender: Subsemnatul/Subsemnata'),
            (r'\bnăscut\b', '{{entity.gender:născut:născută}}', 'Gender: născut/născută'),
            (r'\bdomiciliat\b', '{{entity.gender:domiciliat:domiciliată}}', 'Gender: domiciliat/domiciliată'),
            (r'\bidentificat\b', '{{entity.gender:identificat:identificată}}', 'Gender: identificat/identificată'),
            (r'\bdenumin\b', '{{entity.gender:denumit:denumită}}', 'Gender: denumit/denumită'),
            (r'\bAngajatul\b', '{{entity.gender:Angajatul:Angajata}}', 'Gender: Angajatul/Angajata'),
            (r'\bangajat\b', '{{entity.gender:angajat:angajată}}', 'Gender: angajat/angajată'),
        ]

        for pattern, replacement, desc in gender_replacements:
            if re.search(pattern, modified):
                modified = re.sub(pattern, replacement, modified)
                changes.append(desc)

        # 2. MOST IMPORTANT: Replace commission sections with conditional structures
        # Concert commissions
        concert_old_pattern = r'Pentru Veniturile din Concerte :\s+în primii 2 ani contractuali:.*?{{commission\.first_years\.concert}}.*?În \[ultimul\] 1 an/i contractual/i:.*?{{commission\.last_years\.concert}}.*?(?=\n\n|\Z)'

        if re.search(r'Pentru Veniturile din Concerte', modified, re.DOTALL):
            # Find the concert section
            concert_new = '''Pentru Veniturile din Concerte :

{{BEGIN:concert_uniform}}
Pe toată durata contractului: Întâi, se vor deduce Cheltuielile, daca acestea nu au fost asigurate de către Organizatorul de Evenimente.
Apoi, PRODUCATORUL va fi remunerat cu o sumă reprezentând un comision de {{commission.concert.uniform}}%.
Din diferența dintre Venitul încasat si comisionul PRODUCĂTORULUI, suma rămasă se va achita ARTISTULUI, urmând ca acesta din urma sa achite toate costurile legate de trupa, backline, tour manager, echipa tehnica, sunet, lumini, video sau orice alte costuri cu personal conex/promovare/de producție – necesare desfășurării evenimentului.
{{END:concert_uniform}}

{{BEGIN:concert_first_years}}
{{concert_first_years.phrase:În primul {n} an contractual:În primii {n} ani contractuali}}: Întâi, se vor deduce Cheltuielile, daca acestea nu au fost asigurate de către Organizatorul de Evenimente.
Apoi, PRODUCATORUL va fi remunerat cu o sumă reprezentând un comision de {{commission.concert.first_years}}%.
Din diferența dintre Venitul încasat si comisionul PRODUCĂTORULUI, suma rămasă se va achita ARTISTULUI, urmând ca acesta din urma sa achite toate costurile legate de trupa, backline, tour manager, echipa tehnica, sunet, lumini, video sau orice alte costuri cu personal conex/promovare/de producție – necesare desfășurării evenimentului.

{{concert_last_years.phrase:În ultimul {n} an contractual:În ultimii {n} ani contractuali}}: Întâi, se vor deduce Cheltuielile, daca acestea nu au fost asigurate de către Organizatorul de Evenimente.
Apoi, PRODUCĂTORUL va fi remunerat cu o sumă reprezentând un comision de {{commission.concert.last_years}}%.
Din diferența dintre Venitul încasat si comisionul PRODUCĂTORULUI, suma rămasă se va achita ARTISTULUI, urmând ca acesta din urma sa achite toate costurile legate de trupa, backline, tour manager, echipa tehnica, sunet, lumini, video sau orice alte costuri cu personal conex/promovare/de producție – necesare desfășurării evenimentului.
{{END:concert_first_years}}'''

            # Replace the concert section
            pattern = r'Pentru Veniturile din Concerte :.*?(?=\n\nPentru drepturi din|Pentru|ARTICOLUL|\Z)'
            modified = re.sub(pattern, concert_new + '\n\n', modified, flags=re.DOTALL)
            changes.append('✅ Commission: Added conditional sections for concert (uniform + split with phrase placeholders)')

        # PPD, EMD, Sync sections
        if re.search(r'{{commission\.first_years\.ppd}}', modified):
            ppd_new = '''{{BEGIN:has_ppd_rights}}
{{BEGIN:ppd_uniform}}
{{commission.ppd.uniform}}% din PPD-ul PRODUCĂTORULUI pentru fiecare Unitate fizica, incasata si nereturnata.
{{END:ppd_uniform}}
{{BEGIN:ppd_first_years}}
{{ppd_first_years.phrase:În primul {n} an contractual:În primii {n} ani contractuali}}: {{commission.ppd.first_years}}% din PPD-ul PRODUCĂTORULUI.
{{ppd_last_years.phrase:În ultimul {n} an contractual:În ultimii {n} ani contractuali}}: {{commission.ppd.last_years}}% din PPD-ul PRODUCĂTORULUI.
{{END:ppd_first_years}}
{{END:has_ppd_rights}}'''

            modified = re.sub(
                r'{{commission\.first_years\.ppd}}% din PPD-ul PRODUCĂTORULUI.*?(?=\n|;)',
                ppd_new,
                modified,
                flags=re.DOTALL
            )
            changes.append('✅ Commission: Added conditional sections for PPD (uniform + split)')

        if re.search(r'{{commission\.first_years\.emd}}', modified):
            emd_new = '''{{BEGIN:has_emd_rights}}
{{BEGIN:emd_uniform}}
În cazul veniturilor obținute din EMD: {{commission.emd.uniform}}% din venitul net încasat de PRODUCATOR de la terți.
{{END:emd_uniform}}
{{BEGIN:emd_first_years}}
{{emd_first_years.phrase:În primul {n} an contractual:În primii {n} ani contractuali}}: {{commission.emd.first_years}}% din venitul net EMD încasat.
{{emd_last_years.phrase:În ultimul {n} an contractual:În ultimii {n} ani contractuali}}: {{commission.emd.last_years}}% din venitul net EMD încasat.
{{END:emd_first_years}}
{{END:has_emd_rights}}'''

            modified = re.sub(
                r'{{commission\.first_years\.emd}}% din venitul net încasat.*?(?=\n|;)',
                emd_new,
                modified,
                flags=re.DOTALL
            )
            changes.append('✅ Commission: Added conditional sections for EMD (uniform + split)')

        if re.search(r'{{commission\.first_years\.sync}}', modified):
            sync_new = '''{{BEGIN:has_sync_rights}}
{{BEGIN:sync_uniform}}
Pentru sincronizare și publicitate: {{commission.sync.uniform}}% din venitul net încasat de PRODUCATOR.
{{END:sync_uniform}}
{{BEGIN:sync_first_years}}
{{sync_first_years.phrase:În primul {n} an contractual:În primii {n} ani contractuali}}: {{commission.sync.first_years}}% din venitul net din sincronizare.
{{sync_last_years.phrase:În ultimul {n} an contractual:În ultimii {n} ani contractuali}}: {{commission.sync.last_years}}% din venitul net din sincronizare.
{{END:sync_first_years}}
{{END:has_sync_rights}}'''

            modified = re.sub(
                r'{{commission\.first_years\.sync}}% din venitul net încasat.*?(?=\n|;|\.|$)',
                sync_new,
                modified,
                flags=re.DOTALL
            )
            changes.append('✅ Commission: Added conditional sections for Sync (uniform + split)')

        # Add merchandising section if it exists
        if re.search(r'Pentru drepturi din merchandising', modified):
            merchandising_new = '''{{BEGIN:has_merchandising_rights}}
Pentru drepturi din merchandising ARTIST:

{{BEGIN:merchandising_uniform}}
Pe toată durata contractului, PRODUCĂTORUL va primi {{commission.merchandising.uniform}}% din veniturile nete generate din vânzarea de produse de merchandising.
{{END:merchandising_uniform}}

{{BEGIN:merchandising_first_years}}
{{merchandising_first_years.phrase:În primul {n} an contractual:În primii {n} ani contractuali}}, PRODUCĂTORUL va primi {{commission.merchandising.first_years}}% din veniturile nete generate din vânzarea de produse de merchandising.

{{merchandising_last_years.phrase:În ultimul {n} an contractual:În ultimii {n} ani contractuali}}, PRODUCĂTORUL va primi {{commission.merchandising.last_years}}% din veniturile nete generate din vânzarea de produse de merchandising.
{{END:merchandising_first_years}}
{{END:has_merchandising_rights}}'''

            modified = re.sub(
                r'Pentru drepturi din merchandising.*?(?=\n\nPentru|ARTICOLUL|\Z)',
                merchandising_new + '\n\n',
                modified,
                flags=re.DOTALL
            )
            changes.append('✅ Commission: Added conditional sections for merchandising (uniform + split)')

        # 3. Update contract term placeholders
        modified = re.sub(r'{{contract\.duration_years}}', '{{contract_duration_years}}', modified)
        modified = re.sub(r'{{contract\.notice_period_days}}', '{{notice_period_days}}', modified)

        if '{{contract_duration_years}}' in modified:
            changes.append('✅ Contract Terms: Updated duration placeholder to {{contract_duration_years}}')
        if '{{notice_period_days}}' in modified:
            changes.append('✅ Contract Terms: Updated notice period placeholder to {{notice_period_days}}')

        # 4. Update investment placeholders
        modified = re.sub(r'{{contract\.minimum_launches}}', '{{minimum_launches_per_year}}', modified)
        modified = re.sub(r'{{investment\.per_song}}', '{{max_investment_per_song}}', modified)

        if '{{minimum_launches_per_year}}' in modified:
            changes.append('✅ Investment: Updated minimum launches placeholder')
        if '{{max_investment_per_song}}' in modified:
            changes.append('✅ Investment: Updated investment per song placeholder')

        return modified, changes

    def create_placeholder_version(self, source_doc_id, output_name=None, output_folder_id=None):
        """
        Read document from Google Drive and create a copy with placeholders.

        Args:
            source_doc_id: Google Drive document ID
            output_name: Name for the new document (default: original name + "_WITH_PLACEHOLDERS")
            output_folder_id: Google Drive folder ID to save the copy (shared drive folder)

        Returns:
            Dict with new file details
        """
        print(f"Reading source document: {source_doc_id}")

        # Get original document name
        file_meta = self.drive_service.get_file(source_doc_id)
        original_name = file_meta.get('name', 'Contract')

        if not output_name:
            output_name = f"{original_name}_WITH_PLACEHOLDERS"

        print(f"Original name: {original_name}")
        print(f"Output name: {output_name}")
        if output_folder_id:
            print(f"Output folder ID: {output_folder_id}")

        # Read document text
        print("\nReading document content...")
        text = self.get_document_text(source_doc_id)

        print(f"Document length: {len(text)} characters")
        print("\nFirst 500 characters:")
        print(text[:500])
        print("\n" + "="*80)

        # Analyze and add placeholders
        print("\nAnalyzing and adding placeholders...")
        modified_text, changes = self.analyze_and_add_placeholders(text)

        print(f"\nChanges made ({len(changes)}):")
        for i, change in enumerate(changes, 1):
            print(f"  {i}. {change}")

        # Copy the document to shared drive folder
        print(f"\nCreating copy in shared drive folder: {output_name}")
        copy_result = self.drive_service.copy_file(
            file_id=source_doc_id,
            new_name=output_name,
            folder_id=output_folder_id
        )

        new_file_id = copy_result['file_id']
        print(f"New file created: {new_file_id}")
        print(f"View at: {copy_result['web_view_link']}")

        # Replace text in the new document
        print("\nReplacing content with placeholder version...")
        self._replace_all_text(new_file_id, modified_text)

        print("\n" + "="*80)
        print("SUCCESS! Document with placeholders created.")
        print(f"URL: {copy_result['web_view_link']}")
        print("\nNEXT STEPS:")
        print("1. Review the document manually")
        print("2. Add conditional sections ({{BEGIN:...}}/{{END:...}}) for commission logic")
        print("3. Add phrase placeholders for year-based text")
        print("4. Test with entity data")
        print("\nYou can safely delete this script after use:")
        print("  rm contracts/TEMP_add_placeholders_to_contract.py")

        return copy_result

    def _replace_all_text(self, doc_id, new_text):
        """Replace all text in a Google Doc."""
        # Get the document to find the end index
        doc = self.docs_service.documents().get(documentId=doc_id).execute()

        # Get the last index of the document
        content = doc.get('body').get('content')
        end_index = content[-1].get('endIndex', 1) - 1

        # Build requests to delete all content and insert new
        requests = [
            {
                'deleteContentRange': {
                    'range': {
                        'startIndex': 1,
                        'endIndex': end_index,
                    }
                }
            },
            {
                'insertText': {
                    'location': {
                        'index': 1,
                    },
                    'text': new_text
                }
            }
        ]

        # Execute the batch update
        self.docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': requests}
        ).execute()


def main():
    """Main execution."""
    # Document ID from the URL
    SOURCE_DOC_ID = '1Pe2B7vnoH-KvYbW_IM7kyk3b4t1MNoZ3E8SQVNlFkwE'

    # Shared drive folder where all contract templates are stored
    # This folder ID is used by all ContractTemplate objects in the database
    OUTPUT_FOLDER_ID = '1TrdRta7xLadFV3vH7-tWZhFLo8ptJvAK'

    print("="*80)
    print("CONTRACT PLACEHOLDER ADDER - ONE-TIME SCRIPT")
    print("="*80)
    print()

    adder = ContractPlaceholderAdder()

    try:
        result = adder.create_placeholder_version(
            SOURCE_DOC_ID,
            output_folder_id=OUTPUT_FOLDER_ID
        )
        print("\n" + "="*80)
        print("DONE!")
        print("="*80)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
