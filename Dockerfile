FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install build deps and install python deps
COPY iroko-flask/requirements.txt /app/requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && \
    pip install --no-cache-dir -r /app/requirements.txt && \
    apt-get remove -y gcc && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Copy app
COPY iroko-flask/ /app

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080

# Use gunicorn to serve the Flask app
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4"]
