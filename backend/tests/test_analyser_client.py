from unittest.mock import patch, MagicMock
import importlib


def test_anthropic_client_reused_across_calls():
    """Same client instance should be returned on repeated calls."""
    import app.analyser.client as client_module
    # Reset singleton
    client_module._anthropic_client = None

    mock_client = MagicMock()
    with patch("anthropic.Anthropic", return_value=mock_client) as mock_cls:
        from app.analyser.client import _get_anthropic_client
        c1 = _get_anthropic_client()
        c2 = _get_anthropic_client()

    assert c1 is c2
    assert mock_cls.call_count == 1


def test_opencode_client_reused_across_calls():
    import app.analyser.client as client_module
    client_module._opencode_client = None

    mock_client = MagicMock()
    with patch("openai.OpenAI", return_value=mock_client) as mock_cls:
        from app.analyser.client import _get_opencode_client
        c1 = _get_opencode_client()
        c2 = _get_opencode_client()

    assert c1 is c2
    assert mock_cls.call_count == 1
