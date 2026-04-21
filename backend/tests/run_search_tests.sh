#!/usr/bin/env bash
# Run FTS integration tests against the dev PostgreSQL database
# Requires: docker compose dev stack running with the database populated
export DATABASE_URL="postgresql://wfm:wfm@localhost:5435/wfm"
cd backend && python -m pytest tests/test_signal_search.py -v