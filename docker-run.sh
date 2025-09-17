#!/bin/bash
# Simple Docker run script for AutoSummary

set -e

IMAGE_NAME="autosummary"
CONTAINER_NAME="autosummary-app"
PORT="8501"

case "$1" in
    build)
        echo "🔨 Building Docker image..."
        docker build -t $IMAGE_NAME .
        echo "✅ Docker image built successfully!"
        ;;
    start)
        echo "🚀 Starting AutoSummary container..."
        # Stop and remove existing container if it exists
        docker stop $CONTAINER_NAME 2>/dev/null || true
        docker rm $CONTAINER_NAME 2>/dev/null || true
        
        # Run the container
        docker run -d \
            --name $CONTAINER_NAME \
            -p $PORT:8501 \
            $IMAGE_NAME
        
        echo "✅ AutoSummary is running at http://localhost:$PORT"
        ;;
    stop)
        echo "🛑 Stopping AutoSummary container..."
        docker stop $CONTAINER_NAME 2>/dev/null || true
        docker rm $CONTAINER_NAME 2>/dev/null || true
        echo "✅ Container stopped and removed"
        ;;
    logs)
        echo "📋 Showing container logs..."
        docker logs -f $CONTAINER_NAME
        ;;
    *)
        echo "Usage: $0 {build|start|stop|logs}"
        echo ""
        echo "Commands:"
        echo "  build  - Build the Docker image"
        echo "  start  - Start the application container"
        echo "  stop   - Stop and remove the container"
        echo "  logs   - Show container logs"
        exit 1
        ;;
esac
