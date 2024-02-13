# api_perplexity_search.py

import openai
import httpx
import logging
import os

# Assuming you've set PERPLEXITY_API_KEY in your environment variables
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

# can be adjusted to any model
async def fact_check_with_perplexity(question: str):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    data = {
        "model": "pplx-7b-online",  # Specifying the pplx-70b-online model
        "stream": False,
        "max_tokens": 1024,
        "temperature": 0.0,  # Adjust based on how deterministic you want the responses to be
        "messages": [
            {
                "role": "system",
                "content": "Be precise and concise in your responses."
            },
            {
                "role": "user",
                "content": question
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Perplexity API Error: {response.text}")
        return None

# perplexity 70b query
async def query_pplx_70b_online(prompt):
    PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")  # Ensure this is securely set
    url = "https://api.perplexity.ai/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    data = {
        "model": "pplx-70b-online",  # Specifying the pplx-70b-online model
        "messages": [
            {"role": "system", "content": "You are a Discord helper bot. Answer accordingly."},
            {"role": "user", "content": prompt},
        ],
        # Include other parameters as necessary
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.text}")
        return None

# queries perplexity
async def query_perplexity(question: str):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    data = {
        "model": "pplx-7b-online",
        "stream": False,
        "max_tokens": 1024,
        "temperature": 0.0,  # Adjust as needed
        "messages": [
            {"role": "system", "content": "Be precise in your responses."},
            {"role": "user", "content": question}
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        logging.info(f"Response type: {type(response.json())}, Content: {response.text}")

        if response.status_code == 200:
            response_data = response.json()  # Ensure we're parsing the JSON response

            # Properly extract the message content using .get()
            if 'choices' in response_data and len(response_data['choices']) > 0:
                bot_reply_content = response_data['choices'][0].get('message', {}).get('content', "")
                return bot_reply_content.strip() if bot_reply_content else "Sorry, I couldn't fetch an answer for that. Please try again later."
            else:
                logging.error("Perplexity API returned an unexpected structure.")
                return "Unexpected response structure from Perplexity API."
        else:
            logging.error(f"Perplexity API Error: {response.text}")
            return None

# translate perplexity replies
async def translate_response(bot, user_request, perplexity_response):
    # Log the Perplexity API response before translation
    logging.info(f"Perplexity API Response to be translated: {perplexity_response}")

    # System message to guide the model for translating
    system_message = {
        "role": "system",
        "content": "Translate the following response to whatever query language the original user question was. Example: if user asked their question in Finnish, translate the provided reply text to Finnish)."
    }

    # Prepare the chat history with only the Perplexity's response as the assistant's message to be translated
    chat_history = [
        system_message,
        {"role": "user", "content": user_request},
        {"role": "assistant", "content": perplexity_response}
    ]

    # Prepare the payload for the OpenAI API
    payload = {
        "model": bot.model,  # Specify the OpenAI model you're using for translating
        "messages": chat_history,
        "temperature": 0.5  # Adjust based on your preference for randomness in translation
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bot.openai_api_key}"  # Use the correct API key variable
    }

    # Make the API request to OpenAI
    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.openai.com/v1/chat/completions",
                                     json=payload,
                                     headers=headers)

    # Process the response
    if response.status_code == 200:
        try:
            response_json = response.json()
            translated_reply = response_json['choices'][0]['message']['content'].strip()
            logging.info(f"Translated response: {translated_reply}")
            return translated_reply
        except Exception as e:
            logging.error(f"Error processing translation response: {e}")
            return f"Translation failed due to an error: {e}"  
    else:
        logging.error(f"Error in translating response: {response.text}")
        return f"Failed to translate, API returned status code {response.status_code}: {response.text}"