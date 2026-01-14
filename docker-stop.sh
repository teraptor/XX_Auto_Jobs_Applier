#!/bin/bash
#
# Stop Docker services for XX Auto Jobs Applier
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}===============================================${NC}"
echo -e "${YELLOW}Stopping XX Auto Jobs Applier Docker Services${NC}"
echo -e "${YELLOW}===============================================${NC}\n"

# Stop all services
echo "Stopping all services..."
docker-compose down

echo -e "${GREEN}✓ All services stopped${NC}\n"

# Optional: Remove volumes if requested
if [ "$1" == "--clean" ]; then
    echo -e "${RED}Removing all volumes (this will delete all data)...${NC}"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v
        echo -e "${GREEN}✓ All volumes removed${NC}"
    else
        echo "Volumes preserved."
    fi
fi

# Optional: Remove images if requested
if [ "$1" == "--clean-all" ]; then
    echo -e "${RED}Removing all containers, volumes, and images...${NC}"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v --rmi all
        echo -e "${GREEN}✓ All containers, volumes, and images removed${NC}"
    else
        echo "Cleanup cancelled."
    fi
fi

echo -e "\n${GREEN}Services stopped.${NC}"