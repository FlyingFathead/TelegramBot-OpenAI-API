# api_get_stock_prices_yfinance.py
#
# Stock price API fetching via Yahoo Finance (yfinance)
# Includes fetching the last 5 days' closing prices.
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import yfinance as yf
import requests
import logging
import sys
import asyncio
from datetime import datetime
import pandas as pd # Added for Timestamp checking if needed, though not strictly necessary here

# Configure logging
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# Configure basic logging if not already set elsewhere
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def search_stock_symbol(keyword):
    logging.info(f"Searching stock symbol for keyword: {keyword}")
    
    # 1) First try using the exact Ticker approach:
    try:
        ticker = yf.Ticker(keyword)
        hist_check = ticker.history(period="1d")
        if not hist_check.empty:
            # We have data => success
            return ticker
        # If hist is empty, keep going
    except Exception as e:
        logging.error(f"Error attempting to validate ticker for '{keyword}': {e}")
    
    # 2) If the direct Ticker() attempt fails or is empty, fallback to a Yahoo search
    logging.info(f"No direct Ticker() data. Attempting fallback search for: {keyword}")
    symbols_found = yahoo_finance_search(keyword)  # see function below

    if symbols_found:
        # If you want to automatically pick the best match (the first or so):
        best_candidate = symbols_found[0]  # or rank them somehow
        logging.info(f"Found possible symbol: {best_candidate}. Verifying with yf.Ticker()")
        ticker = yf.Ticker(best_candidate)
        hist_check = ticker.history(period="1d")
        if not hist_check.empty:
            return ticker
        else:
            logging.info(f"Fallback candidate {best_candidate} has no history.")
    # 3) If we still don’t get a valid ticker, just bail out
    return "No matches found."

def yahoo_finance_search(query):
    """
    Use the (unofficial) Yahoo Finance search endpoint to find possible symbols.
    Returns a list of symbols (strings) if any are found, empty list if not.
    """
    url = "https://query2.finance.yahoo.com/v1/finance/search"
    params = {"q": query, "quotesCount": 5}  # maybe fetch top 5
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        return []
    data = resp.json()
    if "quotes" not in data:
        return []
    
    symbols = []
    for item in data["quotes"]:
        # each item might have "symbol", "longname", etc.
        sym = item.get("symbol")
        if sym:
            symbols.append(sym)
    return symbols

# # Search for stock symbol (Using yfinance for direct data fetching)
# async def search_stock_symbol(keyword):
#     logging.info(f"Searching stock symbol for keyword: {keyword}")
#     # yfinance doesn't have a direct search function like some APIs.
#     # We often rely on Ticker() working or failing.
#     # For a more robust search, you might need another library or API,
#     # but Ticker() often works well with common names/symbols.
#     try:
#         ticker = yf.Ticker(keyword)
#         # Attempt to access some data to validate the ticker
#         if not ticker.info:
#             # If .info is empty, try fetching history as another check
#             hist_check = ticker.history(period="1d")
#             if hist_check.empty:
#                 logging.info(f"No valid data found for keyword: {keyword} using yf.Ticker.")
#                 return "No matches found."
#         logging.debug(f"Ticker info potentially found for {keyword}: {ticker.info.get('symbol', 'N/A')}")
#         return ticker
#     except Exception as e:
#         logging.error(f"Error attempting to validate ticker for keyword '{keyword}': {e}")
#         return "Error during symbol search."

# format conversion (currently not in use)
def format_float(value):
    """Return 'N/A' if value is NaN/None, else format with 2 decimals."""
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.2f}"

def format_int(value):
    """Return 'N/A' if value is NaN/None, else convert to int."""
    if value is None or pd.isna(value):
        return "N/A"
    return str(int(value))

