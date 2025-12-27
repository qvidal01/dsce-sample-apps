"""
Direct Watsonx AI implementation - bypasses Orchestrate agents
Uses Watsonx AI vision models directly to process documents
"""
import os
import ibm_boto3
import base64
import mimetypes
from ibm_botocore.client import Config
from langchain_ibm import ChatWatsonx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# COS setup
cos = ibm_boto3.client("s3",
    ibm_api_key_id=os.getenv("COS_API_KEY"),
    ibm_service_instance_id=os.getenv("COS_SERVICE_INSTANCE_ID"),
    config=Config(signature_version="oauth"),
    endpoint_url=os.getenv("COS_ENDPOINT")
)

bucket_name = os.getenv("COS_BUCKET_NAME")

# Vision LLM setup
vision_llm = ChatWatsonx(
    model_id="meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
    apikey=os.getenv('WATSONX_APIKEY'),
    url=os.getenv('WATSONX_URL'),
    project_id=os.getenv('WATSONX_PROJECT_ID'),
    params={
        "max_new_tokens": 2000,
        "temperature": 0.0,
        "top_p": 0.1,
    }
)

# Text LLM setup (for cross-validation and final decision)
text_llm = ChatWatsonx(
    model_id="mistralai/mistral-medium-2505",
    apikey=os.getenv('WATSONX_APIKEY'),
    url=os.getenv('WATSONX_URL'),
    project_id=os.getenv('WATSONX_PROJECT_ID'),
    params={
        "max_new_tokens": 2000,
        "temperature": 0.3,
    }
)


def read_image_from_cos_as_base64(key: str) -> str:
    """Read image from COS and return as base64 data URI"""
    response = cos.get_object(Bucket=bucket_name, Key=key)
    image_bytes = response['Body'].read()
    base64_encoded = base64.b64encode(image_bytes).decode("utf-8")
    mime_type, _ = mimetypes.guess_type(key)
    if mime_type is None:
        mime_type = "image/png"
    return f"data:{mime_type};base64,{base64_encoded}"


def classify_document(filename: str) -> Dict:
    """Classify a document image"""
    image_base64 = read_image_from_cos_as_base64(filename)

    system_prompt = """You are a helpful document classification assistant. You will be given an image of a document. Your task is to carefully analyze the visual and textual content of the document to determine its type.

The possible types are:
    * Driving License
    * Passport
    * SSN (Social Security Number card)
    * Utility Bill
    * Salary Slip
    * ITR (Income Tax Return)
    * Bank Account Statement
    * Others (if it does not match any of the above types)

Based on the layout, text, and any visible clues, classify the document into one of these types.
Return your answer strictly in the following JSON format (without any extra text):

```
{
  "doc_type": "<document type>"
}
```

Replace `<document type>` with one of the above options exactly as written."""

    content = [
        {"type": "text", "text": "Classify this document"},
        {"type": "image_url", "image_url": {"url": image_base64}}
    ]

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=content)
    ]

    response = vision_llm.invoke(messages)
    parser = JsonOutputParser()
    parsed = parser.parse(response.content)
    parsed["filename"] = filename
    return parsed


def extract_document_info(filename: str) -> Dict:
    """Extract PII from a document image"""
    image_base64 = read_image_from_cos_as_base64(filename)

    system_prompt = """You are a highly skilled information extraction assistant.
You will be given an image of a document. Your task is to carefully analyze the visual and textual content of the document and extract all available personal information.

Specifically, extract details such as (if present):
 - Name
 - Address
 - Date of Birth (DOB)
 - Gender
 - Document Number (e.g., passport number, license number, SSN)
 - Nationality
 - Issuing authority
 - Date of issue and expiry
 - Any other identifiable personal information visible in the document

All the dates should be extracted in the format YYYY-MM-DD.
For document number, the json key should be respective to the document type (e.g., "passport_number", "driving_license_number", etc.).
Only include information explicitly present on the document. If a field is not found, omit it from the output.
Return the extracted information strictly in a JSON format, for example:

```json
{
  "name": "John Doe",
  "address": "123 Main Street, Springfield, IL, USA",
  "dob": "1990-05-15",
  "gender": "Male",
  "document_number": "X1234567",
  "nationality": "USA",
  "issuing_authority": "US Department of State",
  "issue_date": "2015-04-10",
  "expiry_date": "2025-04-10"
}
```

If any information is missing, do not include that key in the JSON.
Provide only the JSON object as the output, with no additional text."""

    content = [
        {"type": "text", "text": "Extract personal information from this document"},
        {"type": "image_url", "image_url": {"url": image_base64}}
    ]

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=content)
    ]

    response = vision_llm.invoke(messages)
    parser = JsonOutputParser()
    parsed = parser.parse(response.content)
    parsed["filename"] = filename
    return parsed


