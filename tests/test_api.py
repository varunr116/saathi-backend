"""
Simple test script to validate Saathi backend setup
"""
import requests
import sys
import json


def test_health_check():
    """Test basic health check endpoint"""
    print("Testing health check endpoint...")
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            data = response.json()
            print("✅ Health check passed")
            print(f"   Status: {data['status']}")
            print(f"   Services: {json.dumps(data['services'], indent=6)}")
            return True
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is it running?")
        print("   Run: python app/main.py")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_text_query():
    """Test simple text query"""
    print("\nTesting text query endpoint...")
    try:
        response = requests.post(
            "http://localhost:8000/api/query",
            data={"text": "Hello Saathi, introduce yourself"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Text query passed")
            print(f"   Query: {data['query']}")
            print(f"   Response: {data['response'][:100]}...")
            return True
        else:
            print(f"❌ Query failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("=" * 50)
    print("🙏 Saathi Backend Test Suite")
    print("=" * 50)
    
    tests = [
        test_health_check,
        test_text_query
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
    
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! Backend is working correctly.")
    else:
        print("❌ Some tests failed. Check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
