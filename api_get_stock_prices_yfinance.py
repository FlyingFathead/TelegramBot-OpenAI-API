# api_get_stock_prices_yfinance.py
#
# Stock price API fetching via Yahoo Finance (yfinance)
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import yfinance as yf
import logging
import sys
import asyncio
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Search for stock symbol (Using yfinance for direct data fetching)
async def search_stock_symbol(keyword):
    logging.info(f"Searching stock symbol for keyword: {keyword}")
    ticker = yf.Ticker(keyword)
    
    if not ticker.info:
        logging.info("No matches found.")
        return "No matches found."

    logging.debug(f"Ticker info: {ticker.info}")
    return ticker

# Get stock price data with fallback to search
async def get_stock_price(symbol, original_symbol=None):
    if original_symbol is None:
        original_symbol = symbol

    if symbol != original_symbol and symbol == original_symbol:
        logging.error(f"Symbol search loop detected for {symbol}. Terminating.")
        return "Symbol search loop detected. Please check the stock symbol and try again."

    logging.info(f"Fetching stock data for symbol: {symbol}")
    ticker = yf.Ticker(symbol)

    try:
        hist = ticker.history(period="1d", interval="1m")
        logging.debug(f"Stock data history: {hist}")

        if hist.empty:
            logging.info(f"Symbol {symbol} not found, attempting to search for symbol.")
            # Fallback to search if direct symbol fetch fails
            ticker_info = await search_stock_symbol(symbol)
            logging.debug(f"Search result for symbol {symbol}: {ticker_info}")
            if isinstance(ticker_info, yf.Ticker):
                new_symbol = ticker_info.info['symbol']
                logging.info(f"Found new symbol: {new_symbol}")
                if new_symbol == symbol:
                    logging.error(f"Symbol search loop detected for {symbol}. Terminating.")
                    return "Symbol search loop detected. Please check the stock symbol and try again."
                return f"Symbol {symbol} wasn't found, searched instead. " + await get_stock_price(new_symbol, original_symbol)
            else:
                logging.error(f"Search for symbol failed or returned no matches: {ticker_info}")
                return "Error fetching data. Please check the stock symbol and try again."
        
        last_refreshed = hist.index[-1]
        last_price = hist['Open'][-1]
        now_utc = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        return f"{symbol} last price: {last_price} USD. Data fetched at: {now_utc} UTC via Yahoo! Finance. [NOTE: Translate to the user if needed and do not omit any data, tell them that it's fetched from Yahoo! Finance]"
    except Exception as e:
        logging.error(f"Failed to fetch stock data: {str(e)}")
        return "Failed to fetch stock data. Please try again later."

# Main function to handle command-line arguments
async def main():
    if len(sys.argv) < 2:
        print("Usage: python api_get_stock_prices_yfinance.py <symbol or keyword>")
        return

    query = sys.argv[1]
    stock_data = await get_stock_price(query)
    print(stock_data)

if __name__ == "__main__":
    asyncio.run(main())
