# DrawingScan: Production Dockerfile
FROM python:3.11-slim

# Install system dependencies for OpenCV and fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    fonts-noto-cjk \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency specifications
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and data
COPY . .

# Expose FastAPI (8000) and Streamlit (8501)
EXPOSE 8000 8501

# Default command: launch both FastAPI service and Streamlit UI
CMD ["sh", "-c", "uvicorn api.server:app --host 0.0.0.0 --port 8000 & streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0"]

