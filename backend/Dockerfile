FROM python:3.11-slim

# Install system dependencies including liblouis for Braille formatting, and ffmpeg for audio
RUN apt-get update && apt-get install -y \
    liblouis-dev \
    liblouis-data \
    liblouis-bin \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml .

# Install python dependencies using uv
RUN uv sync --no-cache

# Copy application files
COPY . .

# Expose port
EXPOSE 8000

# Start server
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
