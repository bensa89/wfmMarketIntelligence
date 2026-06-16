from typing import List, Dict, Any


def build_synthesis_prompt(signals: List[Dict[str, Any]]) -> str:
    signals_text = "\n\n".join(
        f"[Signal {i + 1}]\nTitle: {s.get('title', '')}\nTopic: {s.get('topic', '')}\n"
        f"Summary: {s.get('summary', '')}\nWhy it matters: {s.get('why_it_matters', '')}"
        for i, s in enumerate(signals)
    )

    return f"""You are a brand analyst. Based on the following signals extracted from a company's own public website and blog, synthesize a structured overview of how the company presents itself externally.

SIGNALS FROM OWN COMPANY CONTENT ({len(signals)} total):
{signals_text}

Based on these signals, produce a JSON object that captures the company's external communication profile:

{{
  "summary": "3-5 sentence synthesis of how the company presents itself externally, its tone, and key themes",
  "key_messages": ["list of 3-6 core messages the company consistently communicates"],
  "observed_capabilities": ["list of capabilities the company actively highlights publicly"],
  "observed_differentiators": ["list of differentiators the company claims publicly"],
  "observed_target_markets": ["list of target markets or industries mentioned in public content"],
  "tone_and_positioning": "2-3 sentences describing communication style, tone, and market positioning approach"
}}

No markdown fences, no extra text. Only the JSON object."""
