FROM python:3.11.2-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gdb \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory in container
WORKDIR /app

COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

EXPOSE 8000

# Create a non-root user and switch to it
RUN useradd -m guest && chown -R guest:guest /app
USER guest

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "120", "app:create_app()"]
