# AutoSummary

An automated story summarization tool that crawls web novels and generates summaries using AI.

## Prerequisites

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/) package manager

## Setup

### 1. Install uv Package Manager

If you don't have `uv` installed, install it using one of these methods:

**On Linux/macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**On Windows:**
```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Using pip:**
```bash
pip install uv
```

### 2. Clone and Setup Project

```bash
git clone <your-repo-url>
cd AutoSummary
```

### 3. Sync Dependencies

Install all project dependencies using uv:

```bash
uv sync
```

This will create a virtual environment and install all packages listed in `pyproject.toml`.

### 4. Environment Configuration

#### Quick Setup (Recommended)

Run the setup script to configure everything automatically:

```bash
uv run python setup.py
```

This script will:
- Check if uv is properly installed
- Sync dependencies if needed
- Help you create the `.env` file with your API key

#### Manual Setup

Alternatively, create a `.env` file manually:

```bash
# Create .env file
touch .env
```

Add your Google API key to the `.env` file:

```bash
echo "GOOGLE_API_KEY=your_google_api_key_here" > .env
```

**Important:** Replace `your_google_api_key_here` with your actual Google Gemini API key. You can get one from [Google AI Studio](https://makersuite.google.com/app/apikey).

## How to Run

### Option 1: Docker

Run AutoSummary using Docker:

#### Quick Start with Docker Script

```bash
# Make the script executable
chmod +x docker-run.sh

# Build and start the application
./docker-run.sh build
./docker-run.sh start

# Access at http://localhost:8501
```

#### Manual Docker Commands

```bash
# Build the Docker image
docker build -t autosummary .

# Run the container
docker run -d --name autosummary-app -p 8501:8501 autosummary

# Access at http://localhost:8501
```

Note: You'll need to configure your API key and credentials through the web interface.

### Option 2: Local Development

### Quick Start with Scripts

The easiest way to run AutoSummary locally is using the run script:

```bash
# Make the script executable (first time only)
chmod +x run.sh

# Run the application
./run.sh
```

Or manually:

```bash
uv run streamlit run app.py
```

This will start a web interface at http://localhost:8501 with:
- **Single Column Layout**: New Story form above Continue Story form
- **Real-time Chapter Summaries**: See chapter summaries as they're generated
- **Streaming Updates**: Activity log updates immediately without waiting
- **Story Management**: Easy access to story history and continuation

For convenience, you can also use the provided scripts:

```bash
# Run the web crawler
./scripts/crawl.sh

# Run the AI summarization
./scripts/summarize.sh
```

### Features

#### Web Interface Features
- **New Story Section**: Crawl and summarize new stories
- **Continue Summary Section**: Resume processing from where you left off
- **Real-time Streaming**: Chapter summaries appear immediately as processed
- **Story History**: Manage multiple stories with persistent history
- **Activity Log**: Real-time updates without waiting for completion
- **API Management**: Easy API key configuration in the sidebar

### Manual Execution

#### Streamlit Web Interface (Recommended)

Run the web interface for easy story crawling and summarization:

```bash
uv run streamlit run app.py
```

This will start a web interface at http://localhost:8501 where you can:
- Crawl stories from websites with a user-friendly interface
- Generate AI summaries interactively
- Manage multiple stories and continue summaries
- View crawling and summarization history

#### Command Line Usage

### 1. Web Crawling

To crawl stories from websites:

```bash
uv run python src/crawl/crawling.py
```

This will:
- Launch a headless Chrome browser
- Navigate to the specified story URL
- Extract all chapters
- Save them as text files in the `story/` directory

### 2. Story Summarization

To generate summaries from crawled stories:

```bash
uv run python src/agent/workflow.py
```

This will:
- Process chapters sequentially
- Extract character information
- Generate chapter summaries
- Create periodic long summaries
- Output the final story summary

## Project Structure

```
AutoSummary/
├── src/
│   ├── agent/
│   │   └── workflow.py      # AI summarization workflow
│   └── crawl/
│       └── crawling.py      # Web scraping functionality
├── scripts/
│   ├── crawl.sh            # Convenience script for crawling
│   └── summarize.sh        # Convenience script for summarization
├── story/                  # Directory for crawled stories
├── app.py                  # Main Streamlit application
├── setup.py               # Setup script for environment configuration
├── pyproject.toml         # Project dependencies
├── uv.lock                # Dependency lock file
├── .env                   # Environment variables (create this)
└── README.md
```

## Configuration

### Crawler Settings

You can modify the crawler settings in `src/crawl/crawling.py`:
- `headless`: Run browser in headless mode (default: True)
- `wait_s`: Wait time for page loads (default: 12 seconds)

### Summarization Settings

You can modify the workflow settings in `src/agent/workflow.py`:
- `max_chapters`: Maximum chapters to process
- `big_summary_interval`: Interval for generating long summaries
- Model selection and prompts

## Troubleshooting

### Common Issues

1. **Chrome Driver Issues**: The crawler automatically downloads ChromeDriver, but ensure Chrome/Chromium is installed
2. **API Key Errors**: Make sure your Google API key is valid and has Gemini API access enabled
   - Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Ensure the Gemini API is enabled in your Google Cloud Console
3. **Memory Issues**: For large stories, consider adjusting the `big_summary_interval` to process in smaller chunks
4. **Permission Issues**: On Linux/macOS, you might need to make scripts executable: `chmod +x scripts/*.sh`

### Dependencies

If you encounter dependency issues, try:

```bash
# Update uv
uv self update

# Clean and reinstall dependencies
rm uv.lock
uv sync
```

## License