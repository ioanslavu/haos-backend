#!/usr/bin/env python
"""
Test script for PDF generation with weasyprint
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from camps.models import Camp, CampStudio, CampStudioArtist
from camps.services.pdf_generator import CampPDFGenerator
from api.models import Department
from identity.models import Entity

User = get_user_model()

def test_pdf_generation():
    """Test PDF generation for camps"""
    print("=" * 60)
    print("Testing PDF Generation for Camps")
    print("=" * 60)
    
    try:
        # Check if weasyprint is installed
        from weasyprint import HTML
        print("✓ Weasyprint is installed successfully")
    except ImportError as e:
        print(f"✗ Weasyprint import failed: {e}")
        return False
    
    try:
        # Get or create a test user
        user = User.objects.first() or User.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='testpass123'
        )
        print(f"✓ Using user: {user.email}")
        
        # Get or create a department
        department = Department.objects.first()
        if not department:
            print("✗ No department found. Please create a department first.")
            return False
        print(f"✓ Using department: {department.name}")
        
        # Create a test camp
        camp = Camp.objects.create(
            name="Test Camp for PDF Generation",
            status='draft',
            department=department,
            created_by=user
        )
        print(f"✓ Created test camp: {camp.name} (ID: {camp.id})")
        
        # Create test studios
        studio1 = CampStudio.objects.create(
            camp=camp,
            name="Studio A",
            location="Abbey Road",
            city="London",
            country="UK",
            hours=8.5,
            sessions=4
        )
        print(f"✓ Created studio: {studio1.name}")
        
        studio2 = CampStudio.objects.create(
            camp=camp,
            name="Studio B",
            location="Electric Lady",
            city="New York",
            country="USA",
            hours=6.0,
            sessions=3
        )
        print(f"✓ Created studio: {studio2.name}")
        
        # Add some test artists if they exist
        artists = Entity.objects.filter(kind='PF')[:2]
        if artists:
            for i, artist in enumerate(artists):
                CampStudioArtist.objects.create(
                    studio=studio1,
                    artist=artist,
                    is_internal=(i == 0)
                )
                print(f"✓ Added artist: {artist.display_name}")
        
        # Test PDF generation
        print("\n" + "-" * 60)
        print("Generating PDF...")
        print("-" * 60)
        
        generator = CampPDFGenerator(camp)
        
        # Generate HTML
        html_content = generator.generate_html()
        print(f"✓ HTML generated successfully ({len(html_content)} bytes)")
        
        # Generate PDF
        pdf_content = generator.generate_pdf()
        
        if isinstance(pdf_content, bytes) and len(pdf_content) > 0:
            print(f"✓ PDF generated successfully ({len(pdf_content)} bytes)")
            
            # Save PDF to file for inspection
            pdf_filename = f"/tmp/test_camp_{camp.id}.pdf"
            with open(pdf_filename, 'wb') as f:
                f.write(pdf_content)
            print(f"✓ PDF saved to: {pdf_filename}")
            
            # Verify file exists
            if os.path.exists(pdf_filename):
                file_size = os.path.getsize(pdf_filename)
                print(f"✓ File verified ({file_size} bytes)")
                return True
        else:
            print(f"✗ PDF generation returned invalid content: {type(pdf_content)}")
            return False
            
    except Exception as e:
        print(f"✗ Error during PDF generation: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_pdf_generation()
    print("\n" + "=" * 60)
    if success:
        print("PDF GENERATION TEST: PASSED ✓")
        sys.exit(0)
    else:
        print("PDF GENERATION TEST: FAILED ✗")
        sys.exit(1)
