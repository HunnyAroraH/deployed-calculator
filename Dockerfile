# Use a lightweight official Python image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Install Chrome dependencies
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg \
    apt-transport-https \
    ca-certificates \
    libnss3 \
    libxss1 \
    libappindicator1 \
    fonts-liberation \
    libasound2 \
    xdg-utils \
    libgbm-dev

# Download and install the specific Chrome version you provided
RUN wget https://storage.googleapis.com/chrome-for-testing-public/128.0.6613.119/linux64/chrome-linux64.zip -O /tmp/chrome-linux64.zip \
    && unzip /tmp/chrome-linux64.zip -d /tmp/ \
    && mv /tmp/chrome-linux64/chrome /usr/local/bin/chrome \
    && chmod +x /usr/local/bin/chrome

# Ensure ChromeDriver is executable (if you're including it in the project)
COPY chromedriver /usr/local/bin/chromedriver
RUN chmod +x /usr/local/bin/chromedriver

# Log all files and folders in /usr/local/bin
RUN echo "Listing files in /usr/local/bin:" && ls -la /usr/local/bin

# Log all files and folders in /tmp to check Chrome installation
RUN echo "Listing files in /tmp:" && ls -la /tmp

# Copy requirements and install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 8000 to the outside world
EXPOSE 8000

# Start the Flask application with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]
