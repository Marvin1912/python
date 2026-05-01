const form = document.getElementById("summarize-form");
const submitBtn = document.getElementById("submit-btn");
const statusEl = document.getElementById("status");
const errorEl = document.getElementById("error");
const resultsEl = document.getElementById("results");
const transcriptResult = document.getElementById("transcript-result");
const commentsResult = document.getElementById("comments-result");

function reset() {
    errorEl.hidden = true;
    errorEl.textContent = "";
    resultsEl.hidden = true;
    transcriptResult.hidden = true;
    commentsResult.hidden = true;
    transcriptResult.querySelector(".summary-text").textContent = "";
    commentsResult.querySelector(".summary-text").textContent = "";
}

function showError(message) {
    errorEl.textContent = message;
    errorEl.hidden = false;
}

function renderResults(data) {
    let any = false;
    if (data.transcript_summary) {
        transcriptResult.querySelector(".summary-text").textContent = data.transcript_summary;
        transcriptResult.hidden = false;
        any = true;
    }
    if (data.comments_summary) {
        commentsResult.querySelector(".summary-text").textContent = data.comments_summary;
        commentsResult.hidden = false;
        any = true;
    }
    resultsEl.hidden = !any;
    if (!any) {
        showError("No summary returned.");
    }
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    reset();

    const videoInput = document.getElementById("video-input").value.trim();
    const mode = form.querySelector('input[name="mode"]:checked').value;

    submitBtn.disabled = true;
    statusEl.hidden = false;

    try {
        const response = await fetch("/summarize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ video_id: videoInput, mode }),
        });

        let data;
        try {
            data = await response.json();
        } catch {
            throw new Error(`Unexpected response (HTTP ${response.status}).`);
        }

        if (!response.ok) {
            throw new Error(data.error || `Request failed (HTTP ${response.status}).`);
        }

        renderResults(data);
    } catch (err) {
        showError(err.message || "Something went wrong.");
    } finally {
        statusEl.hidden = true;
        submitBtn.disabled = false;
    }
});
