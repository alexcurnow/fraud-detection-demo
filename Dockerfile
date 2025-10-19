# Backend Dockerfile - builds the Python FastAPI application
FROM python:3.12-slim

# Set working directory inside container
WORKDIR /app

# Copy requirements first (Docker caching optimization)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY run_api.py .
COPY train_model.py .

# Create directory for data persistence
RUN mkdir -p /app/data /app/models

# Expose port 8000 for FastAPI
EXPOSE 8000

# Run the FastAPI server
CMD ["python", "run_api.py"]
