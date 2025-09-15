# Docker Setup for AutoSummary

This guide explains how to run the AutoSummary application using Docker, making it easy to deploy and run consistently across different environments.

## Prerequisites

- **Docker**: [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose**: Usually included with Docker Desktop
- **Google Gemini API Key**: Get one from [Google AI Studio](https://makersuite.google.com/app/apikey)

## Quick Start

### 1. Initial Setup

```bash
# Make the run script executable (Linux/macOS)
chmod +x docker-run.sh

# Run initial setup - creates .env file and directories
./docker-run.sh setup
```

This will prompt you to enter your Google Gemini API key and create the necessary configuration files.

### 2. Run the Application

**Development Mode (with logs):**
```bash
./docker-run.sh run
```

**Detached Mode (background):**
```bash
./docker-run.sh start
```

**Production Mode (with Nginx reverse proxy):**
```bash
./docker-run.sh prod
```

### 3. Access the Application

- **Development/Standard**: http://localhost:8501
- **Production Mode**: http://localhost (with Nginx proxy)

## Available Commands

| Command | Description |
|---------|-------------|
| `./docker-run.sh setup` | Initial setup (create .env, directories) |
| `./docker-run.sh build` | Build the Docker image |
| `./docker-run.sh run` | Run in development mode (with logs) |
| `./docker-run.sh start` | Start in detached mode (background) |
| `./docker-run.sh stop` | Stop the application |
| `./docker-run.sh restart` | Restart the application |
| `./docker-run.sh logs` | View application logs |
| `./docker-run.sh shell` | Open shell in container |
| `./docker-run.sh clean` | Clean up containers and images |
| `./docker-run.sh prod` | Run in production mode with Nginx |

## Manual Docker Commands

If you prefer using Docker commands directly:

### Build and Run
```bash
# Build the image
docker build -t autosummary:latest .

# Run with docker-compose
docker-compose up -d

# Access logs
docker-compose logs -f autosummary

# Stop
docker-compose down
```

### Single Container Run
```bash
docker run -d \
  --name autosummary-app \
  -p 8501:8501 \
  -e GOOGLE_API_KEY="your_api_key_here" \
  -v $(pwd)/story:/app/story \
  -v $(pwd)/summary:/app/summary \
  -v $(pwd)/crawl_history.json:/app/crawl_history.json \
  --shm-size=2g \
  autosummary:latest
```

## Environment Variables

Set these in your `.env` file or pass directly to Docker:

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Your Google Gemini API key | **Required** |
| `CHROME_OPTIONS` | Chrome browser options for container | `--headless --no-sandbox --disable-dev-shm-usage --disable-gpu` |
| `STREAMLIT_SERVER_HEADLESS` | Run Streamlit in headless mode | `true` |
| `STREAMLIT_SERVER_PORT` | Streamlit server port | `8501` |

## Volume Mounts

The Docker setup automatically mounts these directories to persist data:

- `./story` → `/app/story` - Crawled story files
- `./summary` → `/app/summary` - Generated summaries
- `./crawl_history.json` → `/app/crawl_history.json` - Application history

## Architecture

### Development Mode
```
[Browser] → [Streamlit:8501] → [Chrome + Selenium] → [AI Summarization]
```

### Production Mode
```
[Browser] → [Nginx:80] → [Streamlit:8501] → [Chrome + Selenium] → [AI Summarization]
```

## Troubleshooting

### Common Issues

1. **Chrome/Selenium Issues in Container**
   - The Docker image includes Chrome and proper configurations
   - Uses `--no-sandbox` and `--disable-dev-shm-usage` for container compatibility
   - Allocates 2GB shared memory (`shm-size=2g`)

2. **API Key Issues**
   ```bash
   # Check if .env file exists and contains your key
   cat .env
   
   # Recreate .env file
   ./docker-run.sh setup
   ```

3. **Port Already in Use**
   ```bash
   # Check what's using port 8501
   lsof -i :8501
   
   # Stop the application
   ./docker-run.sh stop
   ```

4. **Permission Issues (Linux)**
   ```bash
   # Make sure the script is executable
   chmod +x docker-run.sh
   
   # Fix directory permissions
   sudo chown -R $USER:$USER story summary
   ```

5. **Memory Issues**
   - The container uses 2GB shared memory for Chrome
   - Adjust `shm_size` in `docker-compose.yml` if needed
   - Monitor with: `docker stats autosummary-app`

### Logs and Debugging

```bash
# View application logs
./docker-run.sh logs

# Check container status
docker-compose ps

# Enter container for debugging
./docker-run.sh shell

# Check Chrome process in container
./docker-run.sh shell
ps aux | grep chrome
```

### Performance Optimization

1. **Chrome Optimization**
   - Images are disabled by default (`--disable-images`)
   - Extensions and plugins are disabled
   - Headless mode reduces resource usage

2. **Container Resources**
   ```bash
   # Monitor resource usage
   docker stats autosummary-app
   
   # Adjust memory limits in docker-compose.yml if needed
   ```

## Security Considerations

1. **API Key Security**
   - Store API keys in `.env` file (not committed to git)
   - Use Docker secrets for production deployments
   - Never hardcode API keys in Dockerfile

2. **Container Security**
   - Runs as non-root user (`appuser`)
   - Uses specific security options for Chrome
   - Network isolation with custom network

3. **Production Security**
   - Enable HTTPS with SSL certificates in Nginx
   - Use environment variable injection instead of `.env` files
   - Implement proper logging and monitoring

## Custom Configuration

### Modify Chrome Options
Edit the `CHROME_OPTIONS` in your `.env` file:
```bash
CHROME_OPTIONS=--headless --no-sandbox --disable-dev-shm-usage --disable-gpu --window-size=1920,1080
```

### Adjust Streamlit Settings
Add to `.env` file:
```bash
STREAMLIT_SERVER_PORT=8502
STREAMLIT_SERVER_HEADLESS=false
STREAMLIT_SERVER_ENABLE_CORS=true
```

### Production Nginx Configuration
Edit `nginx.conf` to customize reverse proxy settings, SSL, caching, etc.

## Support

For issues related to:
- **Docker setup**: Check this documentation and Docker logs
- **Application functionality**: See main README.md
- **Selenium/Chrome**: Ensure proper container configuration and shared memory allocation
