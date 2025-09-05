FROM python:3.11-slim

WORKDIR /app

# Cài đặt system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements và cài đặt Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy SSL generation script từ thư mục ssl
COPY ssl/generate_ssl_python.py ./ssl/

# Generate SSL certificates using Python
RUN python ssl/generate_ssl_python.py

# Copy source code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Make start.sh executable
RUN chmod +x /app/start.sh

# Expose both HTTP and HTTPS ports
EXPOSE 8000 8443

# Command to run the application
CMD ["/app/start.sh"]