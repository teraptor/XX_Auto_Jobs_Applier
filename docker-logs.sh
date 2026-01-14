#!/bin/bash
#
# View logs for Docker services
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

# Default service
SERVICE=$1
TAIL_LINES=${2:-100}

show_help() {
    echo -e "${BLUE}Usage: ./docker-logs.sh [service] [lines]${NC}"
    echo ""
    echo "Services:"
    echo "  api       - View API service logs"
    echo "  worker-1  - View Worker 1 logs"
    echo "  worker-2  - View Worker 2 logs"
    echo "  postgres  - View PostgreSQL logs"
    echo "  redis     - View Redis logs"
    echo "  nginx     - View Nginx logs"
    echo "  all       - View all service logs"
    echo ""
    echo "Options:"
    echo "  lines     - Number of lines to tail (default: 100)"
    echo "  -f        - Follow log output (real-time)"
    echo ""
    echo "Examples:"
    echo "  ./docker-logs.sh api          # View last 100 lines of API logs"
    echo "  ./docker-logs.sh worker-1 50  # View last 50 lines of Worker 1 logs"
    echo "  ./docker-logs.sh all -f       # Follow all logs in real-time"
}

if [ -z "$SERVICE" ] || [ "$SERVICE" == "--help" ] || [ "$SERVICE" == "-h" ]; then
    show_help
    exit 0
fi

# Check if following logs
FOLLOW=""
if [ "$SERVICE" == "-f" ] || [ "$2" == "-f" ] || [ "$3" == "-f" ]; then
    FOLLOW="-f"
fi

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}XX Auto Jobs Applier - Log Viewer${NC}"
echo -e "${GREEN}===============================================${NC}\n"

case $SERVICE in
    api|worker-1|worker-2|postgres|redis|nginx)
        echo -e "${BLUE}Viewing logs for: $SERVICE${NC}"
        if [ -n "$FOLLOW" ]; then
            echo -e "${YELLOW}Following logs (Ctrl+C to stop)...${NC}\n"
            docker-compose logs -f $SERVICE
        else
            echo -e "${YELLOW}Showing last $TAIL_LINES lines...${NC}\n"
            docker-compose logs --tail=$TAIL_LINES $SERVICE
        fi
        ;;
    all)
        echo -e "${BLUE}Viewing logs for all services${NC}"
        if [ -n "$FOLLOW" ]; then
            echo -e "${YELLOW}Following logs (Ctrl+C to stop)...${NC}\n"
            docker-compose logs -f
        else
            echo -e "${YELLOW}Showing last $TAIL_LINES lines...${NC}\n"
            docker-compose logs --tail=$TAIL_LINES
        fi
        ;;
    *)
        echo -e "${RED}Unknown service: $SERVICE${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac