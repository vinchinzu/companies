#!/bin/bash
# Quick test script for Companies House API using curl

# Load API key from .env (strip CRLF/whitespace)
API_KEY=$(grep '^COMPANIES_HOUSE_API_KEY=' .env | cut -d'=' -f2- | tr -d '\r' | xargs)

if [ -z "$API_KEY" ]; then
    echo "ERROR: COMPANIES_HOUSE_API_KEY not found in .env"
    exit 1
fi

echo "Testing Companies House API..."
echo "API Key: [redacted] (len=${#API_KEY})"
echo "=========================================="
echo ""

# Test company lookup
COMPANY_NUMBER="00000006"
echo "Looking up company: $COMPANY_NUMBER"
echo ""

# Make the request and save to file
OUTPUT_FILE="companies_house_response_$(date +%Y%m%d_%H%M%S).json"

curl -u "$API_KEY:" \
    -H "Accept: application/json" \
    "https://api.company-information.service.gov.uk/company/$COMPANY_NUMBER" \
    -o "$OUTPUT_FILE" \
    -w "\n\nHTTP Status: %{http_code}\n"

echo ""
echo "Response saved to: $OUTPUT_FILE"
echo ""
echo "Contents:"
cat "$OUTPUT_FILE" | python3 -m json.tool 2>/dev/null || cat "$OUTPUT_FILE"
