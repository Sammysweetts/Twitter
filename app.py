import streamlit as st
import snscrape.modules.twitter as sntwitter
import pandas as pd
import requests
import os
from zipfile import ZipFile
import re

# Function to sanitize filenames
def sanitize_filename(filename):
    return re.sub(r'[\/:*?"<>|]', '_', filename)

# Function to download video
def download_video(video_url, filename):
    try:
        with requests.get(video_url, stream=True) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Error downloading video: {e}")
        return False

st.title("Twitter Data Downloader")
st.write("Download posts and videos from any public Twitter account.")

username = st.text_input("Enter Twitter Username (without @):")
num_posts = st.number_input("Number of recent posts to fetch:", min_value=1, max_value=1000, value=10)

if st.button("Download Data"):
    if username:
        try:
            st.info("Fetching data... Please wait.")

            # Create a directory to store data
            if not os.path.exists(username):
                os.makedirs(username)

            tweets_list = []
            video_files = []

            scraper = sntwitter.TwitterUserScraper(username)
            for i, tweet in enumerate(scraper.get_items()):
                if i >= num_posts:
                    break

                tweet_data = {
                    'Date': tweet.date,
                    'ID': tweet.id,
                    'URL': tweet.url,
                    'Content': tweet.rawContent,
                    'Username': tweet.user.username,
                    'Likes': tweet.likeCount,
                    'Retweets': tweet.retweetCount
                }
                tweets_list.append(tweet_data)

                if tweet.media:
                    for medium in tweet.media:
                        if isinstance(medium, sntwitter.Video):
                            # Find the variant with the highest bitrate
                            best_variant = None
                            for variant in medium.variants:
                                if variant.bitrate and (not best_variant or variant.bitrate > best_variant.bitrate):
                                    best_variant = variant
                            
                            if best_variant:
                                video_filename = os.path.join(username, f"{tweet.id}.mp4")
                                if download_video(best_variant.url, video_filename):
                                    video_files.append(video_filename)

            if not tweets_list:
                st.warning("No tweets found for this user.")
            else:
                # Create a DataFrame and save to CSV
                df = pd.DataFrame(tweets_list)
                csv_filename = os.path.join(username, f"{username}_tweets.csv")
                df.to_csv(csv_filename, index=False)
                st.success(f"Successfully fetched {len(tweets_list)} tweets.")

                # Create a zip file
                zip_filename = f"{username}_twitter_data.zip"
                with ZipFile(zip_filename, 'w') as zipf:
                    zipf.write(csv_filename, os.path.basename(csv_filename))
                    for video_file in video_files:
                        zipf.write(video_file, os.path.basename(video_file))

                # Provide a download button for the zip file
                with open(zip_filename, "rb") as f:
                    st.download_button(
                        label="Download ZIP",
                        data=f,
                        file_name=zip_filename,
                        mime="application/zip"
                    )

                # Clean up individual files and directory
                for file in [csv_filename] + video_files:
                    os.remove(file)
                os.rmdir(username)
                os.remove(zip_filename)

        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.warning("Please enter a Twitter username.")
