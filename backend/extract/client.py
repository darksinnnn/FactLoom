"""
FactLoom Groq LLM Client
Implements model routing, rate-limit backoff, and JSON mode per agents.md.
"""

import os
import time
import json
import logging
import httpx
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Model Routing per agents.md
MODEL_ROUTING = {
    "extractor": "openai/gpt-oss-120b",
    "canonicalizer_fast": "openai/gpt-oss-120b",
    "canonicalizer_adjudicator": "openai/gpt-oss-120b",
    "reconciliation_adjudicator": "openai/gpt-oss-120b",
    "query_parser": "openai/gpt-oss-120b",
    "answer_composer": "openai/gpt-oss-120b",
    "answer_synthesizer": "openai/gpt-oss-120b",
    "vision_fallback": "meta-llama/llama-4-maverick-17b-128e-instruct"
}

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

class GroqClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self.timeout = 60.0

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model_role: str = "extractor",
        temperature: float = 0.0,
        response_json: bool = True,
        reasoning_effort: Optional[str] = "low",
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Call Groq chat completion with automatic model routing and rate-limit backoff.
        """
        if not self.api_key or self.api_key.startswith("your_groq"):
            raise ValueError(
                "GROQ_API_KEY is not configured. Please add your Groq API key to .env"
            )

        model = MODEL_ROUTING.get(model_role, "openai/gpt-oss-120b")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }

        if reasoning_effort and "gpt-oss" in model:
            payload["reasoning_effort"] = reasoning_effort

        if response_json:
            payload["response_format"] = {"type": "json_object"}

        delay = 1.0
        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(GROQ_API_URL, headers=headers, json=payload)
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data["choices"][0]["message"]["content"]
                        actual_model = data.get("model", payload["model"])
                        if response_json:
                            parsed = json.loads(content)
                            if isinstance(parsed, dict):
                                parsed["_model_used"] = actual_model
                            return parsed
                        return {"content": content, "_model_used": actual_model}
                    
                    elif resp.status_code == 429:
                        # Parse retry-after header or error message
                        retry_after = 2.0
                        try:
                            if "retry-after" in resp.headers:
                                retry_after = float(resp.headers["retry-after"])
                            else:
                                err_data = resp.json()
                                msg = err_data.get("error", {}).get("message", "")
                                import re
                                match = re.search(r"try again in ([\d\.]+)s", msg)
                                if match:
                                    retry_after = float(match.group(1)) + 1.0
                        except Exception:
                            pass

                        # If rate limit wait is significant or on second retry attempt, fall back to alternative model
                        if retry_after > 3.0 or attempt >= 1:
                            alt_model = "qwen/qwen3.8-27b" if "120b" in payload.get("model", "") else "openai/gpt-oss-120b"
                            if payload.get("model") != alt_model:
                                logger.warning(f"429 rate limit hit on {payload.get('model')} (retry_after={retry_after:.1f}s, attempt={attempt+1}). Falling back immediately to {alt_model}...")
                                payload["model"] = alt_model
                                time.sleep(0.5)
                                continue
                            elif retry_after > 5.0:
                                raise RuntimeError(f"Groq 429 rate limit cooldown exceeds threshold ({retry_after:.1f}s). Engaging deterministic backstop.")

                        wait_time = min(max(delay, retry_after) + 0.5, 4.0)
                        logger.warning(f"Groq 429 rate limit hit. Waiting {wait_time:.2f}s before retry (attempt {attempt+1}/{max_retries})...")
                        time.sleep(wait_time)
                        delay = min(delay * 1.5, 4.0)
                    else:
                        err_msg = f"Groq API error {resp.status_code}: {resp.text}"
                        logger.error(err_msg)
                        # Do not retry on 413 payload too large or input token limit exceeded
                        if resp.status_code == 413 or "Request too large" in resp.text or "too large for model" in resp.text:
                            raise RuntimeError(err_msg)
                        if attempt == max_retries - 1:
                            raise RuntimeError(err_msg)
                        time.sleep(delay)
                        delay *= 1.5

            except (httpx.RequestError, json.JSONDecodeError) as e:
                logger.warning(f"Request failed: {e}. Retrying in {delay}s...")
                if attempt == max_retries - 1:
                    raise
                time.sleep(delay)
                delay *= 1.5

        raise RuntimeError(f"Groq call failed after {max_retries} attempts.")
