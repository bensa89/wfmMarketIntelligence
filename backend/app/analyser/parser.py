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
    event_date: Optional[datetime] = None
    event_location: Optional[str] = None


_DATE_FORMATS = [
    ("%Y-%m-%dT%H:%M:%SZ", 20),
    ("%Y-%m-%dT%H:%M:%S", 19),
    ("%Y-%m-%d", 10),
]

_UNABLE_TO_ANALYZE_PATTERNS = [
    "unable to analyze",
    "no content provided",
    "cannot analyze",
    "not enough content",
    "insufficient content",
    "no meaningful content",
    "content is empty",
    "no content to analyze",
]


def _is_unable_to_analyze(raw: str) -> bool:
    lower = raw.lower()
    return any(pattern in lower for pattern in _UNABLE_TO_ANALYZE_PATTERNS)


def parse_llm_response(raw: str) -> Optional[SignalData]:
    if _is_unable_to_analyze(raw):
        return None

    try:
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if json_match:
            raw = json_match.group(1)

        json_match2 = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match2:
            raw = json_match2.group(0)

        data = json.loads(raw)

        title = str(data.get("title", "Untitled"))[:500]
        if any(p in title.lower() for p in _UNABLE_TO_ANALYZE_PATTERNS):
            return None

        signal_type_str = data.get("signal_type", "other")
        try:
            signal_type = SignalType(signal_type_str)
        except ValueError:
            signal_type = SignalType.other

        def _parse_date(key: str) -> Optional[datetime]:
            date_str = data.get(key)
            if not date_str or not isinstance(date_str, str):
                return None
            for fmt, length in _DATE_FORMATS:
                try:
                    return datetime.strptime(date_str[:length], fmt)
                except ValueError:
                    continue
            return None

        event_location = data.get("event_location")
        if event_location and not isinstance(event_location, str):
            event_location = None

        return SignalData(
            title=title,
            signal_type=signal_type,
            topic=data.get("topic"),
            summary=data.get("summary"),
            why_it_matters=data.get("why_it_matters"),
            relevance_score=float(data.get("relevance_score", 0.5)),
            confidence_score=float(data.get("confidence_score", 0.5)),
            published_at=_parse_date("published_at"),
            event_date=_parse_date("event_date"),
            event_location=event_location,
        )
    except Exception:
        return None
