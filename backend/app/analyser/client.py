import time
import logging

from app.config import settings

logger = logging.getLogger(__name__)

_anthropic_client = None
_opencode_client = None

_OPENCODE_RETRY_ATTEMPTS = 3
_OPENCODE_RETRY_BACKOFF = 30  # seconds; error says retry_after=120 but 30s is enough for transient 524s


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        _anthropic_client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key, timeout=120.0
        )
    return _anthropic_client


def _get_opencode_client():
    global _opencode_client
    if _opencode_client is None:
        from openai import OpenAI
        _opencode_client = OpenAI(
            api_key=settings.opencode_api_key,
            base_url=settings.opencode_base_url,
            timeout=180.0,
            max_retries=0,  # we handle retries ourselves
        )
    return _opencode_client


def call_llm(prompt: str, max_tokens: int = 1024, caller: str = "") -> str:
    label = caller or "unknown"
    logger.info("LLM call start [caller=%s provider=%s max_tokens=%d]", label, settings.llm_provider, max_tokens)
    t0 = time.monotonic()
    if settings.llm_provider == "ollama":
        text, input_tokens, output_tokens, estimated = _call_ollama(prompt, max_tokens=max_tokens)
        model = settings.ollama_model
    elif settings.llm_provider == "opencode":
        text, input_tokens, output_tokens, estimated = _call_opencode(prompt, max_tokens=max_tokens)
        model = settings.opencode_model
    else:
        text, input_tokens, output_tokens, estimated = _call_claude(prompt, max_tokens=max_tokens)
        model = settings.claude_model
    elapsed = time.monotonic() - t0
    logger.info("LLM call done [caller=%s duration=%.1fs chars=%d]", label, elapsed, len(text))
    _record_llm_call(
        caller=label,
        provider=settings.llm_provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated=estimated,
        duration_ms=int(elapsed * 1000),
    )
    return text


def _record_llm_call(
    caller: str, provider: str, model: str,
    input_tokens: int, output_tokens: int, estimated: bool, duration_ms: int,
) -> None:
    from app.database import SessionLocal
    from app.models.llm_call import LlmCall

    db = SessionLocal()
    try:
        db.add(LlmCall(
            caller=caller,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated=estimated,
            duration_ms=duration_ms,
        ))
        db.commit()
    except Exception:
        logger.warning("Failed to record LLM usage", exc_info=True)
        db.rollback()
    finally:
        db.close()


def _call_claude(prompt: str, max_tokens: int = 1024) -> tuple[str, int, int, bool]:
    client = _get_anthropic_client()
    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text
    return text, message.usage.input_tokens, message.usage.output_tokens, False


def _call_opencode(prompt: str, max_tokens: int = 1024) -> str:
    """Stream the response to avoid Cloudflare's 120-second proxy timeout (error 524)."""
    client = _get_opencode_client()
    last_exc: Exception | None = None
    for attempt in range(_OPENCODE_RETRY_ATTEMPTS):
        if attempt > 0:
            wait = _OPENCODE_RETRY_BACKOFF * attempt
            logger.warning("opencode retry %d/%d after %ds", attempt + 1, _OPENCODE_RETRY_ATTEMPTS, wait)
            time.sleep(wait)
        try:
            chunks: list[str] = []
            with client.chat.completions.create(
                model=settings.opencode_model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            ) as stream:
                for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta.content
                    if delta:
                        chunks.append(delta)
            return "".join(chunks)
        except Exception as exc:
            last_exc = exc
            logger.warning("opencode attempt %d failed: %s", attempt + 1, exc)
    raise last_exc


def _call_ollama(prompt: str, max_tokens: int = 1024) -> tuple[str, int, int, bool]:
    import httpx

    response = httpx.post(
        f"{settings.ollama_base_url}/api/generate",
        json={
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens},
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data["response"], data.get("prompt_eval_count", 0), data.get("eval_count", 0), False
