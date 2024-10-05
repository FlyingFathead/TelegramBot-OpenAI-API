#!/bin/bash

function hzline() {
printf '%*s\n' "${COLUMNS:-$(tput cols)}" '' | tr ' ' - ;
}

# Check if Docker is installed
if ! [ -x "$(command -v docker)" ]; then
  echo 'Error: Docker is not installed. Please install Docker first: https://www.docker.com/get-started/' >&2
  exit 1
fi

# Welcome Message
echo "" &&
hzline &&
echo "::: Welcome to the TelegramBot-OpenAI-API setup." &&
echo "::: Source code & repo: https://github.com/FlyingFathead/TelegramBot-OpenAI-API/" &&
hzline &&
echo

# Function to check for empty or invalid inputs for required keys
validate_input() {
  if [[ -z "$1" || ${#1} -lt 10 ]]; then
    echo "Error: Input cannot be blank or too short (must be at least 10 characters). Please try again."
    return 1
  fi
  return 0
}

# Prompt for required API keys (OpenAI and Telegram)
while true; do
  read -p "Please enter your OpenAI API key (required): " OPENAI_API_KEY
  validate_input "$OPENAI_API_KEY" && break
done

while true; do
  read -p "Please enter your Telegram Bot API key (required): " TELEGRAM_BOT_API_KEY
  validate_input "$TELEGRAM_BOT_API_KEY" && break
done

# Prompt for optional API keys (user can leave them blank)
hzline &&
echo "Below are optional keys for the bot's supported API functionalities that you can add in, or just press ENTER to leave them blank." &&
hzline &&
read -p "Please enter your Perplexity API key (optional): " PERPLEXITY_API_KEY
read -p "Please enter your OpenWeatherMap API key (optional): " OPENWEATHERMAP_API_KEY
read -p "Please enter your WeatherAPI key (optional): " WEATHERAPI_KEY
read -p "Please enter your MapTiler API key (optional): " MAPTILER_API_KEY
read -p "Please enter your Openrouteservice API key (optional): " OPENROUTESERVICE_API_KEY

# Create a .env file with the required and optional keys
hzline &&
echo "Generating .env file..."
cat <<EOL > .env
OPENAI_API_KEY=$OPENAI_API_KEY
TELEGRAM_BOT_API_KEY=$TELEGRAM_BOT_API_KEY
OPENWEATHERMAP_API_KEY=$OPENWEATHERMAP_API_KEY
WEATHERAPI_KEY=$WEATHERAPI_KEY
MAPTILER_API_KEY=$MAPTILER_API_KEY
OPENROUTESERVICE_API_KEY=$OPENROUTESERVICE_API_KEY
PERPLEXITY_API_KEY=$PERPLEXITY_API_KEY
# Additional variables can be added here
EOL

echo "Environment variables saved to .env." &&
hzline &&

# Instructions for the next steps
echo
echo "Next Steps:"
echo "1. Build the Docker image by running the following command:"
echo "   sudo docker build -t telegrambot-openai-api ."
echo
echo "2. After building the image, start the bot container using:"
echo "   sudo docker run --env-file .env -d telegrambot-openai-api"
echo
echo "3. Check the container status with:"
echo "   sudo docker ps"
echo
echo "4. Stop the container with:"
echo "   sudo docker stop <container_id>"
echo
echo "After that, you're all set! Enjoy, and don't forget to start the repository if you like it. :-)"
hzline &&
echo ""

# optional build & run function
function build_and_run() {
# Build Docker image
sudo docker build -t telegrambot-openai-api .
if [[ $? -ne 0 ]]; then
  echo "Error: Docker image build failed."
  exit 1
fi

# Run Docker container
sudo docker run --env-file .env -d telegrambot-openai-api
if [[ $? -ne 0 ]]; then
  echo "Error: Failed to run the Docker container."
  exit 1
fi
}

# build_and_run
