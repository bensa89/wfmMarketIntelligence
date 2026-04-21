from app.config import settings


def call_llm(prompt: str, max_tokens: int = 1024) -> str:
    if settings.llm_provider == "ollama":
        return _call_ollama(prompt, max_tokens=max_tokens)
    return _call_claude(prompt, max_tokens=max_tokens)


def _call_claude(prompt: str, max_tokens: int = 1024) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _call_ollama(prompt: str, max_tokens: int = 1024) -> str:
    import httpx

    response = httpx.post(
        f"{settings.ollama_base_url}/api/generate",
        json={"model": settings.ollama_model, "prompt": prompt, "stream": False, "options": {"num_predict": max_tokens}},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["response"]