# stock price fetch
async def get_stock_price(symbol, original_symbol=None):
    """
    - Fetch up to 5 days of daily data for `symbol`.
    - If empty, fallback to searching for the original symbol.
    - Return a message with:
        * 'most recent value' (from ticker.info if possible),
        * the last row from the daily history,
        * up to 5 days of close data,
        * plus the UTC fetch time.
    """
    if original_symbol is None:
        original_symbol = symbol

    # Simple loop check
    if symbol != original_symbol and symbol == original_symbol:
        logging.error(f"Symbol search loop detected for {symbol}.")
        return "Symbol search loop detected. Please check the stock symbol and try again."

    logging.info(f"Fetching stock data for symbol: {symbol}")
    ticker = yf.Ticker(symbol)

    try:
        # Attempt daily history (5 days)
        hist = ticker.history(period="5d", interval="1d")
        logging.debug(f"Fetched 5d daily history for {symbol}:\n{hist}")

        if hist.empty:
            # Fallback to search if no direct data
            logging.info(f"No history for {symbol}, attempting fallback search.")
            search_result = await search_stock_symbol(original_symbol)
            if isinstance(search_result, yf.Ticker):
                try:
                    new_sym = search_result.info.get('symbol')
                    if not new_sym:
                        return "Search returned Ticker but missing 'symbol' info."
                    if new_sym == symbol:
                        return f"No data for {symbol}, and no alternative found."
                    return (f"Symbol '{symbol}' not found. Found '{new_sym}' instead.\n"
                            + await get_stock_price(new_sym, original_symbol))
                except Exception as e:
                    logging.error(f"Error processing search result for {original_symbol}: {e}")
                    return "Error processing search result. Please check the stock symbol and try again."
            else:
                return "Error fetching data. Please check the stock symbol and try again."

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 1) Try to get the 'most recent' live-ish price from .info (if any)
        #    fallback to the last daily close if .info is incomplete
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        info_data = ticker.info
        # Some tickers have different naming: 'currentPrice', 'regularMarketPrice'
        current_price = info_data.get('regularMarketPrice') or info_data.get('currentPrice')
        # If we don't get anything from .info, we fallback to last daily close
        fallback_close = hist['Close'].iloc[-1]

        if current_price is None or pd.isna(current_price):
            # fallback
            formatted_current_price = format_float(fallback_close)
        else:
            # has a 'live' price
            formatted_current_price = format_float(current_price)

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 2) Get the last row from daily history
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        last_refreshed = hist.index[-1]
        last_refreshed_str = last_refreshed.strftime('%Y-%m-%d')

        last_open_val = hist['Open'].iloc[-1]
        last_close_val = hist['Close'].iloc[-1]
        last_volume_val = hist['Volume'].iloc[-1]

        if len(hist) > 1:
            prev_close_val = hist['Close'].iloc[-2]
        else:
            prev_close_val = None

        last_open_str = format_float(last_open_val)
        last_close_str = format_float(last_close_val)
        last_volume_str = format_int(last_volume_val)
        prev_close_str = format_float(prev_close_val)

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 3) Build a short summary of the last 5 closes
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        recent_closes = []
        for dt, row in hist.tail(5).iterrows():
            dt_str = dt.strftime('%Y-%m-%d')
            close_str = format_float(row['Close'])
            recent_closes.append(f"{dt_str}📉 {close_str}")
        recent_closes_text = " | ".join(recent_closes)

        # now_utc = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        now_dt = datetime.utcnow()
        now_utc = f"{now_dt.strftime('%B')} {now_dt.day}, {now_dt.year} {now_dt.strftime('%H:%M:%S')} UTC"

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 4) Construct final message
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        msg = (
            f"📈 **{symbol}**\n"
            f"   - **Most Recent Price**: {formatted_current_price}\n"
            f"   - **Last Trading Day in History**: {last_refreshed_str}\n"
            f"       Open: {last_open_str}, Close: {last_close_str}, Volume: {last_volume_str}\n"
            f"       Prev. Close: {prev_close_str}\n"
            f"\n"
            f"🕰 **Recent 5-Day Closes**:\n"
            f"  {recent_closes_text}\n"
            f"\n"
            f"Data fetched at: {now_utc} UTC via Yahoo! Finance. (<= TELL THE TIME AND SOURCE TO THE USER)\n"
            "💡 Note: The 'Most Recent Price' might reflect partial/intraday data if the market is open.\n"
            "🌐 [We do not omit any data; you can localize or translate and use additional emojis if needed. USE THE USER'S OWN NATURAL LANGUAGE IN YOUR REPLIES. If they asked in English, keep it in English, etc.]"
            "🤔 [Also note that the latest data doesn't necessarily mean that it's what we've closed with; the trading day can either be yet to be opened or ongoing.]"            
        )

        return msg

    except Exception as e:
        logging.exception(f"Failed to fetch/parse data for {symbol}: {str(e)}")
        return "Failed to fetch stock data. Please try again later."

async def main():
    if len(sys.argv) < 2:
        print("Usage: python api_get_stock_prices_yfinance.py <symbol or keyword>")
        return

    query = sys.argv[1]
    result = await get_stock_price(query)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())

# # Get stock price data with fallback to search
# async def get_stock_price(symbol, original_symbol=None):
#     if original_symbol is None:
#         original_symbol = symbol # Keep track of the initial request

