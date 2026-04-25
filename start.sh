#!/usr/bin/env bash
# Apex Platform — one-command setup script
# Usage: ./start.sh
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Apex Platform Setup ===${NC}"
echo ""

# 1. Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker is not installed.${NC}"
    echo "Install Docker Desktop from https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}ERROR: Docker daemon is not running.${NC}"
    echo "Start Docker Desktop and try again."
    exit 1
fi

echo -e "${GREEN}✓ Docker detected${NC}"

# 2. Copy .env if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}Created .env from .env.example${NC}"
    echo ""
    echo "IMPORTANT: Open .env and fill in your API keys before continuing."
    echo "Required keys:"
    echo "  - ANTHROPIC_API_KEY  (https://console.anthropic.com)"
    echo "  - SUPABASE_URL + SUPABASE_ANON_KEY + SUPABASE_SERVICE_ROLE_KEY + DATABASE_URL"
    echo "  - OPENAI_API_KEY     (for embeddings)"
    echo ""
    echo "Optional (free tier, improves signal quality):"
    echo "  - NEWSDATA_API_KEY   (https://newsdata.io/register)"
    echo "  - GNEWS_API_KEY      (https://gnews.io/register)"
    echo "  - PDL_API_KEY        (https://dashboard.peopledatalabs.com/signup)"
    echo "  - HUNTER_API_KEY     (https://hunter.io/users/sign_up)"
    echo "  - ADZUNA_APP_ID/KEY  (https://developer.adzuna.com)"
    echo ""
    read -p "Press Enter when .env is filled in..."
fi

echo -e "${GREEN}✓ .env configured${NC}"

# 3. Build and start services
echo ""
echo "Building and starting services (this takes 2-5 minutes on first run)..."
docker-compose up --build -d

# 4. Wait for backend to be healthy
echo "Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is ready${NC}"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo -e "${RED}Backend did not start within 60s. Check: docker-compose logs backend${NC}"
        exit 1
    fi
    sleep 2
done

# 5. Seed demo data
echo "Seeding demo data (5 companies, 5 signals, 3 opportunities)..."
if ! docker-compose exec backend python -m app.db.seeds.seed_demo 2>&1; then
    echo "WARNING: Demo seed encountered an error. This is OK if data already exists."
    echo "To debug: docker-compose exec backend python -m app.db.seeds.seed_demo"
fi

echo ""
echo -e "${GREEN}=== Apex is ready! ===${NC}"
echo ""
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000/api/v1/health"
echo "  API docs: http://localhost:8000/docs"
echo ""
echo "Log in with the credentials you set in .env (OWNER_EMAIL / OWNER_PASSWORD)"
echo "Then click 'Run Pipeline' on the dashboard to ingest your first signals."
