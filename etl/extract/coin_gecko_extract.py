import os
import requests
from dotenv import load_dotenv
from typing import Optional
import pandas as pd

load_dotenv()

COIN_GECKO_API_KEY = os.getenv('COIN_GECKO_API_KEY')


# Base URL for CoinGecko API
BASE_URL = "https://api.coingecko.com/api/v3"


def fetch_data(endpoint: str, params=None) -> Optional[dict]:
    url = f"{BASE_URL}{endpoint}?x_cg_demo_api_key={COIN_GECKO_API_KEY}"
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None
    
def get_coin_list() -> Optional[pd.DataFrame]:
    """Fetch the top 10 coins based on market cap."""
    endpoint = "/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=30"
    data = fetch_data(endpoint)
    if data:
        df = pd.DataFrame(data)
        return df
    return None

def get_coin_kw_lists() -> list[list[str]]:
    """Get list of cryptocurrency keywords."""
    coin_list = get_coin_list()
    all_keywords = []
    for _, row in coin_list.iterrows():
        # Create a list of keywords for each coin
        coin_kw = [row["id"], row["name"].lower(), row["symbol"].lower()]
        all_keywords.append(coin_kw)
    return all_keywords

def get_coin_code():
    """Get list of cryptocurrency codes."""
    coin_list = get_coin_list()
    all_keywords = []
    for _, row in coin_list.iterrows():
        # Create a list of keywords for each coin
        coin_kw = [row["symbol"].upper()]
        all_keywords.append(coin_kw)
    return all_keywords


def get_coins_markets(ids) -> Optional[pd.DataFrame]:
    """Fetch market data for the top N coins by market cap."""
    endpoint = "/coins/markets"
    ids_str = ",".join(ids)
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "ids": ids_str
    }
    data = fetch_data(endpoint, params)
    if data:
        df = pd.DataFrame(data)
        return df
    return None


if __name__ == "__main__":
    # 1. Get list of coins
    pd.set_option('display.max_columns', None)
    coin_list_df = get_coin_list()
    print("Coin List:")
    print(coin_list_df.head(20))

    # # 4. Get market data for top 10 coins by market cap
    market_df = get_coins_markets(coin_list_df['id'].tolist())
    print("\nMarket Data:")
    print(market_df.shape)
    print(market_df.head())