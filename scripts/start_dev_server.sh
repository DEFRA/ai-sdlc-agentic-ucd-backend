#!/bin/bash

# Exit on error
set -e

# Set default log level with both uppercase and lowercase versions
LOG_LEVEL_UPPER=${LOG_LEVEL:-INFO}
LOG_LEVEL_LOWER=$(echo $LOG_LEVEL_UPPER | tr '[:upper:]' '[:lower:]')

# Create logs directory
mkdir -p logs
LOGFILE="$(pwd)/logs/app.log"

# Setup shell logging with timestamps (using Mac-compatible date format)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting development environment script" > "$LOGFILE"

# Log function to write to both console and log file
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOGFILE"
}

log "Starting development environment..."

# Check if Docker is running
# if ! docker info > /dev/null 2>&1; then
#     log "Error: Docker is not running. Please start Docker and try again."
#     exit 1
# fi

# Start dependent services
# log "Starting dependent services with Docker Compose..."
# docker-compose up -d >> "$LOGFILE" 2>&1

# Wait for services to be ready
log "Waiting for services to be ready..."
sleep 5

# Set environment variables for local development
export PORT=8085
export LOCALSTACK_ENDPOINT=http://localhost:4566
export MONGO_URI=mongodb://localhost:27017/
export ENV=dev
export LOG_LEVEL=$LOG_LEVEL_UPPER

# Setup logging if in dev environment
if [ "$ENV" = "dev" ]; then
    log "Setting up logging to $LOGFILE with level $LOG_LEVEL_UPPER"
fi

# Load application environment variables
log "Loading environment variables..."
if [ -f compose/aws.env ]; then
    export $(grep -v '^#' compose/aws.env | xargs)
else
    log "Error: compose/aws.env file not found. This file is required."
    exit 1
fi

log "Loading secrets..."
if [ -f compose/secrets.env ]; then
    export $(grep -v '^#' compose/secrets.env | xargs)
else
    log "Error: compose/secrets.env file not found. This file is required."
    exit 1
fi

# Check Python virtual environment exists
if [ ! -d ".venv" ]; then
    log "No Python virtual environment found. Please setup your environment as per the README."
    exit 1
fi

# Start the application
log "Starting FastAPI application with log level $LOG_LEVEL_UPPER (uvicorn: $LOG_LEVEL_LOWER)..."
log "Logs will be saved to: $LOGFILE"
# Use lowercase log level for uvicorn
uvicorn app.main:app --host 0.0.0.0 --port $PORT --reload --log-level=$LOG_LEVEL_LOWER --log-config=logging-dev.json >> "$LOGFILE" 2>&1

# Cleanup function
cleanup() {
    log "Shutting down..."
    deactivate
    log "Development server stopped."
}

# Register cleanup function
trap cleanup EXIT
