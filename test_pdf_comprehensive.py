#!/usr/bin/env python
"""
Comprehensive test of PDF generation functionality
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from camps.models import Camp
from camps.services.pdf_generator import CampPDFGenerator

def test_pdf_comprehensive():
    """Test PDF generation for all available camps"""
    print("=" * 60)
    print("Comprehensive PDF Generation Test")
    print("=" * 60)
    
    try:
        # Get all camps
        camps = Camp.objects.filter(deleted_at__isnull=True)
        
        if not camps.exists():
            print("✗ No camps found in database")
            return False
        
        print(f"✓ Found {camps.count()} camp(s) in database")
        
        success_count = 0
        for camp in camps:
            print(f"\nTesting camp: {camp.name} (ID: {camp.id})")
            print("-" * 60)
            
            try:
                # Generate PDF
                generator = CampPDFGenerator(camp)
                pdf_content = generator.generate_pdf()
                
                # Verify PDF content
                if isinstance(pdf_content, bytes) and len(pdf_content) > 0:
                    if pdf_content.startswith(b'%PDF'):
                        print(f"✓ Valid PDF generated ({len(pdf_content)} bytes)")
                        print(f"✓ PDF header: %PDF-{pdf_content[5:9]}")
                        success_count += 1
                    else:
                        print(f"✗ Invalid PDF header detected")
                else:
                    print(f"✗ Invalid PDF content: {type(pdf_content)}")
            except Exception as e:
                print(f"✗ Error generating PDF: {type(e).__name__}: {e}")
        
        print("\n" + "=" * 60)
        print(f"Test Results: {success_count}/{camps.count()} camps succeeded")
        
        return success_count == camps.count()
        
    except Exception as e:
        print(f"✗ Error during test: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_pdf_comprehensive()
    print("\n" + "=" * 60)
    if success:
        print("COMPREHENSIVE PDF TEST: PASSED ✓")
        sys.exit(0)
    else:
        print("COMPREHENSIVE PDF TEST: FAILED ✗")
        sys.exit(1)
