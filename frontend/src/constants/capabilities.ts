// frontend/src/constants/capabilities.ts
export interface CapabilityMeta {
  key: string;
  label: string;
  visibilityToUser: boolean;
  strategicWeight: number;
  description: string;
  icon: string;
}

export const CAPABILITIES: Record<string, CapabilityMeta> = {
  demand_forecasting: { key: 'demand_forecasting', label: 'Demand Forecasting', visibilityToUser: true, strategicWeight: 9, description: 'Predicting staffing demand based on historical data', icon: 'TrendingUp' },
  shift_scheduling: { key: 'shift_scheduling', label: 'Shift Scheduling', visibilityToUser: true, strategicWeight: 10, description: 'Creating and optimizing shift plans', icon: 'Calendar' },
  time_attendance: { key: 'time_attendance', label: 'Time & Attendance', visibilityToUser: true, strategicWeight: 7, description: 'Tracking worked hours, absences and compliance', icon: 'CheckCircle2' },
  compliance_rules: { key: 'compliance_rules', label: 'Compliance & Labor Rules', visibilityToUser: true, strategicWeight: 8, description: 'Enforcing labor law and scheduling policies', icon: 'ShieldCheck' },
  employee_self_service: { key: 'employee_self_service', label: 'Employee Self-Service', visibilityToUser: true, strategicWeight: 6, description: 'Employee tools for availability and shift swaps', icon: 'Users' },
  mobile_experience: { key: 'mobile_experience', label: 'Mobile Experience', visibilityToUser: true, strategicWeight: 6, description: 'Mobile apps for deskless workers', icon: 'Smartphone' },
  analytics_insights: { key: 'analytics_insights', label: 'Analytics & Insights', visibilityToUser: true, strategicWeight: 8, description: 'Reporting dashboards and workforce analytics', icon: 'BarChart3' },
  ai_copilot: { key: 'ai_copilot', label: 'AI Copilot', visibilityToUser: true, strategicWeight: 9, description: 'AI-assisted scheduling and conversational interfaces', icon: 'Sparkles' },
  workflow_automation: { key: 'workflow_automation', label: 'Workflow Automation', visibilityToUser: true, strategicWeight: 7, description: 'Automating approval flows and operational processes', icon: 'Zap' },
  integration_hub: { key: 'integration_hub', label: 'Integration Hub', visibilityToUser: true, strategicWeight: 7, description: 'Pre-built connectors to HCM, ERP, and payroll', icon: 'Plug' },
  platform_ecosystem: { key: 'platform_ecosystem', label: 'Platform & Ecosystem', visibilityToUser: true, strategicWeight: 8, description: 'Partner ecosystem and platform extensibility', icon: 'Layers' },
  vertical_solutions: { key: 'vertical_solutions', label: 'Vertical Solutions', visibilityToUser: true, strategicWeight: 7, description: 'Industry-specific WFM modules', icon: 'Building2' },
  data_foundation: { key: 'data_foundation', label: 'Data Foundation', visibilityToUser: false, strategicWeight: 6, description: 'Underlying data model and multi-tenant architecture', icon: 'Database' },
  optimization_engine: { key: 'optimization_engine', label: 'Optimization Engine', visibilityToUser: true, strategicWeight: 9, description: 'Mathematical optimization for schedule quality and cost', icon: 'Target' },
};

export function getCapabilityLabel(key: string | null | undefined): string {
  if (!key) return 'Unknown';
  return CAPABILITIES[key]?.label ?? key;
}
