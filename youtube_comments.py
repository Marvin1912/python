"""CLI wrapper around app.youtube.comments.

Usage:
    Set the YOUTUBE_API_KEY environment variable, then run:
        python youtube_comments.py <video_id_or_url>
"""

import os
import sys

from app.youtube import extract_video_id, fetch_comments


def main():
    if len(sys.argv) < 2:
        print("Usage: python youtube_comments.py <video_id_or_url> [max_results]")
        sys.exit(1)

    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("Error: YOUTUBE_API_KEY environment variable not set.")
        sys.exit(1)

    video_input = sys.argv[1]
    max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    video_id = extract_video_id(video_input)
    print(f"Fetching up to {max_results} comments for video ID: {video_id}\n")

    comments = fetch_comments(video_id, api_key, max_results)

    for i, comment in enumerate(comments, 1):
        print(f"[{i}] {comment['author']} ({comment['published_at'][:10]})")
        print(f"    Likes: {comment['likes']}  Replies: {comment['reply_count']}")
        print(f"    {comment['text'][:200]}")
        print()

    print(f"Total comments fetched: {len(comments)}")


if __name__ == "__main__":
    main()
