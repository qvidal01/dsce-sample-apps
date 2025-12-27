#!/usr/bin/env python3
"""
Upload sample documents to IBM Cloud Object Storage
"""
import os
import sys

# Add minimal imports that should be available
try:
    import urllib.request
    import urllib.parse
    import json
    import hashlib
    import hmac
    from datetime import datetime
    from pathlib import Path
except ImportError as e:
    print(f"Error: Missing required module: {e}")
    sys.exit(1)

# COS credentials from environment
COS_API_KEY = "75W-5kuPpMhwwv4tPtYBvCLjtMznuLSzId-kpnzPoC3Z"
COS_SERVICE_INSTANCE_ID = "crn:v1:bluemix:public:cloud-object-storage:global:a/428988a1df3a40edbde845e4ef7b5728:1624f167-6a19-4e80-bc83-38fb8f985eb8::"
COS_ENDPOINT = "https://s3.us-south.cloud-object-storage.appdomain.cloud"
COS_BUCKET_NAME = "loan-processing-bucket-1766843846"

# Sample documents
SAMPLE_DOCS = [
    "/home/qvidal01/projects/sample_docs_analysis/Address Doc.png",
    "/home/qvidal01/projects/sample_docs_analysis/ID Doc.png",
    "/home/qvidal01/projects/sample_docs_analysis/Income Doc.png",
    "/home/qvidal01/projects/sample_docs_analysis/SSN.png",
    "/home/qvidal01/projects/sample_docs_analysis/Loan Application Form.pdf"
]

def get_iam_token(api_key):
    """Get IAM token for COS authentication"""
    url = "https://iam.cloud.ibm.com/identity/token"
    data = urllib.parse.urlencode({
        'grant_type': 'urn:ibm:params:oauth:grant-type:apikey',
        'apikey': api_key
    }).encode('utf-8')

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }

    req = urllib.request.Request(url, data=data, headers=headers)

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['access_token']
    except Exception as e:
        print(f"Error getting IAM token: {e}")
        return None

def upload_file(token, bucket, key, file_path):
    """Upload a file to COS"""
    if not os.path.exists(file_path):
        print(f"⚠️  File not found: {file_path}")
        return False

    # URL encode the key to handle spaces and special characters
    encoded_key = urllib.parse.quote(key, safe='')
    url = f"{COS_ENDPOINT}/{bucket}/{encoded_key}"

    # Read file content
    with open(file_path, 'rb') as f:
        file_data = f.read()

    headers = {
        'Authorization': f'Bearer {token}',
        'ibm-service-instance-id': COS_SERVICE_INSTANCE_ID,
        'Content-Type': 'application/octet-stream',
        'Content-Length': str(len(file_data))
    }

    req = urllib.request.Request(url, data=file_data, headers=headers, method='PUT')

    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                return True
            else:
                print(f"Upload failed with status: {response.status}")
                return False
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
        print(f"Response: {e.read().decode('utf-8')}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print(f"Uploading to bucket: {COS_BUCKET_NAME}")
    print(f"COS endpoint: {COS_ENDPOINT}\n")

    # Get IAM token
    print("Getting IAM token...")
    token = get_iam_token(COS_API_KEY)
    if not token:
        print("❌ Failed to get IAM token")
        sys.exit(1)
    print("✅ IAM token obtained\n")

    # Upload each document
    uploaded = []
    for doc_path in SAMPLE_DOCS:
        filename = os.path.basename(doc_path)
        key = f"sample_docs/{filename}"

        print(f"Uploading: {filename}...", end=' ')
        if upload_file(token, COS_BUCKET_NAME, key, doc_path):
            print("✅")
            uploaded.append(filename)
        else:
            print("❌")

    print(f"\n✅ Successfully uploaded {len(uploaded)}/{len(SAMPLE_DOCS)} documents:")
    for doc in uploaded:
        print(f"  - {doc}")

if __name__ == '__main__':
    main()
