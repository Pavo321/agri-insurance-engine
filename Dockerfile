FROM python:3.11-slim

# Install GDAL and system dependencies
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

ENV GDAL_VERSION=3.6.0
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

# Non-root user for security
RUN useradd -m -u 1000 agriuser && chown -R agriuser:agriuser /app
USER agriuser

EXPOSE 8000 8501
