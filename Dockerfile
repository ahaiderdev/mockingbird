FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY configs/ ./configs/

# Expose ports
# 8000: Prometheus /metrics endpoint
# 8081: Control API
EXPOSE 8000 8081

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8081/healthz')" || exit 1

# Run the application
CMD ["python", "-m", "src.main", "--config", "configs/baseline.yaml"]

