import os
import re

from googleapiclient.discovery import build


def extract_video_id(video_input: str) -> str:
    """Extract video ID from a URL or return as-is if already an ID."""
    patterns = [
        r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, video_input)
        if match:
            return match.group(1)
    return video_input


def fetch_comments(video_id: str, api_key: str | None = None, max_results: int = 100) -> list[dict]:
    """Fetch top-level comments from a YouTube video."""
    api_key = api_key or os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError("YOUTUBE_API_KEY environment variable not set")

    youtube = build("youtube", "v3", developerKey=api_key)

    comments = []
    next_page_token = None

    while len(comments) < max_results:
        batch_size = min(100, max_results - len(comments))
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=batch_size,
            pageToken=next_page_token,
            textFormat="plainText",
            order="relevance",
        )
        response = request.execute()

        for item in response.get("items", []):
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            comments.append(
                {
                    "author": snippet["authorDisplayName"],
                    "text": snippet["textDisplay"],
                    "likes": snippet["likeCount"],
                    "published_at": snippet["publishedAt"],
                    "reply_count": item["snippet"]["totalReplyCount"],
                }
            )

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return comments
