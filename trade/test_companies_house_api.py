#!/usr/bin/env python3
"""
Test script for Companies House API
Uses the API key from .env file to fetch company information
"""

import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Get API key from environment (strip whitespace/CRLF)
API_KEY = (os.getenv('COMPANIES_HOUSE_API_KEY') or '').strip()

if not API_KEY:
    print("ERROR: COMPANIES_HOUSE_API_KEY not found in .env file")
    exit(1)

# Companies House API base URL
BASE_URL = "https://api.company-information.service.gov.uk"

# Test with a well-known company number (e.g., "00000006" - MARINE AND GENERAL MUTUAL LIFE ASSURANCE SOCIETY)
# You can also try "00000001" or any valid UK company number
TEST_COMPANY_NUMBER = "00000006"

def test_company_lookup(company_number):
    """
    Test the Companies House API by looking up a company

    Args:
        company_number: UK Companies House registration number
    """
    # API endpoint
    url = f"{BASE_URL}/company/{company_number}"

    print(f"Testing Companies House API...")
    print(f"API Key: [redacted] (len={len(API_KEY)})")
    print(f"URL: {url}")
    print(f"Company Number: {company_number}")
    print("-" * 60)

    try:
        # Make the request with basic auth (API key as username, empty password)
        response = requests.get(
            url,
            auth=(API_KEY, ''),  # API key as username, empty password
            headers={'Accept': 'application/json'}
        )

        # Check response status
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            print("✓ Success! API is working correctly.")

            # Parse JSON response
            data = response.json()

            # Save response to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"companies_house_response_{timestamp}.json"

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"\n✓ Response saved to: {output_file}")

            # Display some key information
            print("\n" + "=" * 60)
            print("Company Information:")
            print("=" * 60)
            print(f"Company Name: {data.get('company_name', 'N/A')}")
            print(f"Company Number: {data.get('company_number', 'N/A')}")
            print(f"Status: {data.get('company_status', 'N/A')}")
            print(f"Type: {data.get('type', 'N/A')}")
            print(f"Incorporated: {data.get('date_of_creation', 'N/A')}")

            if 'registered_office_address' in data:
                addr = data['registered_office_address']
                print(f"\nRegistered Office:")
                for key, value in addr.items():
                    print(f"  {key}: {value}")

            return data

        elif response.status_code == 401:
            print("✗ Authentication failed. Check your API key.")
            return None

        elif response.status_code == 404:
            print(f"✗ Company number {company_number} not found.")
            return None

        else:
            print(f"✗ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {e}")
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("Companies House API Test")
    print("=" * 60)
    print()

    # Test the API
    result = test_company_lookup(TEST_COMPANY_NUMBER)

    if result:
        print("\n" + "=" * 60)
        print("Test completed successfully!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("Test failed. Please check the output above.")
        print("=" * 60)
