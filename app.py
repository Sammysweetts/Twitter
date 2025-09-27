import streamlit as st
import requests
from bs4 import BeautifulSoup
from ntscraper import Nitter
import pandas as pd
from io import BytesIO

# --- Haftungsausschluss ---
st.set_page_config(
    page_title="Twitter Video Downloader",
    page_icon="🎬",
    layout="wide"
)

st.warning(
    "**Haftungsausschluss:** Dieses Tool ist nur für Bildungszwecke bestimmt. "
    "Das automatisierte Extrahieren von Inhalten ohne Genehmigung kann gegen die Nutzungsbedingungen von Twitter verstoßen. "
    "Die Zuverlässigkeit kann nicht garantiert werden, da sie von externen Website-Strukturen abhängt."
)

# --- Funktionen zum Scrapen und Herunterladen ---

def get_video_downloader(tweet_url):
    """
    Ruft den direkten Download-Link für ein Video von einem Drittanbieter-Dienst ab.
    """
    try:
        response = requests.post("https://twitsave.com/info", data={"url": tweet_url})
        response.raise_for_status()  # Überprüft auf HTTP-Fehler
        soup = BeautifulSoup(response.text, "lxml")
        
        download_button = soup.find("div", class_="origin-top-right").find_all("a")[0]
        if download_button:
            return download_button["href"]
    except requests.exceptions.RequestException as e:
        st.error(f"Fehler bei der Kontaktaufnahme mit dem Download-Dienst: {e}")
    except (IndexError, AttributeError):
        st.warning(f"Konnte keinen Download-Link für {tweet_url} finden. Das Video könnte nicht verfügbar oder der Tweet geschützt sein.")
    return None

def download_video_content(video_url):
    """
    Lädt den Videoinhalt von einer URL herunter und gibt ihn als Bytes zurück.
    """
    try:
        video_response = requests.get(video_url, stream=True)
        video_response.raise_for_status()
        
        video_bytes = BytesIO()
        for chunk in video_response.iter_content(chunk_size=8192):
            video_bytes.write(chunk)
        video_bytes.seek(0)
        return video_bytes
    except requests.exceptions.RequestException as e:
        st.error(f"Konnte das Video nicht von der URL herunterladen: {e}")
        return None

def scrape_twitter_videos(username, num_posts):
    """
    Scrapt Twitter nach Beiträgen mit Videos von einem bestimmten Benutzer.
    """
    scraper = Nitter()
    try:
        tweets = scraper.get_tweets(username, mode='user', number=num_posts, filters=['videos'])
        video_posts = []
        for tweet in tweets['tweets']:
            if tweet['pictures'] or tweet['videos']:
                video_posts.append({
                    "text": tweet['text'],
                    "link": tweet['link'],
                    "date": tweet['date']
                })
        return video_posts
    except Exception as e:
        st.error(f"Ein Fehler ist beim Scrapen aufgetreten: {e}")
        return []

# --- Streamlit UI-Layout ---

st.title("🎬 Twitter Massen-Video-Downloader")
st.markdown("Geben Sie einen öffentlichen Twitter-Benutzernamen ein, um die neuesten Beiträge mit Videos abzurufen und herunterzuladen.")

with st.form("input_form"):
    twitter_username = st.text_input("Twitter-Benutzername (ohne @)", placeholder="z.B. Google")
    num_posts_to_fetch = st.number_input("Anzahl der zu überprüfenden neuesten Beiträge", min_value=5, max_value=200, value=20, step=5)
    submit_button = st.form_submit_button(label="Videos abrufen")

if submit_button and twitter_username:
    with st.spinner(f"Suche nach Videos in den letzten {num_posts_to_fetch} Beiträgen von @{twitter_username}..."):
        video_posts = scrape_twitter_videos(twitter_username, num_posts_to_fetch)

        if not video_posts:
            st.warning("Keine Beiträge mit Videos im angegebenen Bereich gefunden. Versuchen Sie, die Anzahl der zu überprüfenden Beiträge zu erhöhen, oder überprüfen Sie den Benutzernamen.")
        else:
            st.success(f"{len(video_posts)} Beiträge mit Videos gefunden!")
            
            # DataFrame zur Anzeige und zum CSV-Download vorbereiten
            display_data = []

            for i, post in enumerate(video_posts):
                st.markdown("---")
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Beitragstext:** {post['text']}")
                    st.caption(f"🔗 [Original-Tweet]({post['link']})")
                
                with col2:
                    with st.spinner("Download-Link wird abgerufen..."):
                        download_url = get_video_downloader(post['link'])
                
                post["download_url"] = download_url
                display_data.append(post)

                if download_url:
                    video_content = download_video_content(download_url)
                    if video_content:
                        st.download_button(
                            label="📥 Video herunterladen",
                            data=video_content,
                            file_name=f"{twitter_username}_video_{i+1}.mp4",
                            mime="video/mp4",
                            key=f"download_{i}"
                        )
                else:
                    st.error("Download fehlgeschlagen.")

            # CSV-Download-Button
            st.markdown("---")
            st.header("Daten als CSV exportieren")
            df = pd.DataFrame(display_data)
            csv = df.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                "Beitragsdaten als CSV herunterladen",
                csv,
                f"{twitter_username}_posts.csv",
                "text/csv",
                key='download-csv'
            )
else:
    if submit_button:
        st.error("Bitte geben Sie einen Twitter-Benutzernamen ein.")
