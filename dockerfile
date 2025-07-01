# syntax=docker/dockerfile:1.4
FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
RUN pip install --upgrade pip && pip install uv

# Set workdir
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN uv sync --system --no-cache

# Default entrypoint (can be overridden)
ENTRYPOINT ["uv", "run"]
CMD ["python", "-m", "fantasy_football_2025.main"]
