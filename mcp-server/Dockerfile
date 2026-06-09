FROM python:3.11-slim

# Metadata
LABEL maintainer="CyberSentinel AI"
LABEL description="CyberSentinel AI MCP HTTP Server"
LABEL version="1.0.0"

WORKDIR /app

# Install dependencies first (layer cache efficiency)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Create a non-root user for security
RUN addgroup --system mcpgroup && adduser --system --ingroup mcpgroup mcpuser
USER mcpuser

# Expose HTTP server port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" || exit 1

# Default: run the HTTP server
CMD ["uvicorn", "http_server:app", "--host", "0.0.0.0", "--port", "8001"]
