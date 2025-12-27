#!/bin/bash

# Test loan application submission
# This script submits a loan application using the sample documents

# Set colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# API configuration
API_URL="http://127.0.0.1:8000"
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0dXNlciIsImV4cCI6MTc2Njg0NzUxMH0.GC4_P099G-igUNP88W4qRfzDfkp986JZUcDphGpE1OA"

# Sample documents (already uploaded to COS)
ID_PROOF="/home/qvidal01/projects/sample_docs_analysis/ID Doc.png"
INCOME_PROOF="/home/qvidal01/projects/sample_docs_analysis/Income Doc.png"
ADDRESS_PROOF="/home/qvidal01/projects/sample_docs_analysis/Address Doc.png"

# Form data JSON
FORM_DATA='{
  "fullName": "John Michael Doe",
  "dateOfBirth": "1985-03-15",
  "ssn": "123-45-6789",
  "address": "123 Main Street",
  "city": "Dallas",
  "state": "TX",
  "zipCode": "75201",
  "phone": "555-123-4567",
  "email": "john.doe@example.com",
  "employmentStatus": "employed",
  "employer": "Tech Corp Inc",
  "annualIncome": 75000,
  "loanAmount": 50000,
  "loanPurpose": "business expansion"
}'

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}   IBM Watsonx Loan Application Test${NC}"
echo -e "${BLUE}===========================================${NC}"
echo ""

echo -e "${GREEN}Step 1: Preparing loan application...${NC}"
echo "Applicant: John Michael Doe"
echo "Loan Amount: \$50,000"
echo "Purpose: Business expansion"
echo ""

echo -e "${GREEN}Step 2: Submitting application with documents...${NC}"
echo "- ID Proof: ID Doc.png"
echo "- Income Proof: Income Doc.png"
echo "- Address Proof: Address Doc.png"
echo ""

# Submit the application
RESPONSE=$(curl -s -X POST "${API_URL}/submit_form" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "formDataJson=${FORM_DATA}" \
  -F "idProof=@${ID_PROOF}" \
  -F "incomeProof=@${INCOME_PROOF}" \
  -F "addressProof=@${ADDRESS_PROOF}")

echo -e "${GREEN}Step 3: Processing response...${NC}"
echo ""

# Parse and display response
echo "$RESPONSE" | python3 -m json.tool

# Extract application ID if successful
APP_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('application_id', ''))" 2>/dev/null)

if [ -n "$APP_ID" ]; then
    echo ""
    echo -e "${GREEN}✅ Application submitted successfully!${NC}"
    echo -e "${YELLOW}Application ID: ${APP_ID}${NC}"
    echo ""
    echo -e "${BLUE}===========================================${NC}"
    echo -e "${BLUE}   Watsonx Agents are now processing...${NC}"
    echo -e "${BLUE}===========================================${NC}"
    echo ""
    echo "The following agents will process your application:"
    echo "1. 📄 Document Processor - Classifying and extracting data..."
    echo "2. 🔍 Document Validator - Checking for fraud..."
    echo "3. ✅ Cross Validator - Verifying consistency..."
    echo "4. 🎯 Final Decision - Making loan decision..."
    echo ""
    echo "To check application status:"
    echo "curl -H \"Authorization: Bearer ${TOKEN}\" ${API_URL}/get_logs/${APP_ID} | python3 -m json.tool"
else
    echo ""
    echo -e "${YELLOW}⚠️  Error submitting application${NC}"
fi

echo ""
