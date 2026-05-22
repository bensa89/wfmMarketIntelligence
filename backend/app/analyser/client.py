from app.config import settings

_anthropic_client = None
_opencode_client = None


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
            max_retries=1,
        )
    return _opencode_client


def call_llm(prompt: str, max_tokens: int = 1024) -> str:
    if settings.llm_provider == "ollama":
        return _call_ollama(prompt, max_tokens=max_tokens)
    if settings.llm_provider == "opencode":
        return _call_opencode(prompt, max_tokens=max_tokens)
    return _call_claude(prompt, max_tokens=max_tokens)


def _call_claude(prompt: str, max_tokens: int = 1024) -> str:
    client = _get_anthropic_client()
    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _call_opencode(prompt: str, max_tokens: int = 1024) -> str:
    client = _get_opencode_client()
    response = client.chat.completions.create(
        model=settings.opencode_model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def _call_ollama(prompt: str, max_tokens: int = 1024) -> str:
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
    return response.json()["response"]
