#!/usr/bin/env python3
"""
Setup script for AutoSummary project.
This script helps users configure their environment.
"""

import os
import sys
from pathlib import Path

def create_env_file():
    """Create a .env file with necessary environment variables."""
    env_path = Path(".env")
    
    if env_path.exists():
        print("✓ .env file already exists")
        with open(env_path, 'r') as f:
            content = f.read()
            if 'GOOGLE_API_KEY' in content:
                print("✓ GOOGLE_API_KEY found in .env file")
                return
    
    print("Creating .env file...")
    
    # Get API key from user
    api_key = input("\nPlease enter your Google Gemini API key: ").strip()
    
    if not api_key:
        print("❌ No API key provided. Please run this script again with a valid API key.")
        sys.exit(1)
    
    # Create .env file
    env_content = f"""# AutoSummary Environment Variables
GOOGLE_API_KEY={api_key}

# Optional: Add other configuration here
# HEADLESS_MODE=true
# WAIT_TIME=12
"""
    
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print(f"✓ Created .env file at {env_path.absolute()}")
    print("\n📝 Note: Keep your .env file secure and don't commit it to version control!")

def check_dependencies():
    """Check if uv is installed and dependencies are synced."""
    
    # Check if uv is available
    if os.system("uv --version > /dev/null 2>&1") != 0:
        print("❌ uv is not installed or not in PATH")
        print("Please install uv using:")
        print("  curl -LsSf https://astral.sh/uv/install.sh | sh")
        return False
    
    print("✓ uv is installed")
    
    # Check if dependencies are synced
    if not Path(".venv").exists() or not Path("uv.lock").exists():
        print("⚠️  Dependencies not synced. Running 'uv sync'...")
        if os.system("uv sync") != 0:
            print("❌ Failed to sync dependencies")
            return False
        print("✓ Dependencies synced")
    else:
        print("✓ Dependencies appear to be synced")
    
    return True

def main():
    print("🚀 AutoSummary Setup Script")
    print("=" * 40)
    
    # Check current directory
    if not Path("pyproject.toml").exists():
        print("❌ Please run this script from the AutoSummary project root directory")
        sys.exit(1)
    
    print("✓ Running from correct directory")
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Create .env file
    create_env_file()
    
    print("\n🎉 Setup complete!")
    print("\nNext steps:")
    print("1. To crawl stories: uv run python src/crawl/crawling.py")
    print("2. To generate summaries: uv run python src/agent/workflow.py")
    print("\nFor more information, see README.md")

if __name__ == "__main__":
    main()
