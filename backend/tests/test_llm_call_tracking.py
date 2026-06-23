from unittest.mock import MagicMock, patch


def test_call_llm_claude_records_exact_token_usage(db_session, monkeypatch):
    import app.analyser.client as client_module
    from app.config import settings
    from app.models.llm_call import LlmCall

    monkeypatch.setattr(settings, "llm_provider", "claude")
    monkeypatch.setattr(settings, "claude_model", "claude-haiku-4-5-20251001")

    mock_usage = MagicMock(input_tokens=120, output_tokens=45)
    mock_message = MagicMock(usage=mock_usage)
    mock_message.content = [MagicMock(text="hello world")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message
    client_module._anthropic_client = mock_client

    result = client_module.call_llm("prompt text", caller="analyser")

    assert result == "hello world"
    rows = db_session.query(LlmCall).all()
    assert len(rows) == 1
    assert rows[0].caller == "analyser"
    assert rows[0].provider == "claude"
    assert rows[0].model == "claude-haiku-4-5-20251001"
    assert rows[0].input_tokens == 120
    assert rows[0].output_tokens == 45
    assert rows[0].estimated is False


def test_call_llm_ollama_records_exact_token_usage(db_session, monkeypatch):
    import app.analyser.client as client_module
    from app.config import settings
    from app.models.llm_call import LlmCall

    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "ollama_model", "llama3")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "response": "ollama reply",
        "prompt_eval_count": 80,
        "eval_count": 30,
    }
    mock_response.raise_for_status.return_value = None

    with patch("httpx.post", return_value=mock_response):
        result = client_module.call_llm("prompt", caller="assessor")

    assert result == "ollama reply"
    rows = db_session.query(LlmCall).all()
    assert len(rows) == 1
    assert rows[0].provider == "ollama"
    assert rows[0].input_tokens == 80
    assert rows[0].output_tokens == 30
    assert rows[0].estimated is False


def test_call_llm_opencode_uses_exact_usage_when_available(db_session, monkeypatch):
    import app.analyser.client as client_module
    from app.config import settings
    from app.models.llm_call import LlmCall

    monkeypatch.setattr(settings, "llm_provider", "opencode")
    monkeypatch.setattr(settings, "opencode_model", "qwen3.6-plus")

    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock(delta=MagicMock(content="hi"))]
    mock_chunk.usage = MagicMock(prompt_tokens=50, completion_tokens=20)

    mock_stream = MagicMock()
    mock_stream.__enter__.return_value = [mock_chunk]
    mock_stream.__exit__.return_value = False

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_stream
    client_module._opencode_client = mock_client

    result = client_module.call_llm("prompt", caller="synthesizer")

    assert result == "hi"
    rows = db_session.query(LlmCall).all()
    assert len(rows) == 1
    assert rows[0].input_tokens == 50
    assert rows[0].output_tokens == 20
    assert rows[0].estimated is False


def test_call_llm_opencode_estimates_tokens_when_usage_missing(db_session, monkeypatch):
    import app.analyser.client as client_module
    from app.config import settings
    from app.models.llm_call import LlmCall

    monkeypatch.setattr(settings, "llm_provider", "opencode")
    monkeypatch.setattr(settings, "opencode_model", "qwen3.6-plus")

    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock(delta=MagicMock(content="hi"))]
    mock_chunk.usage = None

    mock_stream = MagicMock()
    mock_stream.__enter__.return_value = [mock_chunk]
    mock_stream.__exit__.return_value = False

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_stream
    client_module._opencode_client = mock_client

    result = client_module.call_llm("prompt", caller="synthesizer")

    assert result == "hi"
    rows = db_session.query(LlmCall).all()
    assert len(rows) == 1
    assert rows[0].estimated is True
    assert rows[0].input_tokens > 0
    assert rows[0].output_tokens > 0
