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

# Add Google Chrome's official GPG key and stable repo
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# Install stable version of Google Chrome
RUN apt-get update && apt-get install -y google-chrome-stable

# Log Chrome version and installation paths
RUN echo "Logging Chrome version and paths" \
    && google-chrome --version \
    && which google-chrome \
    && find / -name chrome 2>/dev/null

# Ensure ChromeDriver is executable (if you're including it in the project)
COPY chromedriver /usr/local/bin/chromedriver
RUN chmod +x /usr/local/bin/chromedriver

# Copy requirements and install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 8000 to the outside world
EXPOSE 8000

# Start the Flask application with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:8000", "--timeout", "120", "app:app"]
