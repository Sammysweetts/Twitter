import streamlit as st
import pandas as pd
from ntscraper import Nitter
import requests
import zipfile
import io

# Function to convert DataFrame to CSV for download
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# Function to scrape Twitter data
def get_tweets_data(username, mode, number):
    scraper = Nitter()
    try:
        # The 'get_tweets' function is a generator. We need to iterate through it.
        tweets_generator = scraper.get_tweets(username, mode=mode, number=number)
        tweets_list = list(tweets_generator['tweets'])
        return tweets_list, None
    except Exception as e:
        return None, str(e)

# --- Streamlit App ---

st.set_page_config(page_title="Twitter Media Downloader", layout="wide")

st.title("🐦 Twitter (X) Bulk Media Downloader")
st.markdown("""
This app allows you to download posts (text, images, and videos) from any public Twitter/X account without needing an API key.
**Disclaimer:** This tool relies on web scraping and may break if Twitter/X changes its website structure. Please use it responsibly.
""")

# --- User Inputs ---
with st.sidebar:
    st.header("Scraping Options")
    twitter_username = st.text_input("Enter Twitter Username (e.g., NASA)", "NASA")
    num_posts = st.number_input("Number of recent posts to fetch", min_value=10, max_value=1000, value=50, step=10)
    
    start_button = st.button("Start Scraping", type="primary")

# --- Main Logic ---
if start_button and twitter_username:
    with st.spinner(f"Scraping the latest {num_posts} posts from '{twitter_username}'... This may take a moment."):
        # Fetch data
        scraped_data, error = get_tweets_data(twitter_username, mode='user', number=num_posts)

    if error:
        st.error(f"An error occurred: {error}")
        st.warning("This could be due to a temporary issue with Twitter/X or a change in their website. Please try again later.")
    elif not scraped_data:
        st.warning("No posts were found. The account might be private, suspended, or does not exist.")
    else:
        st.success(f"Successfully scraped {len(scraped_data)} posts!")

        # Process data into a pandas DataFrame
        processed_data = []
        for tweet in scraped_data:
            # Check for media (pictures or videos)
            if tweet['pictures'] or tweet['videos']:
                processed_data.append({
                    'link': tweet['link'],
                    'text': tweet['text'],
                    'date': tweet['date'],
                    'likes': tweet['stats']['likes'],
                    'retweets': tweet['stats']['retweets'],
                    'comments': tweet['stats']['comments'],
                    'pictures': ", ".join(tweet['pictures']),
                    'videos': ", ".join(tweet['videos'])
                })
        
        if not processed_data:
            st.info("Found posts, but none of them contained images or videos in the batch.")
        else:
            df = pd.DataFrame(processed_data)
            
            st.subheader("📊 Scraped Data with Media")
            st.dataframe(df)

            # --- Download Section ---
            st.subheader("📥 Download Data")

            col1, col2 = st.columns(2)

            with col1:
                # Download CSV
                csv_data = convert_df_to_csv(df)
                st.download_button(
                    label="Download Data as CSV",
                    data=csv_data,
                    file_name=f"{twitter_username}_posts.csv",
                    mime="text/csv",
                )
            
            with col2:
                # Download Media as ZIP
                st.write("Click below to prepare and download all images and videos in a single ZIP file.")
                if st.button("Prepare Media ZIP File"):
                    with st.spinner("Downloading and zipping media... Please wait."):
                        # Create a zip file in memory
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                            for index, row in df.iterrows():
                                # Download Pictures
                                pic_urls = row['pictures'].split(", ") if row['pictures'] else []
                                for i, url in enumerate(pic_urls):
                                    if url:
                                        try:
                                            response = requests.get(url)
                                            response.raise_for_status() # Raise an exception for bad status codes
                                            # Create a unique filename
                                            post_id = row['link'].split('/')[-1]
                                            filename = f"{twitter_username}_{post_id}_pic_{i+1}.jpg"
                                            zip_file.writestr(filename, response.content)
                                        except requests.exceptions.RequestException as e:
                                            st.warning(f"Could not download image {url}: {e}")
                                
                                # Download Videos
                                video_urls = row['videos'].split(", ") if row['videos'] else []
                                for i, url in enumerate(video_urls):
                                    if url:
                                        try:
                                            response = requests.get(url)
                                            response.raise_for_status()
                                            post_id = row['link'].split('/')[-1]
                                            filename = f"{twitter_username}_{post_id}_vid_{i+1}.mp4"
                                            zip_file.writestr(filename, response.content)
                                        except requests.exceptions.RequestException as e:
                                            st.warning(f"Could not download video {url}: {e}")

                        # Move to the beginning of the buffer before reading
                        zip_buffer.seek(0)
                        
                        # Provide the zip file for download
                        st.download_button(
                            label="✅ Click to Download ZIP",
                            data=zip_buffer,
                            file_name=f"{twitter_username}_media.zip",
                            mime="application/zip",
                        )
                        st.success("ZIP file is ready for download!")

else:
    st.info("Enter a username and click 'Start Scraping' to begin.")
