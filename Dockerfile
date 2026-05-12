FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    uvicorn fastapi python-multipart

# Copy project
COPY . .

# Create data directory for SQLite
RUN mkdir -p /app/data

# Make startup script executable
RUN chmod +x /app/start.sh

EXPOSE 8000

CMD ["/app/start.sh"]
