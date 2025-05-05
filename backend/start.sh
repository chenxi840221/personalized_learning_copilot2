#!/bin/bash
# Start script for the Personalized Learning Co-pilot backend
# Use this script to ensure the server runs on the correct port

echo "Starting Personalized Learning Co-pilot backend on port 8001..."
python -m uvicorn app:app --host 0.0.0.0 --port 8001 --reload