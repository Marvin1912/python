# YouTube Summarizer

A Flask application that summarizes YouTube videos using AI-powered transcript analysis.

## Prerequisites

- Docker and Docker CLI installed on your system

## Quick Start with Docker

### Building the Docker Image

Build the Docker image from the Dockerfile:

```bash
docker build -t youtube-summarizer .
```

This will:
- Use Python 3.12-slim as the base image
- Install all dependencies from `requirements.txt`
- Copy the application files into the container
- Expose port 5000

### Running the Container

Start the container with:

```bash
docker run -p 5000:5000 youtube-summarizer
```

This command:
- Maps port 5000 on your host machine to port 5000 in the container
- Runs the Flask application via Gunicorn with 2 workers
- The app will be accessible at `http://localhost:5000`

### Running with Environment Variables

If your application requires API keys or other configuration (e.g., for Anthropic, Google APIs):

```bash
docker run -p 5000:5000 \
  -e ANTHROPIC_API_KEY=your_key_here \
  -e GOOGLE_API_KEY=your_key_here \
  youtube-summarizer
```

Alternatively, create a `.env` file in your project root (see `.env.example`) and use:

```bash
docker run -p 5000:5000 \
  --env-file .env \
  youtube-summarizer
```

### Running in Background

To run the container in detached mode:

```bash
docker run -d -p 5000:5000 \
  --env-file .env \
  --name youtube-summarizer-app \
  youtube-summarizer
```

Then view logs with:

```bash
docker logs youtube-summarizer-app
```

And stop the container with:

```bash
docker stop youtube-summarizer-app
```

## Accessing the Application

Once the container is running, open your browser and navigate to:

```
http://localhost:5000
```

## Development Notes

- The container runs Gunicorn with 2 workers, optimized for production
- The Flask debug mode is disabled in the container (only enabled when running `python run.py` locally)
- All Python environment variables are set to prevent caching and ensure unbuffered output
