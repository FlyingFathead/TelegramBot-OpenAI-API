#!/bin/bash

# horizontal line
function hzline() { printf '%*s\n' "${COLUMNS:-$(tput cols)}" '' | tr ' ' - ; }

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

# Check if .env file already exists and prompt the user
if [ -f .env ]; then
  echo "Warning: A .env file already exists in this directory."
  while true; do
    read -p "Do you want to overwrite the existing .env file? (y/n): " yn
    case $yn in
      [Yy]* ) break;;
      [Nn]* ) echo "Exiting setup without overwriting .env file."; exit 0;;
      * ) echo "Please answer yes or no.";;
    esac
  done
fi

# Function to check for empty or invalid inputs for required keys
validate_input() {
  if [[ -z "$1" || ${#1} -lt 10 ]]; then
    echo "Error: Input cannot be blank or too short (must be at least 10 characters). Please try again."
    return 1
  fi
  return 0
}

validate_openai_key() {
  validate_input "$1" || return 1
  if [[ "$1" =~ [[:space:]] ]]; then
    echo "Error: The OpenAI key must be one uninterrupted line without whitespace."
    return 1
  fi
  if [[ "$1" != sk-* ]]; then
    echo "Warning: OpenAI secret keys currently normally use an sk- prefix."
  fi
  return 0
}

# Prompt for required API keys (OpenAI and Telegram)
while true; do
  read -r -s -p "Please enter your NEW OpenAI project API key (required): " OPENAI_API_KEY
  echo
  validate_openai_key "$OPENAI_API_KEY" && break
done

echo "Confirm in the OpenAI platform that this key belongs to the intended project."

while true; do
  read -r -p "Please enter your Telegram Bot API Token (required): " TELEGRAM_BOT_TOKEN
  validate_input "$TELEGRAM_BOT_TOKEN" && break
done

# Prompt for optional API keys (user can leave them blank)
hzline &&
echo "::: Below are optional keys for the bot's supported API functions." &&
echo "::: They're not required for basic functionality, but are a great enhancement." &&
echo "::: If you don't have an API key right now, just press ENTER to leave them blank." &&
hzline &&
read -r -p "Please enter your Perplexity API key (optional): " PERPLEXITY_API_KEY
read -r -p "Please enter your OpenWeatherMap API key (optional): " OPENWEATHERMAP_API_KEY
read -r -p "Please enter your WeatherAPI key (optional): " WEATHERAPI_KEY
read -r -p "Please enter your MapTiler API key (optional): " MAPTILER_API_KEY
read -r -p "Please enter your Openrouteservice API key (optional): " OPENROUTESERVICE_API_KEY

# Create a .env file with the required and optional keys
hzline &&
echo "Generating .env file..."
umask 077
{
  printf 'OPENAI_API_KEY=%s\n' "$OPENAI_API_KEY"
  printf 'TELEGRAM_BOT_TOKEN=%s\n' "$TELEGRAM_BOT_TOKEN"
  printf 'OPENWEATHERMAP_API_KEY=%s\n' "$OPENWEATHERMAP_API_KEY"
  printf 'WEATHERAPI_KEY=%s\n' "$WEATHERAPI_KEY"
  printf 'MAPTILER_API_KEY=%s\n' "$MAPTILER_API_KEY"
  printf 'OPENROUTESERVICE_API_KEY=%s\n' "$OPENROUTESERVICE_API_KEY"
  printf 'PERPLEXITY_API_KEY=%s\n' "$PERPLEXITY_API_KEY"
} > .env
chmod 600 .env

echo "Environment variables saved to .env with mode 0600." &&
hzline &&

# Instructions for the next steps
echo
echo "Next Steps:"
echo "1. Build the Docker image by running the following command:"
echo "   sudo docker build -t telegrambot-openai-api ."
echo
echo "2. After building the image, start the bot container using:"
echo "   sudo docker run --env-file .env --name telegrambot-openai-api -d telegrambot-openai-api"
echo
echo "3. Check the container status with:"
echo "   sudo docker ps"
echo
echo "4. Check the logs with:"
echo "  sudo docker logs telegrambot-openai-api"
echo 
echo "5. Verify the new OpenAI key before revoking the old one:"
echo "   python3 scripts/verify_openai_key.py --live-request"
echo
echo "6. Stop the container with:"
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
