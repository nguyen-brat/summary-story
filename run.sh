#!/bin/bash
# Run the Streamlit app using uv

echo "🚀 Starting Story Summary AI with UV..."
echo "📍 Make sure you have set your environment variables in .env file"
echo "🔧 Using UV to run: streamlit run main.py"
echo ""

# Run the streamlit app with uv
uv run streamlit run main.py

echo ""
echo "👋 Story Summary AI has stopped."
