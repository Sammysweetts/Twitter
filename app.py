import streamlit as st
import snscrape.modules.twitter as sntwitter
from yt_dlp import YoutubeDL
import pandas as pd
from pathlib import Path
from datetime import datetime
import tempfile
import zipfile
import io
import time
import re

st.set_page_config(page_title="X/Twitter Posts + Video Downloader (No API)", page_icon="🎬")

st.title("🎬 X/Twitter Posts + Video Downloader (No API)")
st.caption("Public accounts only. Respects site Terms. Excludes retweets by default.")

st.info(
    "Use this only for content you’re authorized to access. Respect the website’s Terms of Service and robots.txt. "
    "Do not scrape private or paywalled content, and avoid sending excessive requests."
)


def normalize_username(u: str) -> str:
    u = (u or "").strip()
    u = u.lstrip("@")
    # Allow letters, digits, and underscore (typical handle)
    u = re.sub(r"[^0-9A-Za-z_]", "", u)
    return u


def tweet_has_video(tweet) -> bool:
    media = getattr(tweet, "media", None)
    if not media:
        return False
    for m in media:
        name = m.__class__.__name__.lower()
        if "video" in name or "gif" in name:
            return True
    return False


@st.cache_data(show_spinner=False, ttl=60 * 30)
def scrape_posts(username: str, limit: int, exclude_retweets: bool, exclude_replies: bool):
    query_parts = [f"from:{username}"]
    if exclude_retweets:
        query_parts.append("exclude:retweets")
    if exclude_replies:
        query_parts.append("exclude:replies")
    query = " ".join(query_parts)

    scraper = sntwitter.TwitterSearchScraper(query)
    items = []
    for i, tweet in enumerate(scraper.get_items()):
        items.append(tweet)
        if len(items) >= limit:
            break

    rows = []
    for t in items:
        text = getattr(t, "rawContent", None) or getattr(t, "content", "") or ""
        rows.append(
            {
                "id": t.id,
                "date": t.date.isoformat() if getattr(t, "date", None) else "",
                "username": getattr(t.user, "username", ""),
                "displayname": getattr(t.user, "displayname", ""),
                "url": t.url,
                "content": text,
                "lang": getattr(t, "lang", ""),
                "replyCount": getattr(t, "replyCount", None),
                "retweetCount": getattr(t, "retweetCount", None),
                "likeCount": getattr(t, "likeCount", None),
                "quoteCount": getattr(t, "quoteCount", None),
                "hasVideo": tweet_has_video(t),
                "isReply": getattr(t, "inReplyToTweetId", None) is not None,
            }
        )

    df = pd.DataFrame(rows)
    return df


