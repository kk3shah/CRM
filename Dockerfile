FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

# Install Python deps first (cache layer)
COPY crm/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Playwright browsers already bundled in base image, but ensure chromium is available
RUN playwright install chromium

# Copy project files
COPY . /app/

# Ensure persistent volume mount point exists
RUN mkdir -p /data

# Run from crm/ so all relative paths resolve correctly
WORKDIR /app/crm

CMD ["python", "scheduler.py"]