#     # Simple loop prevention: if we already searched and landed on the same symbol again.
#     if symbol != original_symbol and symbol == original_symbol:
#         logging.error(f"Symbol search loop detected for {symbol}. Terminating.")
#         return "Symbol search loop detected. Please check the stock symbol and try again."

#     logging.info(f"Fetching stock data for symbol: {symbol}")
#     ticker = yf.Ticker(symbol)

#     try:
#         # Fetch basic info first - often includes current price and currency
#         ticker_info_data = ticker.info
#         currency = ticker_info_data.get('currency', 'N/A')
#         current_price = ticker_info_data.get('currentPrice', None) # Try to get live/recent price
#         if not current_price:
#              current_price = ticker_info_data.get('previousClose', None) # Fallback to previous close

#         # Fetch history for the last 5 trading days (includes Close prices)
#         hist = ticker.history(period="5d", interval="1d")
#         logging.debug(f"Stock data history (last 5d):\n{hist}")

#         if hist.empty:
#             logging.info(f"History for symbol {symbol} not found directly, attempting to search.")
#             # Fallback to search if direct symbol fetch yields no history
#             ticker_search_result = await search_stock_symbol(original_symbol) # Search using the *original* term
#             logging.debug(f"Search result for original symbol {original_symbol}: {ticker_search_result}")

#             if isinstance(ticker_search_result, yf.Ticker):
#                 # Extract the symbol found by the search
#                 try:
#                     # Accessing .info might be needed if search_stock_symbol just returns Ticker obj
#                     new_symbol_info = ticker_search_result.info
#                     if not new_symbol_info: # If .info is empty after search
#                          raise ValueError("Search returned Ticker object but .info is empty.")
#                     new_symbol = new_symbol_info.get('symbol')
#                     if not new_symbol:
#                          raise ValueError("Search returned Ticker object but symbol not found in .info.")

#                     logging.info(f"Found potential new symbol via search: {new_symbol}")
#                     # Avoid infinite loop if search returns the same symbol that failed
#                     if new_symbol == symbol:
#                         logging.error(f"Search returned the same symbol '{symbol}' which failed. Cannot proceed.")
#                         return f"Could not retrieve data for {symbol}. Search did not find an alternative."
#                     # Recursively call get_stock_price with the new symbol found by search
#                     return f"Symbol {original_symbol} data wasn't found directly. Found {new_symbol} instead.\n" + await get_stock_price(new_symbol, original_symbol)
#                 except Exception as e:
#                      logging.error(f"Error processing search result for {original_symbol}: {e}")
#                      return "Error processing search result. Please check the stock symbol and try again."
#             else:
#                 # If search didn't return a valid Ticker object
#                 logging.error(f"Search for symbol failed or returned no matches: {ticker_search_result}")
#                 return "Error fetching data. Please check the stock symbol and try again."

#         # --- Process the fetched history ---
#         last_refreshed_date = hist.index[-1].strftime('%Y-%m-%d') if isinstance(hist.index[-1], pd.Timestamp) else "N/A"

#         # Use the currentPrice from .info if available, otherwise the last close from history
#         latest_price_info = f"{current_price:.2f} {currency} (Live/Recent)" if current_price else f"{hist['Close'].iloc[-1]:.2f} {currency} (Last Close)"

#         # Format the closing prices for the last 5 days
#         closing_prices_str_parts = []
#         # Iterate through the DataFrame rows (index is date)
#         for date, row in hist.iterrows():
#             close_price = row['Close']
#             date_str = date.strftime('%Y-%m-%d')
#             closing_prices_str_parts.append(f"{date_str}: {close_price:.2f}")

#         # Reverse the list so the most recent day is first
#         closing_prices_str_parts.reverse()
#         closing_prices_str = "; ".join(closing_prices_str_parts)

#         now_utc = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

#         # Construct the final output string
#         return (f"{symbol} latest price: {latest_price_info}. "
#                 f"Recent prices (last 5 days, the latest might not indicate closing data if the business day is still ongoing): [{closing_prices_str}]. "
#                 f"Data fetched at: {now_utc} UTC via Yahoo! Finance. "
#                 f"[NOTE: Translate to the user if needed and do not omit any data, tell them that it's fetched from Yahoo! Finance and the exact time when it's fetched. You can use emojis to symbolize ups, downs and other factors.]")

#     except Exception as e:
#         logging.exception(f"Failed to fetch or process stock data for {symbol}: {str(e)}") # Use logging.exception to include traceback
#         # Provide a more specific error if it's likely due to an invalid symbol
#         if "No data found for ticker" in str(e) or "symbol may be delisted" in str(e):
#              return f"Failed to fetch stock data for '{symbol}'. It might be an invalid symbol or delisted. Please check and try again."
#         return "Failed to fetch stock data. Please try again later."

