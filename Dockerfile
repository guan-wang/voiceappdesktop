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

EXPOSE 8080

ENV PYTHONUNBUFFERED=1

CMD ["python", "backend/server.py"]