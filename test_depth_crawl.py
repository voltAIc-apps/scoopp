#!/usr/bin/env python3
"""
Test script for the enhanced depth crawling functionality
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def get_auth_token():
    """Get authentication token"""
    token_data = {
        "email": "test@example.com"
    }
    response = requests.post(f"{BASE_URL}/token", json=token_data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Failed to get token: {response.text}")
        return None

def test_regular_crawl(token):
    """Test the /crawl endpoint with regular multi-URL crawling"""
    print("\n=== Testing Regular Multi-URL Crawling ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    crawl_request = {
        "urls": ["https://httpbin.org", "https://example.com"],
        "browser_config": {},
        "crawler_config": {}
    }
    
    print("Sending regular crawl request...")
    response = requests.post(f"{BASE_URL}/crawl", json=crawl_request, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print("✓ Regular crawl successful!")
        print(f"  URLs crawled: {len(result.get('results', []))}")
        return True
    else:
        print(f"✗ Regular crawl failed: {response.status_code}")
        print(response.text)
        return False

def test_depth_crawl(token):
    """Test the enhanced /crawl endpoint with depth crawling"""
    print("\n=== Testing Enhanced /crawl with Depth Crawling ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test depth crawling via /crawl endpoint
    depth_request = {
        "urls": ["https://example.com"],  # Single URL for depth crawling
        "max_depth": 2,
        "crawl_strategy": "bfs",
        "include_external": False,
        "max_pages": 10,
        "browser_config": {},
        "crawler_config": {}
    }
    
    print("Sending depth crawl request via /crawl...")
    response = requests.post(f"{BASE_URL}/crawl", json=depth_request, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print("✓ Depth crawl successful!")
        metadata = result.get('crawl_metadata', {})
        print(f"  Pages crawled: {metadata.get('pages_crawled', 'unknown')}")
        print(f"  Max depth: {metadata.get('max_depth', 'unknown')}")
        print(f"  Strategy: {metadata.get('strategy', 'unknown')}")
        return True
    else:
        print(f"✗ Depth crawl failed: {response.status_code}")
        print(response.text)
        return False

def test_depth_crawl_validation(token):
    """Test validation of depth crawling (should fail with multiple URLs)"""
    print("\n=== Testing Depth Crawl Validation ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # This should fail because depth crawling requires single URL
    invalid_request = {
        "urls": ["https://example.com", "https://httpbin.org"],  # Multiple URLs
        "max_depth": 2,  # This should trigger validation error
        "crawl_strategy": "bfs",
        "include_external": False,
    }
    
    print("Sending invalid depth crawl request (multiple URLs + max_depth)...")
    response = requests.post(f"{BASE_URL}/crawl", json=invalid_request, headers=headers)
    
    if response.status_code == 400:
        print("✓ Validation correctly rejected multiple URLs with depth crawling")
        return True
    elif response.status_code == 200:
        print("✗ Should have failed validation but succeeded")
        return False
    else:
        print(f"✗ Unexpected error: {response.status_code}")
        print(response.text)
        return False

def test_result_structure(token):
    """Test that results are properly structured dictionaries without strings"""
    print("\n=== Testing Result Structure ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test with a simple crawl to verify result structure
    crawl_request = {
        "urls": ["https://httpbin.org/json"],  # Simple JSON endpoint
        "browser_config": {},
        "crawler_config": {}
    }
    
    print("Testing result structure with simple crawl...")
    response = requests.post(f"{BASE_URL}/crawl", json=crawl_request, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        results = result.get('results', [])
        
        if not results:
            print("✗ No results returned")
            return False
            
        # Check that results are list of dicts
        if not isinstance(results, list):
            print(f"✗ Results should be a list, got {type(results)}")
            return False
            
        def check_no_nested_lists(obj, path="root"):
            """Recursively check that there are no nested lists of lists"""
            if isinstance(obj, list):
                for i, item in enumerate(obj):
                    if isinstance(item, list):
                        print(f"✗ Found nested list at {path}[{i}]: {type(item)}")
                        return False
                    elif isinstance(item, dict):
                        if not check_no_nested_lists(item, f"{path}[{i}]"):
                            return False
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    if not check_no_nested_lists(value, f"{path}.{key}"):
                        return False
            return True
        
        for i, r in enumerate(results):
            if not isinstance(r, dict):
                print(f"✗ Result {i} should be a dict, got {type(r)}")
                return False
            
            # Check for nested list structures
            if not check_no_nested_lists(r, f"results[{i}]"):
                return False
                
        print("✓ All results are properly structured as dictionaries")
        print("✓ No nested list(list(dict)) structures found")
        print(f"  Number of results: {len(results)}")
        print(f"  First result keys: {list(results[0].keys())[:5]}...")  # Show first 5 keys
        return True
    else:
        print(f"✗ Request failed: {response.status_code}")
        print(response.text)
        return False

def main():
    print("Depth Crawling Test Suite")
    print("=" * 50)
    
    # This test assumes the server is running
    try:
        # Test if server is up
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("✗ Server is not running or health check failed")
            return
        print("✓ Server is running")
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to server. Make sure it's running on http://localhost:8000")
        return
    
    # Get auth token
    token = get_auth_token()
    if not token:
        print("✗ Failed to authenticate")
        return
    print("✓ Authentication successful")
    
    # Run tests
    test1_passed = test_regular_crawl(token)
    test2_passed = test_depth_crawl(token) 
    test3_passed = test_depth_crawl_validation(token)
    test4_passed = test_result_structure(token)
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"  Regular Multi-URL Crawl: {'✓ PASSED' if test1_passed else '✗ FAILED'}")
    print(f"  Enhanced Depth Crawl: {'✓ PASSED' if test2_passed else '✗ FAILED'}")
    print(f"  Depth Crawl Validation: {'✓ PASSED' if test3_passed else '✗ FAILED'}")
    print(f"  Result Structure Test: {'✓ PASSED' if test4_passed else '✗ FAILED'}")
    
    if test1_passed and test2_passed and test3_passed and test4_passed:
        print("\n🎉 All tests passed! Enhanced /crawl endpoint is working perfectly.")
    else:
        print("\n❌ Some tests failed. Check the implementation.")

if __name__ == "__main__":
    main()