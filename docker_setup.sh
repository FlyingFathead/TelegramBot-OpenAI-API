#!/bin/bash

# Check if Docker is installed
if ! [ -x "$(command -v docker)" ]; then
  echo 'Error: Docker is not installed. Please install Docker first: https://www.docker.com/get-started/' >&2
  exit 1
fi

# Welcome Message
echo "Welcome to the TelegramBot-OpenAI-API setup."
echo "Source code: https://github.com/FlyingFathead/TelegramBot-OpenAI-API/"
echo

# Function to check for empty or invalid inputs
validate_input() {
  if [[ -z "$1" || ${#1} -lt 10 ]]; then
    echo "Error: Input cannot be blank or too short (must be at least 10 characters). Please try again."
    return 1
  fi
  return 0
}

# Prompt for OpenAI API Key with validation
while true; do
  read -p "Please enter your OpenAI API key: " OPENAI_API_KEY
  validate_input "$OPENAI_API_KEY" && break
done

# Prompt for Telegram Bot API Key with validation
while true; do
  read -p "Please enter your Telegram Bot API key: " TELEGRAM_BOT_API_KEY
  validate_input "$TELEGRAM_BOT_API_KEY" && break
done

# Create a .env file with the collected keys
echo "Generating .env file..."
cat <<EOL > .env
OPENAI_API_KEY=$OPENAI_API_KEY
TELEGRAM_BOT_API_KEY=$TELEGRAM_BOT_API_KEY
# Additional variables can be added here
EOL

# Optionally, check for Docker Compose if it's needed later
# if ! [ -x "$(command -v docker-compose)" ]; then
#   echo 'Warning: Docker Compose is not installed. Consider installing it if needed.' >&2
# fi


# Inform the user the setup is complete
echo "Environment variables saved to .env."

# Instructions for the next steps
echo
echo "Next Steps:"
echo "1. Build the Docker image by running the following command:"
echo "   sudo docker build -t telegrambot-openai-api ."
echo
echo "2. After building the image, start the bot container using:"
echo "   sudo docker run --env-file .env -d telegrambot-openai-api"
echo
echo "   This will start the bot in detached mode (-d) using the environment variables from the .env file."
echo
echo "3. Optionally, check if the container is running using:"
echo "   sudo docker ps"
echo
echo "4. To stop the container, you can run:"
echo "   sudo docker stop <container_id>"
echo
echo "You're all set! The bot should now be running and connected to Telegram and OpenAI."

