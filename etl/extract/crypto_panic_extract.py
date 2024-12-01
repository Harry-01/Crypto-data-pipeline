import os
import requests
from dotenv import load_dotenv
import pandas as pd
from typing import Optional
from coin_gecko_extract import get_coin_code

load_dotenv()

BASE_URL = "https://cryptopanic.com/api/free/v1/posts/"

AUTH_TOKEN = os.getenv('CRYPTO_PANIC_API_KEY')

def fetch_data(params: dict) -> Optional[dict]:
    """Fetch data from the API with specified parameters."""
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
        return response.json()  # Return the full response JSON
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None


def fetch_all_posts(params: dict) -> pd.DataFrame:
    """Fetch all posts with pagination."""
    all_posts = []
    while True:
        # Fetch the current page of data
        data = fetch_data(params)
        if data is None or "results" not in data:
            break  # Stop if no results or no more data

        # Append current page of posts to all_posts
        all_posts.append(pd.DataFrame(data["results"]))  # Adjust key to match the API response

        # Check for the next page in the response
        next_page = data.get('next', None)
        if next_page:
            # If there is a next page, update the params to fetch the next page
            params["page"] = next_page.split("page=")[-1]  # Extract the page number from the URL
        else:
            break  # Exit the loop if no more pages

    # Concatenate all pages into a single DataFrame
    return pd.concat(all_posts, ignore_index=True)


def fetch_public_posts() -> pd.DataFrame:
    """Fetch public posts."""
    params = {"auth_token": AUTH_TOKEN, "public": "true"}
    return fetch_all_posts(params)

def fetch_filtered_posts(currencies=None, kind=None, filter_type=None) -> pd.DataFrame:
    """Fetch posts with filters."""
    params = {
        "auth_token": AUTH_TOKEN,
        "public": "true",
        "currencies": ",".join(currencies) if currencies else None,
        "kind": kind,
        "filter": filter_type,
    }
    return fetch_all_posts(params)



if __name__ == "__main__":
    data = fetch_filtered_posts(currencies='ETH', kind='news', filter_type='bullish')
    #data = fetch_public_posts()
    print(data.shape)
    #print(data.head())  # Display the first few rows of the DataFrame