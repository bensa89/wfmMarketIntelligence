ROUTING_VERSION = "v1"
SCORECARD_VERSION = "sc_v1"

RECENCY_DECAY_MAX = 0.30   # recency_weight floor = 0.70
MOMENTUM_RISING_THRESHOLD = 5.0
MOMENTUM_DECLINING_THRESHOLD = -5.0
SIGNAL_CLASS_COUNT = 7     # K for Shannon entropy normalisation — update when SignalClass enum changes

DIMENSION_WEIGHTS: dict[str, float] = {
    "capability_strength": 0.30,
    "market_impact":       0.25,
    "activity":            0.20,
    "customer_proof":      0.15,
    "momentum":            0.10,
}

PERIOD_DAYS: dict[str, int] = {
    "30d":  30,
    "90d":  90,
    "180d": 180,
}

VALID_PERIOD_TYPES = list(PERIOD_DAYS.keys())

# Capability strategic_weight threshold for risk_flags
RISK_FLAG_STRATEGIC_WEIGHT_THRESHOLD = 8
