#!/usr/bin/env python
"""
Test script for PDF generation API endpoint
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory, force_authenticate
from camps.models import Camp
from camps.views import CampViewSet
from api.models import Department

User = get_user_model()

def test_pdf_export_endpoint():
    """Test the PDF export API endpoint"""
    print("=" * 60)
    print("Testing PDF Export API Endpoint")
    print("=" * 60)
    
    try:
        # Get the first camp
        camp = Camp.objects.filter(deleted_at__isnull=True).first()
        
        if not camp:
            print("✗ No camps found in database")
            return False
        
        print(f"✓ Found test camp: {camp.name} (ID: {camp.id})")
        
        # Create a test user
        user = User.objects.first()
        if not user:
            print("✗ No users found in database")
            return False
        print(f"✓ Using available user: {user.email}")
        
        # Create API request
        factory = APIRequestFactory()
        request = factory.post(f'/camps/{camp.id}/export_pdf/')
        force_authenticate(request, user=user)
        
        # Create viewset instance and call export_pdf action
        viewset = CampViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        viewset.kwargs = {'pk': camp.id}
        
        # Call the export_pdf action
        response = viewset.export_pdf(request, pk=camp.id)
        
        # Check response
        print(f"✓ Export PDF action executed")
        print(f"✓ Response status: {response.status_code}")
        print(f"✓ Content type: {response.get('Content-Type', 'Not set')}")
        print(f"✓ Content disposition: {response.get('Content-Disposition', 'Not set')}")
        
        # Check if response has PDF content
        if hasattr(response, 'data') and isinstance(response.data, bytes):
            pdf_size = len(response.data)
            print(f"✓ PDF content size: {pdf_size} bytes")
            
            # Check if it looks like a PDF
            if response.data.startswith(b'%PDF'):
                print("✓ PDF header verified (%PDF)")
                return True
            else:
                print(f"✗ Invalid PDF header: {response.data[:10]}")
                return False
        else:
            print(f"✗ Response data type: {type(response.data)}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing API endpoint: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_pdf_export_endpoint()
    print("\n" + "=" * 60)
    if success:
        print("PDF EXPORT API ENDPOINT TEST: PASSED ✓")
        sys.exit(0)
    else:
        print("PDF EXPORT API ENDPOINT TEST: FAILED ✗")
        sys.exit(1)