# # Main function to handle command-line arguments
# async def main():
#     if len(sys.argv) < 2:
#         print("Usage: python api_get_stock_prices_yfinance.py <symbol or keyword>")
#         return

#     query = sys.argv[1]
#     stock_data = await get_stock_price(query)
#     print(stock_data)

# if __name__ == "__main__":
#     asyncio.run(main())

# # # # // alt method
# # # get the stock price via Yahoo! Finance
# # async def get_stock_price(symbol, original_symbol=None):
# #     """
# #     Fetch daily stock data for the last 5 days. 
# #     Skip any 'placeholder' row for today if it has zero volume. 
# #     If no data found, attempt fallback search.
# #     """
# #     if original_symbol is None:
# #         original_symbol = symbol


# #     # Simple loop-prevention check
# #     if symbol != original_symbol and symbol == original_symbol:
# #         logging.error(f"Symbol search loop detected for {symbol}.")
# #         return "Symbol search loop detected. Please check the stock symbol and try again."

# #     logging.info(f"Fetching stock data for symbol: {symbol}")
# #     ticker = yf.Ticker(symbol)

# #     try:
# #         # Pull up to 5 days of daily data
# #         hist = ticker.history(period="5d", interval="1d")
# #         logging.debug(f"Raw history:\n{hist}")

# #         if hist.empty:
# #             logging.info(f"No history for {symbol}, attempting fallback search.")
# #             ticker_search_result = await search_stock_symbol(original_symbol)
# #             if isinstance(ticker_search_result, yf.Ticker):
# #                 try:
# #                     new_symbol = ticker_search_result.info.get('symbol')
# #                     if not new_symbol:
# #                         return "Search returned Ticker object but missing 'symbol' info."
# #                     if new_symbol == symbol:
# #                         return f"No data for {symbol}, and no alternative symbol found."
# #                     return (f"Symbol {symbol} wasn't found. Found {new_symbol} instead.\n"
# #                             + await get_stock_price(new_symbol, original_symbol))
# #                 except Exception as e:
# #                     logging.error(f"Error processing search result for {original_symbol}: {e}")
# #                     return "Error processing search result. Please check the stock symbol and try again."
# #             else:
# #                 return "Error fetching data. Please check the stock symbol and try again."

# #         # Filter out any 'phantom' row for today with zero volume
# #         today = pd.Timestamp.utcnow().normalize()
# #         mask = []
# #         for dt_index, row in hist.iterrows():
# #             row_date = dt_index.normalize()
# #             # If it's "today" and volume is 0, likely a placeholder => exclude
# #             if row_date == today and row['Volume'] == 0:
# #                 mask.append(False)
# #             else:
# #                 mask.append(True)
# #         hist = hist[mask]
# #         hist.sort_index(inplace=True)

# #         if hist.empty:
# #             return (f"No valid trading data for {symbol} in the last 5 days. "
# #                     "It might not be traded or only has partial data.")

# #         # Extract final row
# #         last_refreshed = hist.index[-1]
# #         last_refreshed_str = last_refreshed.strftime('%Y-%m-%d')

# #         last_open_val = hist['Open'].iloc[-1]
# #         last_close_val = hist['Close'].iloc[-1]
# #         last_volume_val = hist['Volume'].iloc[-1]

# #         # If you want previous close:
# #         if len(hist) > 1:
# #             prev_close_val = hist['Close'].iloc[-2]
# #         else:
# #             prev_close_val = None

# #         # Safely format them
# #         last_open_str = format_float(last_open_val)
# #         last_close_str = format_float(last_close_val)
# #         last_volume_str = format_int(last_volume_val)
# #         prev_close_str = format_float(prev_close_val)

# #         now_utc = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

# #         # Build recent closes text
# #         recent_closes = []
# #         for dt, row in hist.tail(5).iterrows():
# #             dt_str = dt.strftime('%Y-%m-%d')
# #             close_str = format_float(row['Close'])
# #             recent_closes.append(f"{dt_str}: {close_str}")
# #         recent_closes_text = "; ".join(recent_closes)

# #         msg = (
# #             f"{symbol} - Last trading day in data: {last_refreshed_str}\n"
# #             f"  Open: {last_open_str}, Close: {last_close_str}, Volume: {last_volume_str}\n"
# #             f"  Previous Close: {prev_close_str}\n"
# #             f"Recent closes (up to 5 days): [{recent_closes_text}]\n"
# #             f"Data fetched at: {now_utc} UTC via Yahoo! Finance.\n"
# #             "[NOTE: If the current date is missing or removed, it likely had no trading yet or zero volume. Use emojis in your response by default. Also, keep in mind that the latest data might still be from a trading day that's in progress.]"
# #         )
# #         return msg

