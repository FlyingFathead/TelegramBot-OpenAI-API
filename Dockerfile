FROM python:slim-bookworm

# Install dependencies & clean up to reduce Docker image size
RUN apt-get update && apt-get install -y \
    ffmpeg \
    lynx \
    gcc \
    git \
    rustc \
    cargo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
    
WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

# Set environment variables for Docker runtime
ENV PYTHONUNBUFFERED=1
ENV RUNNING_IN_DOCKER=true

# Optional: Debugging tools (disable in production)
# RUN ls -lsa
# RUN pwd

# Default command to run the application
CMD ["python3", "src/main.py"]
