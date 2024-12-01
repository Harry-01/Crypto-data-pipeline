import os
import requests
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime
from coin_gecko_extract import get_coin_kw_lists, get_coin_list

# Load environment variables
load_dotenv()

CLIENT_ID = os.getenv('REDDIT_APP_ID')
CLIENT_SECRET = os.getenv('REDDIT_SECRET_ID')
USERNAME = os.getenv('REDDIT_USERNAME')
PASSWORD = os.getenv('REDDIT_PASSWORD')

USER_AGENT = "ChangeMeClient/0.1 by harrymok_01"
BASE_URL = "https://oauth.reddit.com"


def get_access_token():
    """Fetch OAuth2 access token for Reddit API."""
    auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    data = {'grant_type': 'password', 'username': USERNAME, 'password': PASSWORD}
    headers = {'User-Agent': USER_AGENT}
    
    res = requests.post(f"https://www.reddit.com/api/v1/access_token", auth=auth, data=data, headers=headers)
    
    if res.status_code == 200:
        return res.json()['access_token']
    else:
        print(f"Error fetching access token: {res.status_code} - {res.text}")
        return None


def search_crypto_posts(crypto_kw, sort="relevance", limit=10):
    """
    Search for posts related to each cryptocurrency in a subreddit.
    
    Args:
        crypto_kw (list): List of cryptocurrency keywords to search for.
        sort (str): Sorting order (e.g., 'top', 'new', 'hot').
        limit (int): Number of posts to fetch for each cryptocurrency.

    Returns:
        pd.DataFrame: DataFrame containing all relevant posts.
    """
    token = get_access_token()
    if not token:
        return pd.DataFrame()
    
    headers = {
        'User-Agent': USER_AGENT,
        'Authorization': f'bearer {token}'
    }
    
    all_posts = []
    
    for crypto in crypto_kw:
        after = None  # Start with no pagination
        params = {'q': crypto, 'restrict_sr': 'true', 'sort': sort, 'limit': limit}

        while True:
            if after:
                params['after'] = after 

            url = f"{BASE_URL}/r/cryptocurrency/search"
            
            try:
                res = requests.get(url, headers=headers, params=params)
                res.raise_for_status()
                
                data = res.json()
                posts = [
                    {
                        'id': post['data']['id'],
                        'keyword': crypto,
                        'keywords': crypto_kw[1:],
                        'crypto_id': crypto_kw[0],
                        'title': post['data']['title'],
                        'selftext': post['data']['selftext'],
                        'score': post['data']['score'],
                        'upvote_ratio': post['data'].get('upvote_ratio', None),
                        'created_utc': datetime.utcfromtimestamp(post['data']['created_utc']),
                        'author': post['data']['author'],
                        'num_comments': post['data']['num_comments'],
                        'url': post['data']['url'],
                        'permalink': f"https://reddit.com{post['data']['permalink']}"
                    }
                    for post in data['data']['children']
                ]
                all_posts.extend(posts)

                after = data['data'].get('after', None)
                if not after:
                    break  # Exit if there's no more data
            except requests.exceptions.RequestException as e:
                print(f"Error fetching posts for {crypto}: {e}")
                break
        
    return pd.DataFrame(all_posts)



def all_crypto_posts(crypto_kws: list[list[str]]) -> pd.DataFrame:
    df_list = []  # Collect individual DataFrames in a list
    for kw_list in crypto_kws:
        posts = search_crypto_posts(kw_list, sort="relevance", limit=25)
        if posts is not None:
            df_list.append(posts)  # Append the DataFrame to the list
    
    # Concatenate all collected DataFrames into one
    if df_list:
        df = pd.concat(df_list, ignore_index=True)
    else:
        df = pd.DataFrame()  # Return an empty DataFrame if no data was collected
    
    return df


if __name__ == "__main__":
    coin_kw_list = get_coin_kw_lists()
    #print(coin_kw_list)
    data = all_crypto_posts(coin_kw_list)
    print(data.shape)
    print(data.head())

# crypto_posts_df = search_crypto_posts(crypto_list, sort="relevance", limit=25)

# if crypto_posts_df is not None:
#     print(crypto_posts_df.shape)
#     print(crypto_posts_df.head())
