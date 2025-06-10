from logging import getLogger
from typing import Optional

import httpx

logger = getLogger(__name__)

# Default Ollama configuration
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "gemma3:12b"

_http_client: Optional[httpx.AsyncClient] = None


def get_ollama_client() -> httpx.AsyncClient:
    """Get Ollama HTTP client instance."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            base_url=OLLAMA_BASE_URL,
            timeout=httpx.Timeout(300.0),  # 5 minute timeout for long transcripts
        )
        logger.info("Initialized Ollama HTTP client with base URL %s", OLLAMA_BASE_URL)
    return _http_client


async def test_ollama_connection() -> bool:
    """Test if Ollama is running and accessible."""
    try:
        client = get_ollama_client()
        response = await client.get("/api/tags")
        response.raise_for_status()
        data = response.json()
        models = [model["name"] for model in data.get("models", [])]
        logger.info("Ollama connection successful. Available models: %s", models)

        if OLLAMA_MODEL not in models:
            logger.warning(
                "Model %s not found in available models: %s", OLLAMA_MODEL, models
            )
            return False
        return True
    except Exception as e:
        logger.error("Ollama connection test failed: %s", e)
        return False


async def chat_with_ollama(system_prompt: str, user_prompt: str) -> str:
    """
    Send a chat request to Ollama.

    Args:
        system_prompt: System message content
        user_prompt: User message content

    Returns:
        LLM response content
    """
    # Test connection first
    if not await test_ollama_connection():
        error_msg = f"Cannot connect to Ollama or model {OLLAMA_MODEL} not available"
        raise RuntimeError(error_msg)

    client = get_ollama_client()

    # Format messages for Ollama API
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0},
    }

    logger.debug(
        "Sending Ollama request - Model: %s, System prompt length: %d, User prompt length: %d",
        OLLAMA_MODEL,
        len(system_prompt),
        len(user_prompt),
    )

    try:
        logger.debug(
            "Making request to Ollama: %s",
            {
                **payload,
                "messages": [
                    {"role": m["role"], "content": f"{m['content'][:100]}..."}
                    for m in messages
                ],
            },
        )
        response = await client.post("/api/chat", json=payload)
        response.raise_for_status()

        data = response.json()
        logger.debug("Raw Ollama response keys: %s", list(data.keys()))

        if "message" not in data:
            error_msg = f"Invalid response format from Ollama: {data}"
            raise ValueError(error_msg)

        content = data["message"]["content"]

        logger.debug(
            "Ollama response received, length: %d, content preview: %s",
            len(content),
            content[:200] + "..." if len(content) > 200 else content,
        )
        return content
    except httpx.ConnectError as e:
        logger.error("Cannot connect to Ollama at %s: %s", OLLAMA_BASE_URL, str(e))
        error_msg = f"Cannot connect to Ollama at {OLLAMA_BASE_URL}. Is Ollama running?"
        raise RuntimeError(error_msg) from e
    except httpx.TimeoutException as e:
        logger.error("Ollama request timed out: %s", str(e))
        error_msg = (
            "Ollama request timed out. The model might be taking too long to respond."
        )
        raise RuntimeError(error_msg) from e
    except httpx.HTTPStatusError as e:
        error_text = ""
        try:
            error_text = e.response.text
        except Exception:
            error_text = "Unable to read error response"
        logger.error("Ollama HTTP error: %s - %s", e.response.status_code, error_text)
        error_msg = f"Ollama HTTP error {e.response.status_code}: {error_text}"
        raise RuntimeError(error_msg) from e
    except Exception as e:
        logger.error(
            "Ollama LLM call failed with unexpected error: %s (%s)",
            str(e),
            type(e).__name__,
        )
        error_msg = f"Ollama LLM call failed: {str(e)}"
        raise RuntimeError(error_msg) from e


async def close_ollama_client():
    """Close the Ollama HTTP client."""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
