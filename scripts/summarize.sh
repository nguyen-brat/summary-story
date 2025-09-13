#!/bin/bash
# Script to run the summarization workflow

echo "🤖 Starting AutoSummary AI Workflow..."
echo "This will process stories and generate summaries"
echo

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please run 'uv run python setup.py' first"
    exit 1
fi

# Check if story directory exists and has content
if [ ! -d "story" ] || [ -z "$(ls -A story)" ]; then
    echo "⚠️  No stories found in story/ directory"
    echo "Please run the crawler first: ./scripts/crawl.sh"
    read -p "Do you want to continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Run the workflow
echo "Running AI summarization workflow..."
uv run python src/agent/workflow.py

echo "✅ Summarization complete!"
