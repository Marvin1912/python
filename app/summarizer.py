"""LangChain + Claude Haiku summarization logic."""

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

load_dotenv()

MODEL = "claude-haiku-4-5-20251001"

INSTRUCTIONS = {
    "transcript": (
        "Summarize the following YouTube video transcript in a few paragraphs, "
        "highlighting the main topics, key arguments, and notable takeaways."
    ),
    "comments": (
        "Summarize the audience reaction based on these YouTube comments. "
        "Capture the overall sentiment, recurring themes, praise, and criticism."
    ),
}

_PROMPT = PromptTemplate.from_template(
    "{instruction}\n\n---\n{text}\n---\n\nSummary:"
)

_llm = ChatAnthropic(model=MODEL)
_chain = _PROMPT | _llm | StrOutputParser()


def summarize(text: str, kind: str) -> str:
    if kind not in INSTRUCTIONS:
        raise ValueError(f"Unsupported kind: {kind!r}. Expected 'transcript' or 'comments'.")
    return _chain.invoke({"instruction": INSTRUCTIONS[kind], "text": text})
