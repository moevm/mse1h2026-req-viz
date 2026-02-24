#!/bin/bash
# Start the FastAPI development server for the Ecosystem Analyzer module
# The server will automatically reload on code changes (--reload flag)
# Runs on port 8000 (http://localhost:8000)
uvicorn ecosystem_analyzer.main:app --reload --port 8000
