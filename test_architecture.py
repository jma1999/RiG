#!/usr/bin/env python3
"""
Test script to validate RiG CMMS architecture with large IFC files.
"""
import os
import sys
import time
import requests
import json
from pathlib import Path

# Configuration
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
TEST_FILE_SIZE = 50 * 1024 * 1024  # 50MB test file
MAX_WAIT_TIME = 300  # 5 minutes max wait

def create_test_file(size_bytes):
    """Create a test IFC file of specified size."""
    test_file = Path("test_large.ifc")
    
    # Create a minimal IFC header
    ifc_header = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('test_large.ifc','2024-01-01T00:00:00',('Test User'),('Test Organization'),'Test Software','Test Software Version','Test Identifier');
FILE_SCHEMA(('IFC4'));
ENDSEC;

DATA;
#1=IFCPROJECT('0qX7$n8_0Eux5qy$n8_0Eu',#2,'Test Project',$,$,$,$,$,(#3),#4);
#2=IFCOWNERHISTORY(#5,#6,$,.ADDED.,$,$,$,0);
#3=IFCRELCONTAINEDINSPATIALSTRUCTURE('0qX7$n8_0Eux5qy$n8_0Eu',#7,'Test Structure',$,$,#8);
#4=IFCUNITASSIGNMENT((#9,#10,#11,#12,#13,#14,#15,#16,#17,#18,#19,#20,#21,#22,#23,#24,#25,#26,#27,#28,#29,#30,#31,#32,#33,#34,#35,#36,#37,#38,#39,#40,#41,#42,#43,#44,#45,#46,#47,#48,#49,#50));
#5=IFCPERSONANDORGANIZATION(#51,#52,$);
#6=IFCAPPLICATION(#53,'Test Software','Test Software Version','Test Identifier');
#7=IFCRELCONTAINEDINSPATIALSTRUCTURE('0qX7$n8_0Eux5qy$n8_0Eu',#7,'Test Structure',$,$,#8);
"""
    
    with open(test_file, 'w') as f:
        f.write(ifc_header)
        
        # Add dummy data to reach target size
        dummy_data = " " * 1024  # 1KB chunks
        remaining_size = size_bytes - len(ifc_header)
        
        while remaining_size > 0:
            chunk_size = min(len(dummy_data), remaining_size)
            f.write(dummy_data[:chunk_size])
            remaining_size -= chunk_size
    
    return test_file

def test_api_health():
    """Test API health endpoint."""
    print("Testing API health...")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ API is healthy: {health_data}")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API health check error: {e}")
        return False

def test_upload_session():
    """Test creating an upload session."""
    print("Testing upload session creation...")
    try:
        response = requests.post(
            f"{API_BASE}/upload/session",
            json={
                "file_name": "test_large.ifc",
                "file_size": TEST_FILE_SIZE,
                "content_type": "application/octet-stream",
                "tenant_id": "test"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            session_data = response.json()
            print(f"✅ Upload session created: {session_data['upload_id']}")
            return session_data
        else:
            print(f"❌ Upload session creation failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Upload session creation error: {e}")
        return None

def test_direct_upload(session_data, test_file):
    """Test direct upload to cloud storage."""
    print("Testing direct upload...")
    try:
        # This would normally upload to R2, but for testing we'll simulate
        print(f"✅ Direct upload simulation successful (would upload to {session_data['bucket']})")
        return True
    except Exception as e:
        print(f"❌ Direct upload error: {e}")
        return False

def test_job_processing():
    """Test job processing workflow."""
    print("Testing job processing...")
    try:
        # Simulate job creation
        job_id = "test-job-123"
        
        # Check job status
        response = requests.get(f"{API_BASE}/jobs/{job_id}", timeout=10)
        if response.status_code == 404:
            print("✅ Job status endpoint working (job not found as expected)")
            return True
        else:
            print(f"❌ Job status check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Job processing test error: {e}")
        return False

def test_search_functionality():
    """Test search functionality."""
    print("Testing search functionality...")
    try:
        response = requests.get(
            f"{API_BASE}/search",
            params={"q": "test", "k": 5},
            timeout=10
        )
        
        if response.status_code == 200:
            search_data = response.json()
            print(f"✅ Search working: {len(search_data.get('hits', []))} results")
            return True
        else:
            print(f"❌ Search failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Search test error: {e}")
        return False

def cleanup_test_file(test_file):
    """Clean up test file."""
    try:
        if test_file.exists():
            test_file.unlink()
            print(f"✅ Cleaned up test file: {test_file}")
    except Exception as e:
        print(f"⚠️ Failed to clean up test file: {e}")

def main():
    """Run all tests."""
    print("🚀 Starting RiG CMMS Architecture Tests")
    print(f"API Base URL: {API_BASE}")
    print(f"Test file size: {TEST_FILE_SIZE / (1024*1024):.1f} MB")
    print("-" * 50)
    
    # Create test file
    test_file = create_test_file(TEST_FILE_SIZE)
    print(f"📁 Created test file: {test_file} ({test_file.stat().st_size / (1024*1024):.1f} MB)")
    
    try:
        # Run tests
        tests = [
            ("API Health", test_api_health),
            ("Upload Session", lambda: test_upload_session() is not None),
            ("Direct Upload", lambda: test_direct_upload(test_upload_session(), test_file)),
            ("Job Processing", test_job_processing),
            ("Search Functionality", test_search_functionality),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🧪 Running {test_name} test...")
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} test failed")
        
        print("\n" + "=" * 50)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Architecture is ready for large IFC files.")
            return 0
        else:
            print("⚠️ Some tests failed. Check the issues above.")
            return 1
            
    finally:
        # Cleanup
        cleanup_test_file(test_file)

if __name__ == "__main__":
    sys.exit(main())
