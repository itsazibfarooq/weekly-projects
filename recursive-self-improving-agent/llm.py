"""The frozen "hardware": one function that calls the model.

Agents can call llm() however they like. They are never asked to edit this file,
and the harness never edits it, so the model weights stay fixed. All improvement
happens in the code *around* the model (the scaffold, or harness).
"""
import os

import anthropic

MODEL = os.environ.get("RSI_MODEL", "claude-opus-5-5")
client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY (or an `ant auth login` profile)


def llm(prompt: str, effort: str = "low") -> str:
    """Send one prompt and return the text reply. effort: low | medium | high | xhigh | max."""
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=64000,
        output_config={"effort": effort},
        betas=["server-side-fallback-2026-07-01"],  # if a safety classifier declines,
        fallbacks="default",                        # the API retries on a fallback model
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason == "refusal":
        return ""
    return "".join(b.text for b in msg.content if b.type == "text")
