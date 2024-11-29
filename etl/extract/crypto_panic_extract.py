import os
import requests
from dotenv import load_dotenv
import pandas as pd
from typing import Optional

load_dotenv()

BASE_URL = "https://cryptopanic.com/api/free/v1/posts/"

AUTH_TOKEN = os.getenv('CRYPTO_PANIC_API_KEY')

def fetch_data(params: dict) -> Optional[pd.DataFrame]:
    """Fetch data from the API with specified parameters."""
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
        data = response.json()
        if data and "results" in data:
            return pd.DataFrame(data["results"])  # Adjust key to match the API response
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None
    
def fetch_public_posts() -> pd.DataFrame:
    """Fetch public posts."""
    params = {"auth_token": AUTH_TOKEN, "public": "true"}
    return fetch_data(params)
    


def fetch_filtered_posts(currencies=None, region=None, kind=None, filter_type=None) -> pd.DataFrame:
    """Fetch posts with filters."""
    params = {
        "auth_token": AUTH_TOKEN,
        "public": "true",
        "currencies": ",".join(currencies) if currencies else None,
        "regions": ",".join(region) if region else None,
        "kind": kind,
        "filter": filter_type,
    }
    return fetch_data(params)


if __name__ == "__main__":
    data = fetch_public_posts()
    print(data.head())  # Display the first few rows of the DataFrame