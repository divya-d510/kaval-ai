"""Provider-agnostic LLM client.

Default provider is Google Gemini (free tier — https://aistudio.google.com/apikey).
Set GEMINI_API_KEY in .env. If ANTHROPIC_API_KEY is set instead, the Anthropic
Claude API is used. Override explicitly with LLM_PROVIDER=gemini|anthropic.

Exposes two calls used by all services:
    ask(system, user)              -> str
    ask_json(system, user, schema) -> dict  (validated-ish JSON per schema)
"""

import json
import os
import re
import time

from dotenv import load_dotenv

load_dotenv()


def _provider() -> str:
    explicit = os.getenv("LLM_PROVIDER")
    if explicit:
        return explicit.lower()
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    raise RuntimeError(
        "No LLM API key found. Set GEMINI_API_KEY (free: https://aistudio.google.com/apikey) "
        "or ANTHROPIC_API_KEY in .env"
    )


GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
ANTHROPIC_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-8")

_gemini_client = None
_anthropic_client = None


def _gemini():
    global _gemini_client
    if _gemini_client is None:
        from google import genai

        _gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _gemini_client


def _anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic

        _anthropic_client = anthropic.Anthropic()
    return _anthropic_client


def _gemini_generate(**kwargs):
    """generate_content with retry on transient 503/429 (free-tier congestion)."""
    from google.genai import errors

    last = None
    for attempt in range(4):
        try:
            return _gemini().models.generate_content(**kwargs)
        except errors.APIError as e:
            if e.code in (429, 503):
                last = e
                time.sleep(2 ** attempt * 2)
            else:
                raise
    raise last


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    return json.loads(text)


def ask(system: str, user: str, max_tokens: int = 4096) -> str:
    if _provider() == "gemini":
        from google.genai import types

        resp = _gemini_generate(
            model=GEMINI_MODEL,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
            ),
        )
        return resp.text or ""

    response = _anthropic().messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return next((b.text for b in response.content if b.type == "text"), "")


def ask_json(system: str, user: str, schema: dict, max_tokens: int = 4096) -> dict:
    if _provider() == "gemini":
        from google.genai import types

        schema_note = (
            "\n\nRespond with ONLY a JSON object matching this JSON Schema "
            "(no markdown, no commentary):\n" + json.dumps(schema)
        )
        resp = _gemini_generate(
            model=GEMINI_MODEL,
            contents=user + schema_note,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
                response_mime_type="application/json",
            ),
        )
        return _extract_json(resp.text or "{}")

    response = _anthropic().messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)