# #     except Exception as e:
# #         logging.exception(f"Failed to fetch or process stock data for {symbol}: {str(e)}")
# #         return "Failed to fetch stock data. Please try again later."

# # async def main():
# #     if len(sys.argv) < 2:
# #         print("Usage: python api_get_stock_prices_yfinance.py <symbol or keyword>")
# #         return

# #     query = sys.argv[1]
# #     result = await get_stock_price(query)
# #     print(result)

# # if __name__ == "__main__":
# #     asyncio.run(main())

# # # # api_get_stock_prices_yfinance.py
# # # #
# # # # Stock price API fetching via Yahoo Finance (yfinance)
# # # #
# # # # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# # # # github.com/FlyingFathead/TelegramBot-OpenAI-API/
# # # # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# # # import yfinance as yf
# # # import logging
# # # import sys
# # # import asyncio
# # # from datetime import datetime

# # # # Configure logging
# # # # logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# # # # Search for stock symbol (Using yfinance for direct data fetching)
# # # async def search_stock_symbol(keyword):
# # #     logging.info(f"Searching stock symbol for keyword: {keyword}")
# # #     ticker = yf.Ticker(keyword)
    
# # #     if not ticker.info:
# # #         logging.info("No matches found.")
# # #         return "No matches found."

# # #     logging.debug(f"Ticker info: {ticker.info}")
# # #     return ticker

# # # # Get stock price data with fallback to search
# # # async def get_stock_price(symbol, original_symbol=None):
# # #     if original_symbol is None:
# # #         original_symbol = symbol

# # #     if symbol != original_symbol and symbol == original_symbol:
# # #         logging.error(f"Symbol search loop detected for {symbol}. Terminating.")
# # #         return "Symbol search loop detected. Please check the stock symbol and try again."

# # #     logging.info(f"Fetching stock data for symbol: {symbol}")
# # #     ticker = yf.Ticker(symbol)

# # #     try:
# # #         # hist = ticker.history(period="1d", interval="1m")
# # #         # // get broader history
# # #         hist = ticker.history(period="5d", interval="1d")
# # #         logging.debug(f"Stock data history: {hist}")

# # #         if hist.empty:
# # #             logging.info(f"Symbol {symbol} not found, attempting to search for symbol.")
# # #             # Fallback to search if direct symbol fetch fails
# # #             ticker_info = await search_stock_symbol(symbol)
# # #             logging.debug(f"Search result for symbol {symbol}: {ticker_info}")
# # #             if isinstance(ticker_info, yf.Ticker):
# # #                 new_symbol = ticker_info.info['symbol']
# # #                 logging.info(f"Found new symbol: {new_symbol}")
# # #                 if new_symbol == symbol:
# # #                     logging.error(f"Symbol search loop detected for {symbol}. Terminating.")
# # #                     return "Symbol search loop detected. Please check the stock symbol and try again."
# # #                 return f"Symbol {symbol} wasn't found, searched instead. " + await get_stock_price(new_symbol, original_symbol)
# # #             else:
# # #                 logging.error(f"Search for symbol failed or returned no matches: {ticker_info}")
# # #                 return "Error fetching data. Please check the stock symbol and try again."
        
# # #         last_refreshed = hist.index[-1]

# # #         # # // old method; deprecated
# # #         # last_price = hist['Open'][-1]
        
# # #         last_price = hist['Open'].iloc[-1]
# # #         now_utc = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
# # #         return f"{symbol} last price: {last_price} USD. Data fetched at: {now_utc} UTC via Yahoo! Finance. [NOTE: Translate to the user if needed and do not omit any data, tell them that it's fetched from Yahoo! Finance and the exact time when it's fetched]"
# # #     except Exception as e:
# # #         logging.error(f"Failed to fetch stock data: {str(e)}")
# # #         return "Failed to fetch stock data. Please try again later."

# # # # Main function to handle command-line arguments
# # # async def main():
# # #     if len(sys.argv) < 2:
# # #         print("Usage: python api_get_stock_prices_yfinance.py <symbol or keyword>")
# # #         return

# # #     query = sys.argv[1]
# # #     stock_data = await get_stock_price(query)
# # #     print(stock_data)

# # # if __name__ == "__main__":
# # #     asyncio.run(main())
