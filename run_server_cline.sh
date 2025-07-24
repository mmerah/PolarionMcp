#!/bin/bash
# Startup script for Polarion MCP Server - Cline Compatible Mode

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Polarion MCP Server Launcher (Cline Mode)${NC}"
echo ""

# Disable Copilot Studio mode to use standard MCP protocol
export COPILOT_STUDIO_MODE=false

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${BLUE}Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source .venv/bin/activate

# Install/update dependencies
echo -e "${BLUE}Installing dependencies...${NC}"
pip install -q -e .

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${RED}⚠️  Warning: .env file not found!${NC}"
    echo "Please create a .env file with:"
    echo "  POLARION_URL=your-polarion-url"
    echo "  POLARION_USER=your-username"
    echo "  POLARION_TOKEN=your-token"
    echo ""
fi

# Parse command line arguments
HOST="0.0.0.0"
PORT="8000"
EXTRA_ARGS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --log-level)
            EXTRA_ARGS="$EXTRA_ARGS --log-level $2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}Starting MCP Server in Standard MCP Mode (Cline-compatible)...${NC}"
echo -e "Host: ${HOST}"
echo -e "Port: ${PORT}"
echo -e "Local URL: http://localhost:${PORT}/mcp"
echo ""

# Start the server with Cline-compatible configuration
echo -e "${BLUE}Starting MCP server with FastMCP (Standard HTTP transport)...${NC}"
python -m mcp_server.main_cline --host "$HOST" --port "$PORT" $EXTRA_ARGS