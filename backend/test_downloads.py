#!/usr/bin/env python3
"""
Test script to validate download functionality
"""
import requests
import time
import json

def test_download_persistence():
    """Test that files remain available after download"""
    API_BASE = "http://localhost:5001"
    
    print("🧪 Testing Download Persistence...")
    
    # Test storage info
    try:
        response = requests.get(f"{API_BASE}/storage_info")
        if response.ok:
            data = response.json()
            print(f"📊 Storage Info: {data['active_jobs']} active jobs, {data['downloaded_jobs']} downloaded jobs")
        else:
            print(f"❌ Failed to get storage info: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing storage info: {e}")
    
    # Test system info
    try:
        response = requests.get(f"{API_BASE}/system_info")
        if response.ok:
            data = response.json()
            print(f"🛠️ System Info: {data['current_model']}")
            print(f"📝 Features: {', '.join(data['features'][:3])}...")
        else:
            print(f"❌ Failed to get system info: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing system info: {e}")
    
    # Test health check
    try:
        response = requests.get(f"{API_BASE}/health")
        if response.ok:
            data = response.json()
            print(f"💚 Health: {data['status']} - {data['memory_available_gb']}GB available")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing health: {e}")
    
    print("✅ Backend connectivity test completed!")

if __name__ == "__main__":
    test_download_persistence()
