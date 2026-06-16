from dataclasses import dataclass, field


@dataclass
class SectionDef:
    key: str
    title: str
    signal_types: list[str]
    assessment_classes: list[str]
    use_source_type_filter: bool = False
    competitor_only: bool = False


SECTIONS: list[SectionDef] = [
    SectionDef(
        key="market_movements",
        title="Marktbewegungen",
        signal_types=["positioning_change", "target_market_change"],
        assessment_classes=["positioning_move", "market_expansion_move"],
    ),
    SectionDef(
        key="new_trends",
        title="Neue Trends",
        signal_types=["ai_announcement", "other"],
        assessment_classes=["product_capability_move", "weak_signal"],
    ),
    SectionDef(
        key="competitors",
        title="Wettbewerber",
        signal_types=["product_update", "partnership", "hiring_signal"],
        assessment_classes=["product_capability_move", "ecosystem_move", "hiring_signal"],
        use_source_type_filter=True,
        competitor_only=True,
    ),
    SectionDef(
        key="events",
        title="Thought Leadership",
        signal_types=["event_or_thought_leadership"],
        assessment_classes=["thought_leadership_signal"],
    ),
]