def validate_document(filename: str) -> Dict:
    """Validate document authenticity using vision analysis"""
    image_base64 = read_image_from_cos_as_base64(filename)

    system_prompt = """You are a document fraud detection expert. Analyze this document image for signs of forgery or manipulation.

Check for:
1. Layout consistency - Does the layout match standard government-issued documents?
2. Field consistency - Are all fields properly formatted and aligned?
3. Signs of forgery - Photo manipulation, text overlays, font mismatches, etc.
4. Overall authenticity - Does this appear to be a genuine document?

Return your analysis in JSON format:
```json
{
  "valid": true/false,
  "reason": "Brief explanation of why the document is valid or fake",
  "layout_score": 0-100,
  "field_score": 0-100,
  "forgery_signs": ["list", "of", "issues"] or []
}
```"""

    content = [
        {"type": "text", "text": "Validate the authenticity of this document"},
        {"type": "image_url", "image_url": {"url": image_base64}}
    ]

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=content)
    ]

    response = vision_llm.invoke(messages)
    parser = JsonOutputParser()
    parsed = parser.parse(response.content)
    parsed["filename"] = filename
    return parsed


def cross_validate(application_data: Dict, document_data: List[Dict]) -> Dict:
    """Cross-validate application data with extracted document data"""

    prompt = f"""You are a cross-validation agent. Compare the loan application data with the extracted document data.

Application Data:
{application_data}

Document Data:
{document_data}

Check for:
1. Name consistency (case-insensitive)
2. Date of birth consistency
3. Address consistency (minor variations allowed)
4. Identification numbers (SSN, passport, license)
5. Any other overlapping fields

Return JSON format:
```json
{{
  "cross_validation_results": {{
    "field_comparisons": [
      {{
        "field_name": "string",
        "application_value": "string",
        "document_values": ["array"],
        "status": "matched/mismatched",
        "details": "explanation"
      }}
    ],
    "inconsistencies": [
      {{
        "field": "string",
        "issue": "description",
        "severity": "high/medium/low"
      }}
    ],
    "summary": "Overall summary",
    "overall_status": "passed/failed"
  }}
}}
```"""

    response = text_llm.invoke(prompt)
    parser = JsonOutputParser()
    return parser.parse(response.content)


def calculate_age(dob_str: str) -> int:
    """Calculate age from DOB string in YYYY-MM-DD format"""
    from datetime import datetime
    dob = datetime.strptime(dob_str, "%Y-%m-%d")
    today = datetime.now()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return age


