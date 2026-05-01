from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound


def get_transcript(video_id: str, lang: str = "en") -> str:
    ytt = YouTubeTranscriptApi()
    try:
        transcript = ytt.fetch(video_id, languages=[lang])
    except NoTranscriptFound:
        transcript = ytt.fetch(video_id)

    return " ".join(entry.text for entry in transcript)
