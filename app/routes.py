from flask import Flask, jsonify, render_template, request

from .summarizer import summarize
from .youtube import extract_video_id, fetch_comments, get_transcript

VALID_MODES = {"transcript", "comments", "both"}


def register(app: Flask) -> None:
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.post("/summarize")
    def summarize_endpoint():
        payload = request.get_json(silent=True) or {}
        video_input = payload.get("video_id")
        mode = payload.get("mode")

        if not video_input or not isinstance(video_input, str):
            return jsonify({"error": "Missing or invalid 'video_id'."}), 400
        if mode not in VALID_MODES:
            return (
                jsonify({"error": f"Invalid 'mode'. Expected one of: {sorted(VALID_MODES)}."}),
                400,
            )

        video_id = extract_video_id(video_input)
        result: dict[str, str] = {}

        if mode in ("transcript", "both"):
            try:
                transcript_text = get_transcript(video_id)
            except Exception as exc:
                return jsonify({"error": f"Failed to fetch transcript: {exc}"}), 502
            if not transcript_text.strip():
                return jsonify({"error": "Transcript is empty."}), 404
            try:
                result["transcript_summary"] = summarize(transcript_text, "transcript")
            except Exception as exc:
                return jsonify({"error": f"Failed to summarize transcript: {exc}"}), 502

        if mode in ("comments", "both"):
            try:
                comments = fetch_comments(video_id)
            except Exception as exc:
                return jsonify({"error": f"Failed to fetch comments: {exc}"}), 502
            comments_text = "\n".join(c["text"] for c in comments if c.get("text"))
            if not comments_text.strip():
                return jsonify({"error": "No comments available."}), 404
            try:
                result["comments_summary"] = summarize(comments_text, "comments")
            except Exception as exc:
                return jsonify({"error": f"Failed to summarize comments: {exc}"}), 502

        return jsonify(result)
