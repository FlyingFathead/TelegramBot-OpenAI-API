# api_get_stock_prices.py
#
# Stock price API fetching via Alpha Vantage
# (You need to register at https://www.alphavantage.co for your own API key)
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import httpx
import os
import logging
import sys
import asyncio
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Utility function to get API key
def get_api_key():
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    if not api_key:
        logging.error("[WARNING] Alpha Vantage API key not set. You need to set the 'ALPHA_VANTAGE_API_KEY' environment variable to use Alpha Vantage API functionalities!")
        return None
    return api_key

# Search for stock symbol
async def search_stock_symbol(keyword):
    api_key = get_api_key()
    if not api_key:
        return "Alpha Vantage API key not set."

    logging.info(f"Searching stock symbol for keyword: {keyword}")

    base_url = 'https://www.alphavantage.co/query'
    params = {
        'function': 'SYMBOL_SEARCH',
        'keywords': keyword,
        'apikey': api_key
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(base_url, params=params)
        logging.info(f"Symbol search response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            best_match = data.get('bestMatches', [])
            if best_match:
                return best_match[0]  # Return the first match
            else:
                return "No matches found."
        else:
            logging.error(f"Failed to search for symbol: {response.text}")
            return "Failed to search for symbol. Please try again later."

# Get stock price data
async def get_stock_price(symbol):
    api_key = get_api_key()
    if not api_key:
        return "Alpha Vantage API key not set."

    logging.info(f"Fetching stock data for symbol: {symbol}")

    base_url = 'https://www.alphavantage.co/query'
    params = {
        'function': 'TIME_SERIES_INTRADAY',
        'symbol': symbol,
        'interval': '1min',
        'apikey': api_key
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(base_url, params=params)
        logging.info(f"Stock data response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            try:
                last_refreshed = data['Meta Data']['3. Last Refreshed']
                last_price = data['Time Series (1min)'][last_refreshed]['1. open']
                now_utc = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                return f"{symbol} last price: {last_price} USD (Fetched at: {now_utc} UTC)"
            except KeyError:
                return "Error fetching data. Please check the stock symbol and try again."
        else:
            logging.error(f"Failed to fetch stock data: {response.text}")
            return "Failed to fetch stock data. Please try again later."

# Main function to handle command-line arguments
async def main():
    if len(sys.argv) < 2:
        print("Usage: python api_get_stock_prices.py <symbol or keyword>")
        return

    query = sys.argv[1]
    if len(query) <= 5:  # Assuming the input is a stock symbol if it's 5 characters or less
        stock_data = await get_stock_price(query)
    else:  # Otherwise, search for the stock symbol
        symbol_info = await search_stock_symbol(query)
        if isinstance(symbol_info, dict) and '1. symbol' in symbol_info:
            symbol = symbol_info['1. symbol']
            stock_data = await get_stock_price(symbol)
        else:
            stock_data = "Could not find a matching stock symbol."

    print(stock_data)

if __name__ == "__main__":
    asyncio.run(main())
