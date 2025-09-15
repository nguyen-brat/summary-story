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

### Option 1: Docker (Recommended)

The easiest way to run AutoSummary is using Docker:

```bash
# Initial setup
chmod +x docker-run.sh
./docker-run.sh setup

# Run the application
./docker-run.sh start

# Access at http://localhost:8501
```

For detailed Docker instructions, see [DOCKER.md](DOCKER.md).

### Option 2: Local Development

### Quick Start with Scripts

For convenience, you can use the provided scripts:

```bash
# Run the web crawler
./scripts/crawl.sh

# Run the AI summarization
./scripts/summarize.sh
```

### Manual Execution

#### Streamlit Web Interface (Recommended)

Run the web interface for easy story crawling and summarization:

```bash
uv run streamlit run main.py
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