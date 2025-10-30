"""
Unit tests for security utilities (data redaction and masking).
"""
from django.test import TestCase
from contracts.security_utils import (
    is_sensitive_field,
    redact_value,
    mask_email,
    redact_placeholder_values,
    redact_audit_changes,
    get_redaction_summary,
)


class SensitiveFieldDetectionTests(TestCase):
    """Tests for sensitive field pattern detection."""

    def test_detects_cnp_fields(self):
        """Should detect CNP-related field names (Romanian personal ID)."""
        self.assertTrue(is_sensitive_field('cnp'))
        self.assertTrue(is_sensitive_field('CNP'))  # Case insensitive
        self.assertTrue(is_sensitive_field('entity.cnp'))
        self.assertTrue(is_sensitive_field('artist_cnp'))

    def test_detects_bank_account_fields(self):
        """Should detect banking-related fields."""
        self.assertTrue(is_sensitive_field('bank_account'))
        self.assertTrue(is_sensitive_field('iban'))
        self.assertTrue(is_sensitive_field('entity.bank_account'))
        self.assertTrue(is_sensitive_field('entity.iban'))

    def test_detects_contact_information(self):
        """Should detect contact information fields."""
        self.assertTrue(is_sensitive_field('phone'))
        self.assertTrue(is_sensitive_field('entity.phone'))

    def test_detects_address_fields(self):
        """Should detect address fields."""
        self.assertTrue(is_sensitive_field('address'))
        self.assertTrue(is_sensitive_field('entity.address'))
        self.assertTrue(is_sensitive_field('city'))
        self.assertTrue(is_sensitive_field('zip_code'))

    def test_detects_passport_and_id_fields(self):
        """Should detect passport and ID fields."""
        self.assertTrue(is_sensitive_field('passport_number'))
        self.assertTrue(is_sensitive_field('passport_country'))
        self.assertTrue(is_sensitive_field('id_number'))
        self.assertTrue(is_sensitive_field('id_series'))

    def test_does_not_detect_safe_fields(self):
        """Should not flag non-sensitive fields."""
        self.assertFalse(is_sensitive_field('entity.name'))
        self.assertFalse(is_sensitive_field('entity.full_name'))
        self.assertFalse(is_sensitive_field('entity.first_name'))
        self.assertFalse(is_sensitive_field('entity.last_name'))
        self.assertFalse(is_sensitive_field('entity.email'))
        self.assertFalse(is_sensitive_field('entity.nationality'))
        self.assertFalse(is_sensitive_field('contract.duration_years'))
        self.assertFalse(is_sensitive_field('contract.currency'))
        self.assertFalse(is_sensitive_field('contract.start_date'))
        self.assertFalse(is_sensitive_field('commission.first_years_count'))

    def test_handles_empty_field_name(self):
        """Should handle empty or None field names."""
        self.assertFalse(is_sensitive_field(''))
        self.assertFalse(is_sensitive_field(None))


class ValueRedactionTests(TestCase):
    """Tests for value redaction."""

    def test_partial_redaction_long_value(self):
        """Should show first 2 and last 2 chars for long values."""
        result = redact_value('123456789', 'partial')
        # 9 chars total: 2 shown at start + asterisks (max 8, but 9-4=5) + 2 shown at end
        self.assertEqual(result, '12*****89')

    def test_partial_redaction_short_value(self):
        """Should fully redact short values."""
        result = redact_value('1234', 'partial')
        self.assertEqual(result, '****')

    def test_partial_redaction_very_short(self):
        """Should redact very short values."""
        result = redact_value('12', 'partial')
        self.assertEqual(result, '**')

    def test_full_redaction(self):
        """Should fully redact regardless of length."""
        result = redact_value('123456789', 'full')
        self.assertEqual(result, '***REDACTED***')

    def test_redacts_none_value(self):
        """Should handle None values."""
        result = redact_value(None)
        self.assertEqual(result, '***REDACTED***')

    def test_redacts_empty_string(self):
        """Should handle empty strings."""
        result = redact_value('')
        self.assertEqual(result, '***REDACTED***')

    def test_redacts_numeric_values(self):
        """Should handle numeric values by converting to string."""
        result = redact_value(123456, 'partial')
        self.assertIn('*', result)