def download_twitter_video(url: str, out_dir: Path, base_name: str, quiet=True) -> Path | None:
    out_dir.mkdir(parents=True, exist_ok=True)
    # Force mp4 remux if needed; requires ffmpeg (provided by packages.txt)
    ydl_opts = {
        "outtmpl": str(out_dir / f"{base_name}.%(ext)s"),
        "merge_output_format": "mp4",
        "format": "bv*+ba/b[ext=mp4]/best[ext=mp4]/best",
        "noplaylist": True,
        "retries": 3,
        "concurrent_fragment_downloads": 1,
        "quiet": quiet,
        "no_warnings": quiet,
        # A UA helps reduce random blocks; keep it generic
        "http_headers": {"User-Agent": "Mozilla/5.0"},
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Try to compute final path
            # If ffmpeg remuxed to mp4, ensure .mp4
            ext = "mp4"
            final_path = out_dir / f"{base_name}.{ext}"
            # If that file doesn't exist, try the prepared filename
            if not final_path.exists():
                try:
                    guess = Path(ydl.prepare_filename(info))
                    if guess.exists():
                        return guess
                except Exception:
                    pass
            return final_path if final_path.exists() else None
    except Exception:
        return None


with st.form("controls"):
    handle = st.text_input("Public account handle", placeholder="jack or @jack")
    col1, col2, col3 = st.columns(3)
    with col1:
        limit = st.number_input("Max posts to scan", min_value=1, max_value=5000, value=300, step=50, help="Higher values take longer.")
    with col2:
        exclude_rt = st.checkbox("Exclude retweets", value=True)
    with col3:
        exclude_replies = st.checkbox("Exclude replies", value=True)
    only_download_videos = st.checkbox("Only download videos (still export metadata for all scanned posts)", value=True)
    submitted = st.form_submit_button("Scan account")

if submitted:
    username = normalize_username(handle)
    if not username:
        st.error("Please enter a valid public account handle.")
        st.stop()

    with st.spinner(f"Fetching posts from @{username} …"):
        df = scrape_posts(username, int(limit), exclude_rt, exclude_replies)

    if df.empty:
        st.warning("No posts found for the given parameters.")
        st.stop()

    total = len(df)
    video_df = df[df["hasVideo"] == True].copy()
    st.success(f"Found {total} posts. Posts with video: {len(video_df)}.")

    with st.expander("Preview (first 25 rows)"):
        st.dataframe(df.head(25), use_container_width=True)

    # Prepare to download and package
    download_videos = st.toggle("Download videos now", value=True if len(video_df) > 0 else False)
    rate_delay = st.slider("Delay between video downloads (seconds)", 0.0, 5.0, 0.5, 0.5, help="Be gentle to the site.")
    start = st.button("Build ZIP")

    if start:
        if only_download_videos and not download_videos:
            st.info("You chose not to download videos; will export metadata only.")

        progress = st.progress(0)
        status = st.empty()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            videos_dir = tmpdir / "videos"
            videos_dir.mkdir(exist_ok=True, parents=True)

            downloaded = []
            attempted = 0
            if download_videos and len(video_df) > 0:
                rows = list(video_df.itertuples(index=False))
                total_videos = len(rows)
                for idx, row in enumerate(rows, start=1):
                    attempted += 1
                    status.write(f"Downloading {idx}/{total_videos}: {row.url}")
                    base_name = f"{row.username}_{row.id}"
                    path = download_twitter_video(row.url, videos_dir, base_name, quiet=True)
                    if path is not None and path.exists():
                        downloaded.append(path)
                    progress.progress(int(100 * idx / total_videos))
                    time.sleep(rate_delay)
                status.write(f"Downloaded {len(downloaded)} / {attempted} video posts.")
            else:
                status.write("Skipping video downloads.")

            # Build CSVs in memory and ZIP everything
            created_at = datetime.utcnow().isoformat() + "Z"
            meta_buf = io.StringIO()
            df.to_csv(meta_buf, index=False)
            meta_buf.seek(0)

            video_meta_buf = io.StringIO()
            video_df.to_csv(video_meta_buf, index=False)
            video_meta_buf.seek(0)

            readme_text = f"""Dataset built at: {created_at}
Account: @{username}
Total scanned posts: {len(df)}
Posts with video: {len(video_df)}
Excluded retweets: {exclude_rt}
Excluded replies: {exclude_replies}

Notes:
- This archive contains post metadata (CSV) and any successfully downloaded public videos.
- Use only as permitted by the site's Terms of Service. Do not redistribute without rights.
- Tools: snscrape + yt-dlp (no official API used).
"""

            zip_bytes = io.BytesIO()
            with zipfile.ZipFile(zip_bytes, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("README.txt", readme_text)
                zf.writestr("posts.csv", meta_buf.getvalue())
                zf.writestr("video_posts.csv", video_meta_buf.getvalue())
                # Add videos, if any
                if videos_dir.exists():
                    for p in videos_dir.glob("*"):
                        if p.is_file():
                            zf.write(p, arcname=f"videos/{p.name}")

            zip_bytes.seek(0)
            st.success("ZIP built.")
            st.download_button(
                label="Download ZIP",
                data=zip_bytes,
                file_name=f"{username}_twitter_export.zip",
                mime="application/zip",
            )
