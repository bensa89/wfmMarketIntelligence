from typing import TypedDict


class CapabilityMeta(TypedDict):
    key: str
    label: str
    visibility_to_user: bool
    strategic_weight: int  # 1-10
    default_evolution_band: str
    description: str


CAPABILITIES: dict[str, CapabilityMeta] = {
    "demand_forecasting": {
        "key": "demand_forecasting",
        "label": "Demand Forecasting",
        "visibility_to_user": True,
        "strategic_weight": 9,
        "default_evolution_band": "product",
        "description": "Predicting staffing demand based on historical data and external signals",
    },
    "shift_scheduling": {
        "key": "shift_scheduling",
        "label": "Shift Scheduling",
        "visibility_to_user": True,
        "strategic_weight": 10,
        "default_evolution_band": "product",
        "description": "Creating and optimizing shift plans for frontline workers",
    },
    "intraday_management": {
        "key": "intraday_management",
        "label": "Intraday Management",
        "visibility_to_user": True,
        "strategic_weight": 8,
        "default_evolution_band": "product",
        "description": "Real-time adjustment of staffing to match live demand",
    },
    "time_attendance": {
        "key": "time_attendance",
        "label": "Time & Attendance",
        "visibility_to_user": True,
        "strategic_weight": 7,
        "default_evolution_band": "product",
        "description": "Tracking worked hours, absences and compliance",
    },
    "compliance_rules": {
        "key": "compliance_rules",
        "label": "Compliance & Labor Rules",
        "visibility_to_user": True,
        "strategic_weight": 8,
        "default_evolution_band": "product",
        "description": "Enforcing labor law, union rules and company policies in scheduling",
    },
    "employee_self_service": {
        "key": "employee_self_service",
        "label": "Employee Self-Service",
        "visibility_to_user": True,
        "strategic_weight": 6,
        "default_evolution_band": "product",
        "description": "Employee-facing tools for availability, shift swaps and requests",
    },
    "manager_experience": {
        "key": "manager_experience",
        "label": "Manager Experience",
        "visibility_to_user": True,
        "strategic_weight": 7,
        "default_evolution_band": "product",
        "description": "Tooling and UX specifically designed for frontline managers",
    },
    "mobile_experience": {
        "key": "mobile_experience",
        "label": "Mobile Experience",
        "visibility_to_user": True,
        "strategic_weight": 6,
        "default_evolution_band": "product",
        "description": "Mobile apps and responsiveness for deskless worker access",
    },
    "analytics_insights": {
        "key": "analytics_insights",
        "label": "Analytics & Insights",
        "visibility_to_user": True,
        "strategic_weight": 8,
        "default_evolution_band": "product",
        "description": "Reporting dashboards and workforce analytics capabilities",
    },
    "ai_copilot": {
        "key": "ai_copilot",
        "label": "AI Copilot",
        "visibility_to_user": True,
        "strategic_weight": 9,
        "default_evolution_band": "genesis",
        "description": "AI-assisted scheduling, recommendations and conversational interfaces",
    },
    "workflow_automation": {
        "key": "workflow_automation",
        "label": "Workflow Automation",
        "visibility_to_user": True,
        "strategic_weight": 7,
        "default_evolution_band": "product",
        "description": "Automating approval flows, notifications and operational processes",
    },
    "integration_hub": {
        "key": "integration_hub",
        "label": "Integration Hub",
        "visibility_to_user": True,
        "strategic_weight": 7,
        "default_evolution_band": "product",
        "description": "Pre-built connectors to HCM, ERP, and payroll systems",
    },
    "platform_ecosystem": {
        "key": "platform_ecosystem",
        "label": "Platform & Ecosystem",
        "visibility_to_user": True,
        "strategic_weight": 8,
        "default_evolution_band": "product",
        "description": "Partner ecosystem, marketplace, and platform extensibility",
    },
    "vertical_solutions": {
        "key": "vertical_solutions",
        "label": "Vertical Solutions",
        "visibility_to_user": True,
        "strategic_weight": 7,
        "default_evolution_band": "product",
        "description": "Industry-specific WFM modules for retail, healthcare, logistics, etc.",
    },
    "data_foundation": {
        "key": "data_foundation",
        "label": "Data Foundation",
        "visibility_to_user": False,
        "strategic_weight": 6,
        "default_evolution_band": "product",
        "description": "Underlying data model, multi-tenant architecture and data quality",
    },
    "optimization_engine": {
        "key": "optimization_engine",
        "label": "Optimization Engine",
        "visibility_to_user": True,
        "strategic_weight": 9,
        "default_evolution_band": "product",
        "description": "Mathematical optimization for schedule quality, cost and coverage",
    },
}

CAPABILITY_KEYS = list(CAPABILITIES.keys())