class EmailMaskingTests(TestCase):
    """Tests for email address masking."""

    def test_masks_external_email(self):
        """Should mask external email addresses."""
        result = mask_email('john.doe@example.com')
        self.assertIn('*', result)
        self.assertIn('@example.com', result)
        self.assertTrue(result.startswith('jo'))

    def test_masks_short_local_part(self):
        """Should handle short local parts."""
        result = mask_email('ab@example.com')
        # Short local parts should still show
        self.assertIn('@example.com', result)

    def test_does_not_mask_internal_email(self):
        """Should not mask internal company emails."""
        result = mask_email('employee@hahahaproduction.com')
        self.assertEqual(result, 'employee@hahahaproduction.com')

    def test_force_mask_internal_email(self):
        """Should mask internal emails when force_mask=True."""
        result = mask_email('employee@hahahaproduction.com', force_mask=True)
        self.assertIn('*', result)
        self.assertIn('@hahahaproduction.com', result)

    def test_handles_invalid_email(self):
        """Should handle invalid email formats."""
        result = mask_email('not-an-email')
        self.assertEqual(result, 'not-an-email')

    def test_handles_empty_email(self):
        """Should handle empty email."""
        result = mask_email('')
        self.assertEqual(result, '')


class PlaceholderRedactionTests(TestCase):
    """Tests for placeholder values redaction."""

    def test_redacts_sensitive_placeholders(self):
        """Should redact sensitive fields from placeholder dict."""
        placeholders = {
            'entity.name': 'John Doe',
            'cnp': '1234567890123',
            'entity.iban': 'RO49AAAA1B31007593840000',
            'entity.email': 'artist@example.com',
        }

        result = redact_placeholder_values(placeholders)

        # Non-sensitive fields should remain
        self.assertEqual(result['entity.name'], 'John Doe')

        # Sensitive fields should be redacted
        self.assertIn('*', result['cnp'])
        self.assertIn('*', result['entity.iban'])

        # Emails should be masked
        self.assertIn('*', result['entity.email'])
        self.assertIn('@example.com', result['entity.email'])

    def test_handles_empty_placeholders(self):
        """Should handle empty placeholder dict."""
        result = redact_placeholder_values({})
        self.assertEqual(result, {})

    def test_handles_none_placeholders(self):
        """Should handle None placeholder dict."""
        result = redact_placeholder_values(None)
        self.assertIsNone(result)

    def test_handles_non_dict_placeholders(self):
        """Should handle non-dict placeholder values."""
        result = redact_placeholder_values([1, 2, 3])
        self.assertEqual(result, [1, 2, 3])

    def test_full_redaction_mode(self):
        """Should support full redaction mode."""
        placeholders = {
            'cnp': '1234567890123',
        }

        result = redact_placeholder_values(placeholders, redaction_type='full')
        self.assertEqual(result['cnp'], '***REDACTED***')


class AuditChangesRedactionTests(TestCase):
    """Tests for audit trail changes redaction."""

    def test_redacts_sensitive_changes(self):
        """Should redact sensitive field changes."""
        changes = {
            'title': {'old': 'Old Title', 'new': 'New Title'},
            'cnp': {'old': '1234567890123', 'new': '9876543210987'},
            'iban': {'old': 'RO49AAAA1111', 'new': 'RO49AAAA2222'},
        }

        result = redact_audit_changes(changes)

        # Non-sensitive changes remain
        self.assertEqual(result['title']['old'], 'Old Title')
        self.assertEqual(result['title']['new'], 'New Title')

        # Sensitive changes redacted
        self.assertIn('REDACTED', result['cnp']['old'])
        self.assertIn('REDACTED', result['iban']['old'])

    def test_redacts_simple_value_changes(self):
        """Should handle simple value changes (not old/new dict)."""
        changes = {
            'status': 'draft',
            'cnp': '1234567890123',
        }

        result = redact_audit_changes(changes)

        self.assertEqual(result['status'], 'draft')
        self.assertIn('REDACTED', result['cnp'])

    def test_handles_empty_changes(self):
        """Should handle empty changes dict."""
        result = redact_audit_changes({})
        self.assertEqual(result, {})

    def test_handles_none_changes(self):
        """Should handle None changes."""
        result = redact_audit_changes(None)
        self.assertIsNone(result)


