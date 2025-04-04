# api_get_stock_prices_alphavantage.py
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
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Utility function to get API key
def get_api_key():
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    if not api_key:
        logging.error("Alpha Vantage API key not set. You need to set the 'ALPHA_VANTAGE_API_KEY' environment variable to use Alpha Vantage API functionalities!")
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
            logging.debug(f"Symbol search response data: {data}")
            if 'Information' in data and 'rate limit' in data['Information'].lower():
                return "API rate limit exceeded. Please try again later or upgrade to a premium plan."

            best_match = data.get('bestMatches', [])
            if best_match:
                # Prioritize correct symbol
                for match in best_match:
                    if match['1. symbol'].upper() == keyword.upper():
                        logging.debug(f"Exact match found: {match}")
                        return match
                logging.debug(f"Best match found: {best_match[0]}")
                return best_match[0]  # Return the first match if no exact match found
            else:
                logging.info("No matches found.")
                return "No matches found."
        else:
            logging.error(f"Failed to search for symbol: {response.text}")
            return "Failed to search for symbol. Please try again later."

# Get stock price data with fallback to search
async def get_stock_price(symbol, original_symbol=None):
    if original_symbol is None:
        original_symbol = symbol

    if symbol != original_symbol and symbol == original_symbol:
        logging.error(f"Symbol search loop detected for {symbol}. Terminating.")
        return "Symbol search loop detected. Please check the stock symbol and try again."

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
        logging.debug(f"Stock data response content: {response.text}")

        if response.status_code == 200:
            data = response.json()
            logging.debug(f"Stock data response JSON: {data}")
            if 'Information' in data and 'rate limit' in data['Information'].lower():
                return "API rate limit exceeded. Please try again later or upgrade to a premium plan."
            try:
                last_refreshed = data['Meta Data']['3. Last Refreshed']
                last_price = data['Time Series (1min)'][last_refreshed]['1. open']
                now_utc = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                return f"{symbol} last price: {last_price} USD. Data fetched at: {now_utc} UTC via Alpha Vantage."
            except KeyError:
                logging.info(f"Symbol {symbol} not found, attempting to search for symbol.")
                # Fallback to search if direct symbol fetch fails
                symbol_info = await search_stock_symbol(symbol)
                logging.debug(f"Search result for symbol {symbol}: {symbol_info}")
                if isinstance(symbol_info, dict) and '1. symbol' in symbol_info:
                    new_symbol = symbol_info['1. symbol']
                    logging.info(f"Found new symbol: {new_symbol}")
                    if new_symbol == symbol:
                        logging.error(f"Symbol search loop detected for {symbol}. Terminating.")
                        return "Symbol search loop detected. Please check the stock symbol and try again."
                    return f"Symbol {symbol} wasn't found, searched instead. " + await get_stock_price(new_symbol, original_symbol)
                else:
                    logging.error(f"Search for symbol failed or returned no matches: {symbol_info}")
                    return "Error fetching data. Please check the stock symbol and try again."
        else:
            logging.error(f"Failed to fetch stock data: {response.text}")
            return "Failed to fetch stock data. Tell the user to please try again later or try with Perplexity API as a fallback."

# Main function to handle command-line arguments
async def main():
    if len(sys.argv) < 2:
        print("Usage: python api_get_stock_prices.py <symbol or keyword>")
        return

    query = sys.argv[1]
    stock_data = await get_stock_price(query)
    print(stock_data)

if __name__ == "__main__":
    asyncio.run(main())
