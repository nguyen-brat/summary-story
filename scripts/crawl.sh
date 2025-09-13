#!/bin/bash
# Script to run the web crawler

echo "🕷️ Starting AutoSummary Web Crawler..."
echo "This will crawl stories and save them to the story/ directory"
echo

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please run 'uv run python setup.py' first"
    exit 1
fi

# Run the crawler
echo "Running crawler..."
uv run python src/crawl/crawling.py

echo "✅ Crawling complete! Check the story/ directory for results."