class RedactionSummaryTests(TestCase):
    """Tests for redaction summary generation."""

    def test_generates_summary(self):
        """Should generate summary of redacted fields."""
        placeholders = {
            'entity.name': 'John Doe',
            'contract.duration_years': '3',
            'cnp': '1234567890123',
            'entity.phone': '+40712345678',
            'entity.iban': 'RO49AAAA1B31007593840000',
        }

        summary = get_redaction_summary(placeholders)

        self.assertEqual(summary['total_fields'], 5)
        self.assertEqual(summary['redacted_fields'], 3)
        self.assertIn('cnp', summary['redacted_field_names'])
        self.assertIn('entity.phone', summary['redacted_field_names'])
        self.assertIn('entity.iban', summary['redacted_field_names'])

    def test_summary_with_no_sensitive_fields(self):
        """Should handle placeholders with no sensitive fields."""
        placeholders = {
            'entity.name': 'John Doe',
            'contract.duration_years': '3',
        }

        summary = get_redaction_summary(placeholders)

        self.assertEqual(summary['total_fields'], 2)
        self.assertEqual(summary['redacted_fields'], 0)
        self.assertEqual(summary['redacted_field_names'], [])

    def test_summary_with_empty_placeholders(self):
        """Should handle empty placeholders."""
        summary = get_redaction_summary({})

        self.assertEqual(summary['total_fields'], 0)
        self.assertEqual(summary['redacted_fields'], 0)
        self.assertEqual(summary['redacted_field_names'], [])

    def test_summary_with_none_placeholders(self):
        """Should handle None placeholders."""
        summary = get_redaction_summary(None)

        self.assertEqual(summary['total_fields'], 0)
        self.assertEqual(summary['redacted_fields'], 0)


class IntegrationTests(TestCase):
    """Integration tests for complete redaction workflows."""

    def test_complete_contract_data_redaction(self):
        """Should redact all sensitive data from a typical contract."""
        contract_data = {
            'entity.name': 'John Doe',
            'contract.duration_years': '3',
            'start_date': '2024-01-01',
            'cnp': '1234567890123',  # Romanian CNP
            'passport_number': 'AB123456',
            'entity.iban': 'RO49AAAA1B31007593840000',  # Romanian IBAN
            'entity.phone': '+40712345678',
            'entity.address': '123 Main St, Bucharest',
            'entity.email': 'artist@example.com',
        }

        result = redact_placeholder_values(contract_data)

        # Safe fields preserved
        self.assertEqual(result['entity.name'], 'John Doe')
        self.assertEqual(result['contract.duration_years'], '3')
        self.assertEqual(result['start_date'], '2024-01-01')

        # Sensitive fields redacted
        self.assertNotEqual(result['cnp'], '1234567890123')
        self.assertNotEqual(result['passport_number'], 'AB123456')
        self.assertNotEqual(result['entity.iban'], 'RO49AAAA1B31007593840000')
        self.assertNotEqual(result['entity.phone'], '+40712345678')
        self.assertNotEqual(result['entity.address'], '123 Main St, Bucharest')

        # All sensitive fields should contain asterisks
        self.assertIn('*', result['cnp'])
        self.assertIn('*', result['passport_number'])
        self.assertIn('*', result['entity.iban'])
        self.assertIn('*', result['entity.phone'])
        self.assertIn('*', result['entity.address'])

        # Email should be masked but preserve domain
        self.assertIn('*', result['entity.email'])
        self.assertIn('@example.com', result['entity.email'])