def make_final_decision(
    application_data: Dict,
    doc_processor_results: List[Dict],
    doc_validation_results: List[Dict],
    cross_validation_result: Dict
) -> Dict:
    """Make final loan decision based on all validation results"""

    # Check if all documents are valid
    all_docs_valid = all(doc.get("valid", False) for doc in doc_validation_results)

    # Check cross-validation status
    cross_val_passed = cross_validation_result.get("cross_validation_results", {}).get("overall_status") == "passed"

    # Check age from extracted DOB
    age_valid = False
    applicant_age = None
    dob_consistency = "unknown"

    # Try to get DOB from documents
    dobs = [doc.get("dob") for doc in doc_processor_results if doc.get("dob")]
    if dobs:
        # Check if all DOBs are consistent
        if len(set(dobs)) == 1:
            dob_consistency = "consistent"
            try:
                applicant_age = calculate_age(dobs[0])
                age_valid = applicant_age >= 18
            except:
                age_valid = False
        else:
            dob_consistency = "inconsistent"

    # Make final decision
    if all_docs_valid and cross_val_passed and age_valid:
        loan_status = "passed"
    else:
        loan_status = "rejected"

    return {
        "validation_details": {
            "document_authenticity": {
                "status": "passed" if all_docs_valid else "failed",
                "details": f"{sum(1 for d in doc_validation_results if d.get('valid', False))}/{len(doc_validation_results)} documents validated as authentic"
            },
            "cross_validation": {
                "status": "passed" if cross_val_passed else "failed",
                "details": cross_validation_result.get("cross_validation_results", {}).get("summary", "No summary")
            },
            "age_verification": {
                "status": "passed" if age_valid else "failed",
                "applicant_age": applicant_age,
                "dob_consistency": dob_consistency,
                "details": f"Applicant age: {applicant_age}" if applicant_age else "Could not verify age"
            },
            "overall_validation_summary": f"Documents: {'✅' if all_docs_valid else '❌'}, Cross-validation: {'✅' if cross_val_passed else '❌'}, Age: {'✅' if age_valid else '❌'}"
        },
        "loan_application_status": loan_status
    }


def process_loan_application_direct(
    document_names: List[str],
    loan_application_file: str
) -> Dict:
    """
    Process loan application using direct Watsonx AI calls (bypassing Orchestrate agents)

    Args:
        document_names: List of document paths in COS (e.g., ["uploads/app_xxx/ID Doc.png"])
        loan_application_file: Path to loan application JSON in COS

    Returns:
        Dict with validation details and loan status
    """
    print("🚀 Starting direct Watsonx AI processing...")

    # Step 1: Document Processing
    print(f"\n📄 Processing {len(document_names)} documents...")
    doc_processor_results = []
    for doc in document_names:
        print(f"  - Classifying {doc}...")
        classification = classify_document(doc)
        print(f"    ✅ Type: {classification.get('doc_type')}")

        print(f"  - Extracting PII from {doc}...")
        extraction = extract_document_info(doc)
        print(f"    ✅ Extracted: {list(extraction.keys())}")

        doc_processor_results.append({
            **classification,
            **extraction
        })

    # Step 2: Document Validation
    print(f"\n🔍 Validating {len(document_names)} documents...")
    doc_validation_results = []
    for doc in document_names:
        print(f"  - Validating {doc}...")
        validation = validate_document(doc)
        print(f"    {'✅' if validation.get('valid') else '❌'} {validation.get('reason', 'No reason')}")
        doc_validation_results.append(validation)

    # Step 3: Load application data
    print(f"\n📋 Loading application data from {loan_application_file}...")
    try:
        response = cos.get_object(Bucket=bucket_name, Key=loan_application_file)
        import json
        application_data = json.loads(response['Body'].read().decode('utf-8'))
        print(f"  ✅ Loaded application for: {application_data.get('firstName')} {application_data.get('lastName')}")
    except Exception as e:
        print(f"  ⚠️ Could not load application: {e}")
        application_data = {}

    # Step 4: Cross Validation
    print(f"\n🔄 Cross-validating application data with documents...")
    cross_validation_result = cross_validate(application_data, doc_processor_results)
    print(f"  {cross_validation_result.get('cross_validation_results', {}).get('overall_status', 'unknown')}")

    # Step 5: Final Decision
    print(f"\n🎯 Making final loan decision...")
    final_decision = make_final_decision(
        application_data,
        doc_processor_results,
        doc_validation_results,
        cross_validation_result
    )

    print(f"\n{'='*60}")
    print(f"FINAL DECISION: {final_decision['loan_application_status'].upper()}")
    print(f"{'='*60}\n")

    return final_decision
