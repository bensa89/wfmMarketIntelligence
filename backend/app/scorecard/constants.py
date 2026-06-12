import math

ROUTING_VERSION = "v1"
SCORECARD_VERSION = "sc_v2"

MOMENTUM_RISING_THRESHOLD = 5.0
MOMENTUM_DECLINING_THRESHOLD = -5.0
SIGNAL_CLASS_COUNT = 7     # K for Shannon entropy normalisation — update when SignalClass enum changes

# How many days back the "prior" reference point sits for momentum comparison
MOMENTUM_WINDOW_DAYS = 60

# Exponential decay half-life per period type (controls recency emphasis)
DECAY_LAMBDA: dict[str, float] = {
    "30d":  math.log(2) / 30,   # strong recency emphasis
    "90d":  math.log(2) / 90,
    "180d": math.log(2) / 180,  # near-flat — historical view
}

DIMENSION_WEIGHTS: dict[str, float] = {
    "capability_strength": 0.30,
    "market_impact":       0.25,
    "activity":            0.20,
    "customer_proof":      0.15,
    "momentum":            0.10,
}

VALID_PERIOD_TYPES = ["30d", "90d", "180d"]

# Capability strategic_weight threshold for risk_flags
RISK_FLAG_STRATEGIC_WEIGHT_THRESHOLD = 8
