#!/bin/bash

# IBM Watsonx Agent Model Fix Script
# This script updates agent configurations to use available models and redeploys them

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}  IBM Watsonx Agent Model Fix${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Configuration
OLD_MODEL="mistralai/mistral-large"
NEW_MODEL="mistralai/mistral-medium-2505"
AGENTS_DIR="/home/qvidal01/projects/ibm-dsce-sample-apps/loan-preprocessing-agents/agents"

echo -e "${YELLOW}Model Configuration:${NC}"
echo "  Old: ${OLD_MODEL}"
echo "  New: ${NEW_MODEL}"
echo ""

# Navigate to agents directory
cd "$AGENTS_DIR"
echo -e "${GREEN}Step 1: Activating virtual environment...${NC}"
export PATH="$HOME/.local/bin:$PATH"
source .venv/bin/activate

echo -e "${GREEN}Step 2: Updating agent YAML files...${NC}"

# Backup original files
echo "  Creating backups..."
find . -name "*_agent.yaml" -exec cp {} {}.backup \;

# Update model references in all agent YAML files
echo "  Updating data_processing_agent.yaml..."
sed -i "s|model_id: ${OLD_MODEL}|model_id: ${NEW_MODEL}|g" \
  data_processing/agents/data_processing_agent.yaml

echo "  Updating document_validate.yaml..."
sed -i "s|model_id: ${OLD_MODEL}|model_id: ${NEW_MODEL}|g" \
  document_validate/agents/document_validate.yaml

echo "  Updating cross_validation.yaml..."
sed -i "s|model_id: ${OLD_MODEL}|model_id: ${NEW_MODEL}|g" \
  cross_validation/agents/cross_validation.yaml

echo "  Updating final_decision.yaml..."
sed -i "s|model_id: ${OLD_MODEL}|model_id: ${NEW_MODEL}|g" \
  final_decision/agents/final_decision.yaml

echo -e "${GREEN}✅ All YAML files updated${NC}"
echo ""

# Verify changes
echo -e "${GREEN}Step 3: Verifying changes...${NC}"
echo "Checking model_id in YAML files:"
grep -r "model_id:" data_processing/agents/data_processing_agent.yaml | head -1
grep -r "model_id:" document_validate/agents/document_validate.yaml | head -1
grep -r "model_id:" cross_validation/agents/cross_validation.yaml | head -1
grep -r "model_id:" final_decision/agents/final_decision.yaml | head -1
echo ""

echo -e "${YELLOW}Step 4: Deleting old agents...${NC}"
echo "This may show 'not found' errors if agents don't exist - that's OK"
echo ""

orchestrate agents delete document_processor 2>/dev/null || echo "  (document_processor not found, skipping)"
orchestrate agents delete validate_document_agent 2>/dev/null || echo "  (validate_document_agent not found, skipping)"
orchestrate agents delete cross_validation 2>/dev/null || echo "  (cross_validation not found, skipping)"
orchestrate agents delete final_loan_decision 2>/dev/null || echo "  (final_loan_decision not found, skipping)"

echo ""
echo -e "${GREEN}Step 5: Redeploying agents with updated models...${NC}"
echo ""

echo -e "${BLUE}[1/4] Deploying Document Processor Agent...${NC}"
orchestrate tools import -k python -f data_processing/tools/data_processing_tools.py \
  --app-id wxai_credential --app-id cos_credential
orchestrate agents import -f data_processing/agents/data_processing_agent.yaml
echo -e "${GREEN}✅ Document Processor Agent deployed${NC}"
echo ""

echo -e "${BLUE}[2/4] Deploying Document Validator Agent...${NC}"
orchestrate tools import -k python -f document_validate/tools/validate_document.py \
  --app-id wxai_credential --app-id cos_credential
orchestrate agents import -f document_validate/agents/document_validate.yaml
echo -e "${GREEN}✅ Document Validator Agent deployed${NC}"
echo ""

echo -e "${BLUE}[3/4] Deploying Cross-Validation Agent...${NC}"
orchestrate agents import -f cross_validation/agents/cross_validation.yaml
echo -e "${GREEN}✅ Cross-Validation Agent deployed${NC}"
echo ""

echo -e "${BLUE}[4/4] Deploying Final Decision Agent...${NC}"
orchestrate tools import -k python -f final_decision/tools/final_decision_tools.py \
  --app-id cos_credential
orchestrate agents import -f final_decision/agents/final_decision.yaml
echo -e "${GREEN}✅ Final Decision Agent deployed${NC}"
echo ""

echo -e "${GREEN}Step 6: Verifying deployment...${NC}"
orchestrate agents list | grep -E "document_processor|validate_document|cross_validation|final_loan_decision"
echo ""

echo -e "${GREEN}Step 7: Extracting new agent IDs...${NC}"
orchestrate agents list --output json > /tmp/agents_list.json 2>/dev/null || orchestrate agents list > /tmp/agents_list.txt

# Try to extract agent IDs
echo "Extracting agent IDs from deployment..."
DOC_PROCESSOR_ID=$(orchestrate agents list | grep document_processor | awk '{print $NF}' | head -1)
VALIDATE_DOC_ID=$(orchestrate agents list | grep validate_document_agent | awk '{print $NF}' | head -1)
FINAL_DECISION_ID=$(orchestrate agents list | grep final_loan_decision | awk '{print $NF}' | head -1)

echo ""
echo -e "${YELLOW}New Agent IDs:${NC}"
echo "  DOC_PROCESSOR_AGENT_ID=${DOC_PROCESSOR_ID}"
echo "  DOCUMENT_VALIDATION_AGENT_ID=${VALIDATE_DOC_ID}"
echo "  FINAL_DECISION_AGENT_ID=${FINAL_DECISION_ID}"
echo ""

# Update backend .env file if IDs are found
if [ -n "$DOC_PROCESSOR_ID" ] && [ -n "$VALIDATE_DOC_ID" ] && [ -n "$FINAL_DECISION_ID" ]; then
  echo -e "${GREEN}Step 8: Updating backend .env file...${NC}"
  ENV_FILE="/home/qvidal01/projects/ibm-dsce-sample-apps/loan-preprocessing-agents/.env"

  sed -i "s/DOC_PROCESSOR_AGENT_ID=.*/DOC_PROCESSOR_AGENT_ID=${DOC_PROCESSOR_ID}/" "$ENV_FILE"
  sed -i "s/DOCUMENT_VALIDATION_AGENT_ID=.*/DOCUMENT_VALIDATION_AGENT_ID=${VALIDATE_DOC_ID}/" "$ENV_FILE"
  sed -i "s/FINAL_DECISION_AGENT_ID=.*/FINAL_DECISION_AGENT_ID=${FINAL_DECISION_ID}/" "$ENV_FILE"

  echo -e "${GREEN}✅ Backend .env updated${NC}"
else
  echo -e "${YELLOW}⚠️  Could not extract agent IDs automatically${NC}"
  echo "Run 'orchestrate agents list' to get IDs manually"
fi

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}✅ Agent Model Fix Complete!${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Restart the backend server (if it's running)"
echo "2. Submit a new test application:"
echo "   cd /home/qvidal01/projects/ibm-dsce-sample-apps/loan-preprocessing-agents"
echo "   ./test_application.sh"
echo ""
echo "3. Monitor the logs to verify agents are working:"
echo "   curl -H \"Authorization: Bearer <TOKEN>\" \\"
echo "     http://127.0.0.1:8000/get_logs/<APP_ID> | python3 -m json.tool"
echo ""
echo -e "${GREEN}All agents are now using: ${NEW_MODEL}${NC}"
echo ""
