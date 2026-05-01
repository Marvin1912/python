#!/usr/bin/env python3
import argparse
import sys

from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, VideoUnavailable

from app.youtube import get_transcript


def main():
    parser = argparse.ArgumentParser(description="Fetch YouTube video transcript")
    parser.add_argument("video_id", help="YouTube video ID (e.g. dQw4w9WgXcQ)")
    parser.add_argument("--lang", default="en", help="Preferred language code (default: en)")
    parser.add_argument("--timestamps", action="store_true", help="Include timestamps")
    args = parser.parse_args()

    if not args.timestamps:
        try:
            print(get_transcript(args.video_id, args.lang))
        except VideoUnavailable:
            print(f"Error: video '{args.video_id}' is unavailable.", file=sys.stderr)
            sys.exit(1)
        return

    ytt = YouTubeTranscriptApi()
    try:
        transcript = ytt.fetch(args.video_id, languages=[args.lang])
    except NoTranscriptFound:
        transcript = ytt.fetch(args.video_id)
    except VideoUnavailable:
        print(f"Error: video '{args.video_id}' is unavailable.", file=sys.stderr)
        sys.exit(1)

    for entry in transcript:
        minutes, seconds = divmod(int(entry.start), 60)
        print(f"[{minutes:02d}:{seconds:02d}] {entry.text}")


if __name__ == "__main__":
    main()
