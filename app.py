import streamlit as st
import pandas as pd
import asyncio
import nest_asyncio
import os
import twint2
import subprocess

# Allow asyncio to run in nested event loops
nest_asyncio.apply()

st.set_page_config(page_title="Twitter (X) Downloader", layout="wide")

st.title("🐦 Twitter (X) Post + Video Downloader (No API)")

username = st.text_input("Enter Twitter @username (no @ symbol)", "elonmusk")
tweet_limit = st.slider("Number of tweets to scrape", 10, 200, 50)

if st.button("Scrape Now"):
    if not username:
        st.error("Please enter a valid username.")
    else:
        with st.spinner("Scraping tweets..."):
            # Setup Twint2 configuration
            c = twint2.Config()
            c.Username = username
            c.Limit = tweet_limit
            c.Pandas = True
            c.Store_object = True
            c.Hide_output = True

            # Run TWINT2 search
            asyncio.run(twint2.run.Search(c))
            tweets_df = twint2.storage.panda.Tweets_df

        if tweets_df.empty:
            st.warning("No tweets found or scraping failed.")
        else:
            st.success(f"Successfully scraped {len(tweets_df)} tweets from @{username}")

            # Show table
            tweets_df_display = tweets_df[["date", "tweet", "link"]]
            st.dataframe(tweets_df_display)

            # Allow CSV download
            csv = tweets_df_display.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📁 Download CSV",
                data=csv,
                file_name=f"{username}_tweets.csv",
                mime="text/csv",
            )

            # Find Tweets likely containing video
            st.subheader("🎥 Tweets with Videos (Prediction Based)")
            video_tweets_df = tweets_df[tweets_df["tweet"].str.contains("https://t.co/")]
            likely_video_df = video_tweets_df[
                video_tweets_df["tweet"].str.contains("video", case=False)
                | video_tweets_df["tweet"].str.contains("watch", case=False)
                | video_tweets_df["tweet"].str.contains("youtu", case=False)
            ]

            if not likely_video_df.empty:
                st.info(f"Found {len(likely_video_df)} tweet(s) that likely contain videos.")

                st.write("Some sample video tweet links:")
                st.write(likely_video_df["link"].tolist())

                # Download videos with yt-dlp
                download_dir = f"downloads/{username}_videos"
                os.makedirs(download_dir, exist_ok=True)

                with st.spinner("Downloading videos..."):
                    for url in likely_video_df["link"].tolist():
                        try:
                            subprocess.run(
                                [
                                    "yt-dlp",
                                    url,
                                    "-o",
                                    f"{download_dir}/%(title).50s.%(ext)s",
                                ],
                                check=True,
                            )
                        except Exception as e:
                            st.error(f"Error downloading {url}: {e}")

                st.success(f"Downloaded videos to `{download_dir}` (check Streamlit Cloud workspace files)")

            else:
                st.warning("Couldn't find any tweets that look like video content.")
