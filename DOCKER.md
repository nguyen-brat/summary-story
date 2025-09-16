# Docker Setup for AutoSummary

This guide explains how to run the AutoSummary application using Docker. The application is fully self-contained - **no .env file or environment setup required!** All credentials are entered directly through the web interface.

## Prerequisites

- **Docker**: [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose**: Usually included with Docker Desktop
- **Google Gemini API Key**: Get one from [Google AI Studio](https://makersuite.google.com/app/apikey)

## Quick Start

### 1. Build and Run

**Option A: Using the convenient script**
```bash
# Make script executable (Linux/macOS)
chmod +x docker-run.sh

# Build and run in one command
./docker-run.sh run
```

**Option B: Using simple build script**
```bash
# Build the image
./docker-build.sh

# Run the container
docker run -p 8501:8501 autosummary:latest
```

**Option C: Manual Docker commands**
```bash
# Build
docker build -t autosummary:latest .

# Run
docker run -p 8501:8501 autosummary:latest
```

### 2. Access the Application

Open your browser and go to: **http://localhost:8501**

### 3. Enter Credentials in UI

1. Open the app in your browser
2. In the sidebar, expand "🔑 API Configuration" and enter your Google Gemini API key
3. Expand "🌐 Website Credentials" and enter your website login credentials
4. Start crawling and summarizing stories!

**That's it! No configuration files needed.**

## Available Commands

| Command | Description |
|---------|-------------|
| `./docker-build.sh` | Simple build and instructions |
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
  -v $(pwd)/story:/app/story \
  -v $(pwd)/summary:/app/summary \
  -v $(pwd)/crawl_history.json:/app/crawl_history.json \
  --shm-size=2g \
  autosummary:latest
```

## Configuration

### No Environment Variables Required! 🎉

The application is designed to be completely self-contained. All configuration is done through the web interface:

- **Google Gemini API Key**: Enter in the sidebar under "🔑 API Configuration"  
- **Website Credentials**: Enter in the sidebar under "🌐 Website Credentials"
- **Crawl Settings**: Configure in the main form when starting a new crawl

### Optional Environment Variables (Advanced)

For advanced Docker deployments, these environment variables are available:

| Variable | Description | Default |
|----------|-------------|---------|
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

2. **No .env File Needed**
   - All credentials are entered through the web UI
   - No configuration files to manage
   - Just build and run!

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
   - Enter API keys directly in the secure web interface
   - Keys are stored only in browser session (not persisted to disk)
   - Use Docker secrets for production deployments if needed

2. **Container Security**
   - Runs as non-root user (`appuser`)
   - Uses specific security options for Chrome
   - Network isolation with custom network

3. **Production Security**
   - Enable HTTPS with SSL certificates in Nginx
   - Consider using environment variable injection for production
   - Implement proper logging and monitoring

## Custom Configuration

### Modify Chrome Options (Advanced)
If running with custom environment variables:
```bash
docker run -p 8501:8501 -e CHROME_OPTIONS="--headless --no-sandbox --disable-dev-shm-usage --disable-gpu --window-size=1920,1080" autosummary:latest
```

### Adjust Streamlit Settings (Advanced)
```bash
docker run -p 8502:8502 -e STREAMLIT_SERVER_PORT=8502 autosummary:latest
```

### Production Nginx Configuration
Edit `nginx.conf` to customize reverse proxy settings, SSL, caching, etc.

## Support

For issues related to:
- **Docker setup**: Check this documentation and Docker logs
- **Application functionality**: See main README.md
- **Selenium/Chrome**: Ensure proper container configuration and shared memory allocation
