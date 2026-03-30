#!/bin/bash
set -e

echo "Starting HireLogic Docker stack..."

if [ -z "$GEMINI_API_KEY" ]; then
  echo "ERROR: GEMINI_API_KEY not set"
  echo "Export it: export GEMINI_API_KEY=your_key"
  exit 1
fi

docker compose up -d db

echo "Waiting for database to be healthy..."
sleep 10

docker compose run --rm server alembic upgrade head
docker compose run --rm server python -m app.db.seed.seed_db
docker compose up -d --build

echo ""
echo "✅ HireLogic is running!"
echo ""
echo "  App:    http://localhost:3000"
echo "  API:    http://localhost:8000"
echo "  ADK UI: http://localhost:8080"
echo ""
echo "Login: recruiter_alice / pass1234"
