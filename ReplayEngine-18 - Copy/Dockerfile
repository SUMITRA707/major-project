# Base image: Lightweight Python
FROM python:3.12-slim

# Set working dir
WORKDIR /app

# Install dependencies (for log processing & HTML gen)
RUN pip install --no-cache-dir requests pandas jinja2 flask

# Copy code (we'll add scripts next)
COPY . .

# Expose port for report
EXPOSE 8080

# Run the replay engine
CMD ["python", "replay_engine.py"]