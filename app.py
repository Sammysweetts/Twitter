import streamlit as st
import snscrape.modules.twitter as sntwitter
import pandas as pd

# ----------------
# Function to extract media links from a Twitter user
# ----------------
def extract_media_links(username, limit=50):
    tweets = []
    scraped_count = 0
    query = f'from:{username} has:media'

    for tweet in sntwitter.TwitterSearchScraper(query).get_items():
        if scraped_count >= limit:
            break

        tweet_data = {
            'date': tweet.date.strftime("%Y-%m-%d %H:%M:%S"),
            'url': tweet.url,
            'media': []
        }

        if tweet.media:
            media_links = []
            for media in tweet.media:
                if hasattr(media, 'fullUrl'):  # photo
                    media_links.append(media.fullUrl)
                elif hasattr(media, 'variants'):  # video or gif
                    video_urls = [v.url for v in media.variants if 'video' in v.contentType]
                    media_links.extend(video_urls)
            tweet_data['media'] = media_links

        tweets.append(tweet_data)
        scraped_count += 1

    return tweets

# ----------------
# Streamlit UI
# ----------------
st.set_page_config(page_title="Twitter Media URL Extractor", layout="wide")
st.title("🐦 Twitter Media Extractor (Images/Videos)")

with st.form("input_form"):
    username = st.text_input("Enter Twitter Username (without @):", "urstrulyMahesh")
    num_links = st.number_input("Number of Media Tweets to Extract:", min_value=1, max_value=500, value=50)
    submitted = st.form_submit_button("Extract Media Links")

if submitted:
    st.info(f"Extracting media tweets for @{username}...")
    results = extract_media_links(username.strip(), num_links)

    if results:
        df = pd.DataFrame(results)
        df['Media Preview'] = df['media'].apply(lambda media: media[0] if media else None)

        # Display table
        st.subheader("📄 Extracted Media Tweets")
        st.dataframe(df[["date", "url", "Media Preview"]])

        # Display previews
        st.subheader("🖼️ Media Previews")
        for idx, row in df.iterrows():
            st.markdown(f"**Tweet URL**: [{row['url']}]({row['url']})")
            if row['media']:
                for media_url in row['media']:
                    if media_url.endswith(('.jpg', '.png', '.jpeg', '.webp')):
                        st.image(media_url, width=300)
                    elif media_url.endswith('.mp4'):
                        st.video(media_url)
            st.markdown("---")

        # Download as CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download as CSV", data=csv, file_name=f"{username}_media_links.csv", mime='text/csv')
    else:
        st.warning("No media tweets found or user doesn't exist.")
