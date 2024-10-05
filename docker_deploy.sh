#!/bin/bash

CONTAINER_NAME="telegrambot-openai-api"
IMAGE_NAME="telegrambot-openai-api"

# Function to stop and remove existing container
cleanup() {
    echo "Stopping container if it's running..."
    sudo docker stop ${CONTAINER_NAME} || true

    echo "Removing container if it exists..."
    sudo docker rm ${CONTAINER_NAME} || true
}

# Function to build and run the container
deploy() {
    echo "Building Docker image..."
    sudo docker build --no-cache -t ${IMAGE_NAME} .
    if [[ $? -ne 0 ]]; then
        echo "Error: Docker image build failed."
        exit 1
    fi

    echo "Running Docker container..."
    sudo docker run --env-file .env --name ${CONTAINER_NAME} -d ${IMAGE_NAME}
    if [[ $? -ne 0 ]]; then
        echo "Error: Failed to run the Docker container."
        exit 1
    fi

    echo "Deployment complete."
}

# Execute the functions
cleanup
deploy
