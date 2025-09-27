import streamlit as st
import snscrape.modules.twitter as sntwitter
import pandas as pd
import subprocess
import os

st.set_page_config(page_title="Twitter Post & Video Downloader", layout="wide")

st.title("🐦 Twitter Post & Video Downloader (No API)")

# Input: Twitter username
username = st.text_input("Enter Twitter (X) username (without @)", "elonmusk")

# Input: Number of posts to scrape
limit = st.slider("Number of posts to scrape", min_value=10, max_value=500, step=10, value=50)

if st.button("Scrape Twitter Data"):
    if not username:
        st.error("Please enter a valid Twitter username.")
    else:
        tweets_list = []
        tweet_urls = []
        with st.spinner("Scraping tweets..."):
            for i, tweet in enumerate(sntwitter.TwitterUserScraper(username).get_items()):
                if i >= limit:
                    break
                tweets_list.append([
                    tweet.date,
                    tweet.url,
                    tweet.content,
                    tweet.media
                ])
                tweet_urls.append(tweet.url)

        df = pd.DataFrame(tweets_list, columns=["Date", "URL", "Content", "Media"])
        st.success(f"Scraped {len(df)} tweets/posts from @{username}")
        st.dataframe(df)

        # Download CSV
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Tweets as CSV", csv, f"{username}_tweets.csv", "text/csv")

        # Extract tweets with videos
        df_videos = df[df['Media'].astype(str).str.contains("Video", na=False)]

        if len(df_videos) > 0:
            st.subheader("🎥 Tweets with Video")
            st.dataframe(df_videos[["Date", "URL", "Content"]])
            st.warning("This may take time based on number of videos...")

            download_folder = f"downloads/{username}_videos"
            os.makedirs(download_folder, exist_ok=True)

            with st.spinner("Downloading videos..."):
                for url in df_videos["URL"]:
                    try:
                        subprocess.run([
                            "yt-dlp", url,
                            "-o", f"{download_folder}/%(id)s.%(ext)s"
                        ], check=True)
                    except Exception as e:
                        st.error(f"Failed to download video: {url} - Error: {e}")

            st.success(f"Videos downloaded to: {download_folder}")
            st.write("Download individual files via [Streamlit Cloud workspace] or set up archive logic.")

        else:
            st.info("No videos found in the scraped tweets.")
