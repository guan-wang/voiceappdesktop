FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY web/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY core/ ./core/
COPY web/backend/ ./backend/
COPY web/frontend/ ./frontend/

# Create reports directory
RUN mkdir -p backend/reports

# Add /app to Python path so 'core' can be imported
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

# Run from /app directory with proper module path
CMD ["python", "-m", "backend.server"]