# Camp PDF Generation - Usage Guide

## Quick Start

### Using the API Endpoint

```bash
# Export a camp as PDF
POST /api/camps/{camp_id}/export_pdf/

# Example with curl:
curl -X POST http://localhost:8000/api/camps/1/export_pdf/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o camp_1.pdf
```

### Using Python Directly

```python
from camps.models import Camp
from camps.services.pdf_generator import CampPDFGenerator

# Get a camp
camp = Camp.objects.get(id=1)

# Generate PDF
generator = CampPDFGenerator(camp)
pdf_bytes = generator.generate_pdf()

# Save to file
with open('camp_report.pdf', 'wb') as f:
    f.write(pdf_bytes)
```

### In Django Shell

```python
python manage.py shell
```

```python
from camps.models import Camp
from camps.services.pdf_generator import CampPDFGenerator

camp = Camp.objects.first()
generator = CampPDFGenerator(camp)
pdf_content = generator.generate_pdf()

# Verify it's a valid PDF
print(f"PDF Size: {len(pdf_content)} bytes")
print(f"PDF Header: {pdf_content[:4]}")  # Should output: b'%PDF'
```

---

## Running Tests

### Basic PDF Generation Test
```bash
cd /home/ioan/projects/HaOS/stack/backend
source venv/bin/activate
python test_pdf_generation.py
```

### Comprehensive Multi-Camp Test
```bash
cd /home/ioan/projects/HaOS/stack/backend
source venv/bin/activate
python test_pdf_comprehensive.py
```

---

## System Architecture

### Components

```
Django Backend
│
├── camps/models.py
│   ├── Camp (main model)
│   ├── CampStudio (studios within camps)
│   └── CampStudioArtist (artists in studios)
│
├── camps/services/pdf_generator.py
│   └── CampPDFGenerator (PDF generation service)
│
├── camps/views.py
│   └── export_pdf() action endpoint
│
├── camps/templates/camps/camp_report.html
│   └── HTML template for PDF content
│
└── requirements.txt
    └── weasyprint (PDF generation library)
```

### Data Flow

```
Camp Object
    ↓
CampPDFGenerator.generate_html()
    ↓ (renders template with camp data)
HTML String
    ↓
weasyprint.HTML(string=html).write_pdf()
    ↓
PDF Binary
    ↓
HTTP Response (application/pdf)
```

---

## Features

### What's Included in Generated PDFs

1. **Camp Information**
   - Camp name
   - Date range (start and end)
   - Status
   - Creation date
   - Creator information

2. **Studio Details** (for each studio)
   - Name and sequence number
   - Location (building name, city, country)
   - Hours and sessions scheduled
   - Internal artists list
   - External contractors list

3. **Professional Formatting**
   - A4 page size with 2cm margins
   - Clean typography (Arial font)
   - Section headers with underlines
   - Tables for structured data
   - Page break control

---

## Configuration

### Settings

The PDF generation uses Django's template system. Ensure your Django settings include:

```python
# config/settings.py

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'camps/templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
            ],
        },
    },
]
```

### Permissions

PDF export requires:
- **Authentication**: User must be logged in (IsAuthenticated)
- **Authorization**: User must be Administrator or Manager (IsAdministratorOrManager)

---

## Troubleshooting

### Issue: "Invalid filter: 'reverse'"
**Solution**: This has been fixed. The template no longer uses the unsupported `reverse` filter.

### Issue: ImportError: No module named 'weasyprint'
**Solution**: Install weasyprint in your virtual environment:
```bash
source venv/bin/activate
pip install weasyprint
```

### Issue: PDF generation is slow
**Solution**: Consider moving to background tasks:
```python
from celery import shared_task

@shared_task
def generate_camp_pdf(camp_id):
    camp = Camp.objects.get(id=camp_id)
    generator = CampPDFGenerator(camp)
    pdf_bytes = generator.generate_pdf()
    # Store or email the PDF
    return len(pdf_bytes)
```

### Issue: Special characters not rendering correctly
**Solution**: The template already uses UTF-8 encoding. Ensure your database returns UTF-8 data.

---

## Performance Considerations

### PDF Generation Time
- Single camp with 2 studios: ~100-200ms
- Single camp with 5 studios: ~300-500ms
- Scales roughly linearly with studio/artist count

### Memory Usage
- Typical camp PDF: 13-15 KB
- HTML template: ~5-6 KB
- Overhead: Minimal

### Recommendations
1. Use background tasks for batch exports
2. Cache frequently accessed PDFs
3. Consider streaming responses for large files
4. Monitor performance in production

---

## Extension Points

### Customizing PDF Layout

Edit the HTML template:
```
/home/ioan/projects/HaOS/stack/backend/camps/templates/camps/camp_report.html
```

Available CSS:
- Page styling with @page rules
- Professional typography
- Table layouts
- Print-friendly styles

### Adding More Data

Edit the PDF generator context:
```python
# camps/services/pdf_generator.py
def generate_html(self):
    context = {
        'camp': self.camp,
        'studios': self.camp.studios.all(),
        'custom_data': self.get_custom_data(),  # Add custom data
        'generated_at': timezone.now(),
    }
```

---

## Support

For issues or questions:
1. Check test files for usage examples
2. Review the CampPDFGenerator source code
3. Consult Django and weasyprint documentation
4. Check Django template syntax reference

---

## Version Information

- Weasyprint: 66.0
- Django: (version from your setup)
- Python: 3.12+
- Installation Date: November 10, 2025
