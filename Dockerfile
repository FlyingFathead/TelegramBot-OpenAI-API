FROM python:3.11-slim-bookworm

# Install dependencies & Rust
RUN apt-get update && apt-get install -y \
    ffmpeg \
    lynx \
    gcc \
    git \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Rust using rustup
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Add Rust to PATH
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Remove build dependencies to reduce image size
RUN apt-get update && apt-get remove -y curl gcc git && apt-get autoremove -y && \
    rm -rf /root/.cargo /root/.rustup /var/lib/apt/lists/*

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
