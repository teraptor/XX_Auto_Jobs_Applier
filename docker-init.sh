#!/bin/bash
#
# Initialize Docker environment for XX Auto Jobs Applier
# This script sets up the database, creates initial tenant and user
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}Initializing XX Auto Jobs Applier${NC}"
echo -e "${BLUE}===============================================${NC}\n"

# Check if services are running
if ! docker-compose ps | grep -q "postgres.*Up"; then
    echo -e "${YELLOW}PostgreSQL is not running. Starting services...${NC}"
    ./docker-start.sh
    sleep 5
fi

# Load environment variables
source .env

echo -e "${GREEN}Step 1: Database initialization${NC}"
echo "Waiting for PostgreSQL to be ready..."
until docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo -e "\n${GREEN}✓ PostgreSQL is ready${NC}\n"

# Run migrations if alembic directory exists
if [ -d "alembic" ]; then
    echo "Running database migrations..."
    docker run --rm \
        --network xx-autojobs_xx-network \
        -v "$PWD":/app \
        -w /app \
        -e DATABASE_URL="postgresql://postgres:postgres@postgres:5432/autoapplyer" \
        python:3.11-slim sh -c "pip install alembic psycopg2-binary asyncpg && alembic upgrade head"
    echo -e "${GREEN}✓ Migrations completed${NC}\n"
fi

echo -e "${GREEN}Step 2: Create test tenant and user${NC}"

# Prompt for tenant information
read -p "Enter tenant name (e.g., 'Test Company'): " TENANT_NAME
read -p "Enter tenant slug (e.g., 'test-company'): " TENANT_SLUG

# Prompt for user information
read -p "Enter user email: " USER_EMAIL
read -p "Enter user full name: " USER_NAME
read -p "Enter HH.ru login: " HH_LOGIN
read -sp "Enter HH.ru password: " HH_PASSWORD
echo

echo -e "\n${YELLOW}Creating tenant and user...${NC}"

# Create Python script for initialization
cat > /tmp/init_tenant.py << 'EOF'
import asyncio
import asyncpg
import sys
import uuid
from cryptography.fernet import Fernet

async def create_tenant_and_user():
    # Get parameters from command line
    db_url = sys.argv[1]
    tenant_name = sys.argv[2]
    tenant_slug = sys.argv[3]
    user_email = sys.argv[4]
    user_name = sys.argv[5]
    hh_login = sys.argv[6]
    hh_password = sys.argv[7]
    encryption_key = sys.argv[8]

    # Connect to database
    conn = await asyncpg.connect(db_url)

    try:
        # Create tenant
        tenant_id = str(uuid.uuid4())
        await conn.execute("""
            INSERT INTO tenants (id, name, slug, status)
            VALUES ($1, $2, $3, 'active')
            ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
        """, tenant_id, tenant_name, tenant_slug)

        # Get tenant_id if already exists
        row = await conn.fetchrow("SELECT id FROM tenants WHERE slug = $1", tenant_slug)
        if row:
            tenant_id = row['id']

        print(f"✓ Tenant created: {tenant_id}")

        # Encrypt password
        cipher = Fernet(encryption_key.encode())
        encrypted_password = cipher.encrypt(hh_password.encode()).decode()

        # Create user
        user_id = str(uuid.uuid4())
        await conn.execute("""
            INSERT INTO users (id, tenant_id, email, full_name, hh_login, hh_password_encrypted, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, true)
            ON CONFLICT (tenant_id, email) DO UPDATE
            SET full_name = EXCLUDED.full_name,
                hh_login = EXCLUDED.hh_login,
                hh_password_encrypted = EXCLUDED.hh_password_encrypted
            RETURNING id
        """, user_id, tenant_id, user_email, user_name, hh_login, encrypted_password)

        # Get user_id if already exists
        row = await conn.fetchrow("""
            SELECT id FROM users WHERE tenant_id = $1 AND email = $2
        """, tenant_id, user_email)
        if row:
            user_id = row['id']

        print(f"✓ User created: {user_id}")

        # Return IDs
        print(f"\nTenant ID: {tenant_id}")
        print(f"User ID: {user_id}")

        return tenant_id, user_id

    finally:
        await conn.close()

if __name__ == "__main__":
    tenant_id, user_id = asyncio.run(create_tenant_and_user())
    # Write to file for later use
    with open("/tmp/tenant_user_ids.txt", "w") as f:
        f.write(f"{tenant_id}\n{user_id}")
EOF

# Run the initialization script
docker run --rm \
    --network xx-autojobs_xx-network \
    -v /tmp:/tmp \
    python:3.11-slim sh -c "
        pip install asyncpg cryptography &&
        python /tmp/init_tenant.py \
            'postgresql://postgres:postgres@postgres:5432/autoapplyer' \
            '$TENANT_NAME' \
            '$TENANT_SLUG' \
            '$USER_EMAIL' \
            '$USER_NAME' \
            '$HH_LOGIN' \
            '$HH_PASSWORD' \
            '$ENCRYPTION_KEY'
    "

# Read the IDs
if [ -f "/tmp/tenant_user_ids.txt" ]; then
    TENANT_ID=$(head -n 1 /tmp/tenant_user_ids.txt)
    USER_ID=$(tail -n 1 /tmp/tenant_user_ids.txt)
    rm /tmp/tenant_user_ids.txt
    rm /tmp/init_tenant.py

    echo -e "\n${GREEN}Step 3: Load search configuration${NC}"

    # Check if search_config.yaml exists
    if [ -f "data_folder/search_config/search_config.yaml" ]; then
        echo "Loading search configuration..."
        docker run --rm \
            --network xx-autojobs_xx-network \
            -v "$PWD":/app \
            -w /app \
            -e DATABASE_URL="postgresql://postgres:postgres@postgres:5432/autoapplyer" \
            python:3.11-slim sh -c "
                pip install asyncpg pyyaml &&
                python scripts/load_search_config.py '$TENANT_ID' '$USER_ID' data_folder/search_config/search_config.yaml
            "
        echo -e "${GREEN}✓ Search configuration loaded${NC}\n"
    else
        echo -e "${YELLOW}No search configuration found. You'll need to create one.${NC}\n"
    fi

    echo -e "${GREEN}===============================================${NC}"
    echo -e "${GREEN}Initialization completed successfully!${NC}"
    echo -e "${GREEN}===============================================${NC}\n"

    echo -e "${BLUE}Your credentials:${NC}"
    echo "  Tenant ID: $TENANT_ID"
    echo "  User ID:   $USER_ID"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Create a search configuration (if not already done):"
    echo "   python scripts/load_search_config.py $TENANT_ID $USER_ID <config_file>"
    echo ""
    echo "2. Enqueue a job:"
    echo "   python scripts/enqueue_job.py $TENANT_ID $USER_ID"
    echo ""
    echo "3. Monitor the task:"
    echo "   python scripts/monitor_task.py <task_id>"
    echo ""
    echo "4. View applications:"
    echo "   python scripts/view_applications.py $TENANT_ID $USER_ID"
else
    echo -e "${RED}Failed to create tenant and user${NC}"
fi