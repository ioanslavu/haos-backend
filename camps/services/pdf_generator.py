"""
PDF Generator for Camp Reports
"""

from django.template.loader import render_to_string
from django.utils import timezone


class CampPDFGenerator:
    """
    Generates PDF reports for camps.
    Uses weasyprint to convert HTML to PDF.
    """

    def __init__(self, camp):
        self.camp = camp

    def generate_pdf(self):
        """
        Generate PDF report for the camp.
        Returns PDF content as bytes.
        """
        # Import weasyprint here to avoid import errors if not installed
        try:
            from weasyprint import HTML
        except ImportError:
            # Fallback: return a simple message if weasyprint is not installed
            return b"PDF generation requires weasyprint library. Install with: pip install weasyprint"

        # Render HTML template
        html_string = self.generate_html()

        # Convert HTML to PDF
        pdf_file = HTML(string=html_string).write_pdf()

        return pdf_file

    def generate_html(self):
        """
        Generate HTML content for the PDF report.
        """
        # Prepare context data
        context = {
            'camp': self.camp,
            'studios': self.camp.studios.all().prefetch_related('studio_artists__artist'),
            'generated_at': timezone.now(),
        }

        # Render template
        html = render_to_string('camps/camp_report.html', context)
        return html
