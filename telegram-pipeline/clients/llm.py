"""
DeepSeek LLM wrapper via OpenAI-compatible API.

Static BIZ context goes into the system prompt — DeepSeek automatically
caches repeated system prompts (context caching is built-in, no extra config needed).
Variable content (message text, bio, channel description) goes in the user message.
"""

import json
import logging
from openai import OpenAI, APITimeoutError, APIConnectionError, APIStatusError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from config import DEEPSEEK_API_KEY

logger = logging.getLogger(__name__)

MODEL = "deepseek-chat"
MAX_TOKENS = 512
BASE_SYSTEM = "You are a JSON-only responder. Output ONLY valid JSON with no markdown fences, no explanation, no extra text."


def validate_enum(value: str | None, allowed: set[str], default: str) -> str:
    """Normalize LLM output to closest allowed enum value, or return default.

    Case-insensitive exact match first, then substring containment fallback.
    Logs a warning when coercion or default is used.
    """
    if not value:
        return default
    val_stripped = value.strip()
    # Exact case-insensitive match
    for a in allowed:
        if a.lower() == val_stripped.lower():
            return a
    # Substring containment (e.g. "Publisher (selling ads)" → "Publisher")
    # Sort by length desc so longer matches win (e.g. "irrelevant" before "relevant")
    for a in sorted(allowed, key=len, reverse=True):
        if a.lower() in val_stripped.lower():
            logger.warning("LLM enum coerced: '%s' → '%s'", value, a)
            return a
    logger.warning("LLM returned unexpected value '%s', allowed=%s, using default='%s'", value, allowed, default)
    return default


def _is_retryable(error: BaseException) -> bool:
    """Return True for transient API errors that should be retried."""
    if isinstance(error, (APITimeoutError, APIConnectionError)):
        return True
    if isinstance(error, APIStatusError) and error.status_code in (429, 500, 502, 503):
        return True
    return False


class LLMClient:
    def __init__(self):
        self._client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
            timeout=60.0,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    def _call_api(self, system_content: str, user_prompt: str, max_tokens: int) -> str:
        """Call DeepSeek API with retry on transient errors (timeout, connection, 5xx/429)."""
        response = self._client.chat.completions.create(
            model=MODEL,
            max_tokens=max_tokens,
            temperature=0.0,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        if not response.choices:
            raise ValueError("API returned empty choices list")
        return response.choices[0].message.content.strip()

    def analyze(
        self,
        user_prompt: str,
        expected_keys: list[str],
        static_context: str = "",
        max_tokens: int = MAX_TOKENS,
    ) -> dict:
        """
        Send prompt to DeepSeek, parse JSON response.

        static_context: large static text (niche lists, product info, etc.)
                        prepended to system prompt — DeepSeek caches repeated
                        system prompts automatically (no explicit cache_control needed).
        user_prompt:    variable part (the actual message/bio/channel text).
        expected_keys:  keys to extract from JSON response.
        max_tokens:     max output tokens (default 512; use 1024 for longer responses).

        Returns dict with expected_keys. On any error: all keys → None + llm_error key.
        """
        system_content = BASE_SYSTEM
        if static_context:
            system_content = f"{BASE_SYSTEM}\n\n{static_context}"

        raw = ""
        try:
            raw = self._call_api(system_content, user_prompt, max_tokens)

            # Strip markdown fences if model adds them despite instructions
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

            data = json.loads(raw)
            return {k: data.get(k) for k in expected_keys}

        except json.JSONDecodeError as e:
            logger.error("LLM JSON parse error: %s | raw: %.300s", e, raw)
            return {k: None for k in expected_keys} | {"llm_error": f"json_parse: {e}"}
        except (APITimeoutError, APIConnectionError) as e:
            logger.error("LLM call failed after retries: %s", e)
            return {k: None for k in expected_keys} | {"llm_error": str(e)}
        except APIStatusError as e:
            logger.error("LLM API error (status %d): %s", e.status_code, e)
            return {k: None for k in expected_keys} | {"llm_error": str(e)}
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return {k: None for k in expected_keys} | {"llm_error": str(e)}
