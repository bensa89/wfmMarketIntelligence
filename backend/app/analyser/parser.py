import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from app.models.signal import SignalType


@dataclass
class SignalData:
    title: str
    signal_type: SignalType
    topic: Optional[str]
    summary: Optional[str]
    why_it_matters: Optional[str]
    relevance_score: float
    confidence_score: float
    published_at: Optional[datetime] = None


def parse_llm_response(raw: str) -> SignalData:
    try:
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if json_match:
            raw = json_match.group(1)

        json_match2 = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match2:
            raw = json_match2.group(0)

        data = json.loads(raw)

        signal_type_str = data.get("signal_type", "other")
        try:
            signal_type = SignalType(signal_type_str)
        except ValueError:
            signal_type = SignalType.other

        published_at = None
        pub_str = data.get("published_at")
        if pub_str and isinstance(pub_str, str):
            for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
                try:
                    published_at = datetime.strptime(pub_str[: len(fmt)], fmt)
                    break
                except ValueError:
                    continue

        return SignalData(
            title=str(data.get("title", "Untitled"))[:500],
            signal_type=signal_type,
            topic=data.get("topic"),
            summary=data.get("summary"),
            why_it_matters=data.get("why_it_matters"),
            relevance_score=float(data.get("relevance_score", 0.5)),
            confidence_score=float(data.get("confidence_score", 0.5)),
            published_at=published_at,
        )
    except Exception:
        return SignalData(
            title="Parse error",
            signal_type=SignalType.other,
            topic=None,
            summary=None,
            why_it_matters=None,
            relevance_score=0.1,
            confidence_score=0.1,
            published_at=None,
        )
