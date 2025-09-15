#!/bin/bash

# Docker run script for AutoSummary
# This script provides easy commands to run the application with Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_help() {
    echo -e "${BLUE}AutoSummary Docker Runner${NC}"
    echo -e "${BLUE}========================${NC}"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  build       Build the Docker image"
    echo "  run         Run the application (development mode)"
    echo "  start       Start with docker-compose (detached)"
    echo "  stop        Stop the application"
    echo "  restart     Restart the application"
    echo "  logs        View application logs"
    echo "  shell       Open a shell in the container"
    echo "  clean       Clean up containers and images"
    echo "  setup       Initial setup (create .env file)"
    echo "  prod        Run in production mode with nginx"
    echo ""
    echo "Examples:"
    echo "  $0 setup                    # Initial setup"
    echo "  $0 build                    # Build image"
    echo "  $0 run                      # Run in development"
    echo "  $0 start                    # Start detached"
    echo "  $0 prod                     # Production mode"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker is not installed${NC}"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo -e "${RED}❌ Docker Compose is not installed${NC}"
        exit 1
    fi
}

create_env_file() {
    if [ ! -f .env ]; then
        echo -e "${YELLOW}📝 Creating .env file...${NC}"
        echo ""
        read -p "Enter your Google Gemini API key: " api_key
        
        if [ -z "$api_key" ]; then
            echo -e "${RED}❌ No API key provided${NC}"
            exit 1
        fi
        
        cat > .env << EOF
# AutoSummary Environment Variables
GOOGLE_API_KEY=$api_key

# Optional: Chrome options (already set in docker-compose.yml)
# CHROME_OPTIONS=--headless --no-sandbox --disable-dev-shm-usage

# Optional: Streamlit configuration
# STREAMLIT_SERVER_PORT=8501
# STREAMLIT_SERVER_HEADLESS=true
EOF
        
        echo -e "${GREEN}✅ Created .env file${NC}"
        echo -e "${YELLOW}⚠️  Keep your .env file secure and don't commit it to version control!${NC}"
    else
        echo -e "${GREEN}✅ .env file already exists${NC}"
    fi
}

create_directories() {
    echo -e "${YELLOW}📁 Creating necessary directories...${NC}"
    mkdir -p story summary
    touch crawl_history.json
    echo -e "${GREEN}✅ Directories created${NC}"
}

build_image() {
    echo -e "${BLUE}🔨 Building Docker image...${NC}"
    docker build -t autosummary:latest .
    echo -e "${GREEN}✅ Image built successfully${NC}"
}

run_dev() {
    echo -e "${BLUE}🚀 Running AutoSummary in development mode...${NC}"
    docker-compose up --build
}

start_detached() {
    echo -e "${BLUE}🚀 Starting AutoSummary in detached mode...${NC}"
    docker-compose up -d --build
    echo -e "${GREEN}✅ Application started${NC}"
    echo -e "${YELLOW}📱 Access the app at: http://localhost:8501${NC}"
}

stop_app() {
    echo -e "${YELLOW}🛑 Stopping AutoSummary...${NC}"
    docker-compose down
    echo -e "${GREEN}✅ Application stopped${NC}"
}

restart_app() {
    echo -e "${YELLOW}🔄 Restarting AutoSummary...${NC}"
    docker-compose restart
    echo -e "${GREEN}✅ Application restarted${NC}"
}

show_logs() {
    echo -e "${BLUE}📋 Showing application logs...${NC}"
    docker-compose logs -f autosummary
}

open_shell() {
    echo -e "${BLUE}🐚 Opening shell in container...${NC}"
    docker-compose exec autosummary /bin/bash
}

cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up Docker resources...${NC}"
    docker-compose down --volumes --remove-orphans
    docker image prune -f
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

run_production() {
    echo -e "${BLUE}🏭 Starting AutoSummary in production mode...${NC}"
    docker-compose --profile production up -d --build
    echo -e "${GREEN}✅ Production environment started${NC}"
    echo -e "${YELLOW}🌐 Access the app at: http://localhost${NC}"
    echo -e "${YELLOW}📱 Direct app access: http://localhost:8501${NC}"
}

# Main script logic
case "${1:-help}" in
    "build")
        check_docker
        create_directories
        build_image
        ;;
    "run")
        check_docker
        create_directories
        run_dev
        ;;
    "start")
        check_docker
        create_directories
        start_detached
        ;;
    "stop")
        check_docker
        stop_app
        ;;
    "restart")
        check_docker
        restart_app
        ;;
    "logs")
        check_docker
        show_logs
        ;;
    "shell")
        check_docker
        open_shell
        ;;
    "clean")
        check_docker
        cleanup
        ;;
    "setup")
        check_docker
        create_env_file
        create_directories
        ;;
    "prod")
        check_docker
        create_directories
        run_production
        ;;
    "help"|*)
        print_help
        ;;
esac
