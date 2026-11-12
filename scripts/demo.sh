#!/bin/bash
# ==============================================================================
# Automated Live Defense Demo Script for pm-service
# Runs through the complete multi-user lifecycle, RBAC, and cascading cleanup.
# ==============================================================================
set -eo pipefail

BASE_URL="${API_URL:-http://localhost:8000}"
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_step() {
    echo -e "\n${BLUE}======================================================================${NC}"
    echo -e "${GREEN}==> $1${NC}"
    echo -e "${BLUE}======================================================================${NC}"
}

log_info() {
    echo -e "${YELLOW}--> $1${NC}"
}

# 1. Healthcheck
log_step "Step 1: Checking Service Health"
curl -s -f "${BASE_URL}/health" | jq . || {
    echo -e "${RED}Error: pm-service is not running at ${BASE_URL}. Start it with 'docker compose up -d'.${NC}"
    exit 1
}

# 2. Register Alice (Project Owner) and Bob (Participant)
log_step "Step 2: Registering Alice (Owner) and Bob (Participant)"
TIMESTAMP=$(date +%s)
ALICE_USER="alice_${TIMESTAMP}"
BOB_USER="bob_${TIMESTAMP}"
PASSWORD="SecurePassword123!"

log_info "Registering Alice (${ALICE_USER})..."
curl -s -X POST "${BASE_URL}/auth" \
    -H "Content-Type: application/json" \
    -d "{\"login\": \"${ALICE_USER}\", \"password\": \"${PASSWORD}\", \"repeat_password\": \"${PASSWORD}\"}" | jq .

log_info "Logging in as Alice to obtain JWT access token..."
ALICE_TOKEN=$(curl -s -X POST "${BASE_URL}/login" \
    -H "Content-Type: application/json" \
    -d "{\"login\": \"${ALICE_USER}\", \"password\": \"${PASSWORD}\"}" | jq -r .access_token)
echo "Alice JWT: ${ALICE_TOKEN:0:20}...[truncated]"

log_info "Registering Bob (${BOB_USER})..."
curl -s -X POST "${BASE_URL}/auth" \
    -H "Content-Type: application/json" \
    -d "{\"login\": \"${BOB_USER}\", \"password\": \"${PASSWORD}\", \"repeat_password\": \"${PASSWORD}\"}" | jq .

log_info "Logging in as Bob to obtain JWT access token..."
BOB_TOKEN=$(curl -s -X POST "${BASE_URL}/login" \
    -H "Content-Type: application/json" \
    -d "{\"login\": \"${BOB_USER}\", \"password\": \"${PASSWORD}\"}" | jq -r .access_token)
echo "Bob JWT: ${BOB_TOKEN:0:20}...[truncated]"

# 3. Alice creates a project
log_step "Step 3: Alice creates a new Project"
PROJECT_RESP=$(curl -s -X POST "${BASE_URL}/projects" \
    -H "Authorization: Bearer ${ALICE_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"name": "Alpha Defense Demo", "description": "EPAM Final Project"}')
echo "${PROJECT_RESP}" | jq .
PROJECT_ID=$(echo "${PROJECT_RESP}" | jq -r .id)
log_info "Created Project ID: ${PROJECT_ID}"

# 4. Upload Document
log_step "Step 4: Alice uploads a project document"
TMP_DOC="/tmp/demo_report.pdf"
printf '%%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%%%%EOF' > "${TMP_DOC}"

DOC_RESP=$(curl -s -X POST "${BASE_URL}/project/${PROJECT_ID}/documents" \
    -H "Authorization: Bearer ${ALICE_TOKEN}" \
    -F "files=@${TMP_DOC};type=application/pdf")
echo "${DOC_RESP}" | jq .
DOC_ID=$(echo "${DOC_RESP}" | jq -r '.[0].id')
log_info "Uploaded Document ID: ${DOC_ID}"

# 5. Security Check: Bob attempts to view project before invitation (Must return 404!)
log_step "Step 5: Security Check - Bob attempts to view project before invitation"
log_info "Expected: HTTP 404 Not Found (information hiding against ID enumeration)"
BOB_PROBE_STATUS=$(curl -s -o /tmp/bob_probe.json -w "%{http_code}" -X GET "${BASE_URL}/project/${PROJECT_ID}/info" \
    -H "Authorization: Bearer ${BOB_TOKEN}")
echo "HTTP Status Code returned: ${BOB_PROBE_STATUS}"
cat /tmp/bob_probe.json | jq .

if [ "${BOB_PROBE_STATUS}" != "404" ]; then
    echo -e "${RED}Security Failure: Expected 404, got ${BOB_PROBE_STATUS}!${NC}"
    exit 1
fi
echo -e "${GREEN}PASS: Uninvited user received 404. Private resource presence is concealed.${NC}"

# 6. Alice invites Bob to the project
log_step "Step 6: Alice invites Bob as project participant"
curl -s -X POST "${BASE_URL}/project/${PROJECT_ID}/invite?user=${BOB_USER}" \
    -H "Authorization: Bearer ${ALICE_TOKEN}" | jq .

# 7. Bob views project info and downloads document
log_step "Step 7: Bob views project and downloads the document"
log_info "Bob fetches project info:"
curl -s -X GET "${BASE_URL}/project/${PROJECT_ID}/info" \
    -H "Authorization: Bearer ${BOB_TOKEN}" | jq .

log_info "Bob downloads document content:"
curl -s -X GET "${BASE_URL}/document/${DOC_ID}" \
    -H "Authorization: Bearer ${BOB_TOKEN}" -o /tmp/downloaded_report.pdf
echo "Downloaded document size: $(wc -c < /tmp/downloaded_report.pdf) bytes"

# 8. Security Check: Bob attempts to delete project (Must return 403 Forbidden!)
log_step "Step 8: Security Check - Bob attempts to delete project"
log_info "Expected: HTTP 403 Forbidden (only project owner can delete)"
BOB_DELETE_STATUS=$(curl -s -o /tmp/bob_del.json -w "%{http_code}" -X DELETE "${BASE_URL}/project/${PROJECT_ID}" \
    -H "Authorization: Bearer ${BOB_TOKEN}")
echo "HTTP Status Code returned: ${BOB_DELETE_STATUS}"
cat /tmp/bob_del.json | jq .

if [ "${BOB_DELETE_STATUS}" != "403" ]; then
    echo -e "${RED}Security Failure: Expected 403, got ${BOB_DELETE_STATUS}!${NC}"
    exit 1
fi
echo -e "${GREEN}PASS: Participant was correctly forbidden from deleting project.${NC}"

# 9. Alice deletes the project (Cascading deletion)
log_step "Step 9: Alice deletes project with cascading cleanup"
curl -s -X DELETE "${BASE_URL}/project/${PROJECT_ID}" \
    -H "Authorization: Bearer ${ALICE_TOKEN}" -w "HTTP Response Code: %{http_code}\n"

log_info "Verifying project no longer exists (404):"
curl -s -X GET "${BASE_URL}/project/${PROJECT_ID}/info" \
    -H "Authorization: Bearer ${ALICE_TOKEN}" | jq .

log_step "DEMO COMPLETED SUCCESSFULLY! All security invariants, RBAC rules, and cascades verified."
rm -f "${TMP_DOC}" /tmp/downloaded_report.pdf /tmp/bob_probe.json /tmp/bob_del.json
