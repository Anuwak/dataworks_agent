FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install Prettier for Markdown formatting
RUN npm install -g prettier@3.4.2

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Start server
CMD ["python", "main.py"]
