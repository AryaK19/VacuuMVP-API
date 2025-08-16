import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base URL
BASE_URL = "http://localhost:8000/api"

# Test user data
test_user = {
    "email": "test@example.com",
    "password": "Test@123456",
    "confirm_password": "Test@123456",
    "username": "testuser",
    "first_name": "Test",
    "last_name": "User"
}

login_data = {
    "email": "test@example.com",
    "password": "Test@123456"
}

forgot_password_data = {
    "email": "test@example.com"
}

# Function to test registration
def test_register():
    print("\n--- Testing Registration ---")
    response = requests.post(f"{BASE_URL}/auth/register", json=test_user)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=4)}")
    return response.json()

# Function to test login
def test_login():
    print("\n--- Testing Login ---")
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=4)}")
    return response.json()

# Function to test forgot password
def test_forgot_password():
    print("\n--- Testing Forgot Password ---")
    response = requests.post(f"{BASE_URL}/auth/forgot-password", json=forgot_password_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=4)}")
    return response.json()

# Function to test logout
def test_logout(access_token):
    print("\n--- Testing Logout ---")
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.post(f"{BASE_URL}/auth/logout", headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=4)}")
    return response.json()

if __name__ == "__main__":
    try:
        # Test registration
        reg_response = test_register()
        
        # Test login
        login_response = test_login()
        
        if login_response.get("session") and login_response["session"].get("access_token"):
            # Test logout with the access token
            logout_response = test_logout(login_response["session"]["access_token"])
        
        # Test forgot password
        forgot_response = test_forgot_password()
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
