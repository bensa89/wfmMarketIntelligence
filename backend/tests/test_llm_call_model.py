from app.models.llm_call import LlmCall
from app.models.llm_model_price import LlmModelPrice


def test_llm_call_round_trip(db_session):
    call = LlmCall(
        caller="analyser",
        provider="claude",
        model="claude-haiku-4-5-20251001",
        input_tokens=120,
        output_tokens=45,
        estimated=False,
        duration_ms=850,
    )
    db_session.add(call)
    db_session.commit()

    fetched = db_session.query(LlmCall).first()
    assert fetched.caller == "analyser"
    assert fetched.input_tokens == 120
    assert fetched.estimated is False
    assert fetched.created_at is not None


def test_llm_model_price_round_trip(db_session):
    price = LlmModelPrice(model="claude-haiku-4-5-20251001", input_price_per_1m=1.0, output_price_per_1m=5.0)
    db_session.add(price)
    db_session.commit()

    fetched = db_session.query(LlmModelPrice).filter(LlmModelPrice.model == "claude-haiku-4-5-20251001").first()
    assert fetched.output_price_per_1m == 5.0
