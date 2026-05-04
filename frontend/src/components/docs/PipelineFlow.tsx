export interface PipelineStep {
  id: string;
  label: string;
  type: 'rule' | 'ai';
  description: string;
}

interface Props {
  steps: PipelineStep[];
  activeStep: string | null;
  onStepClick: (id: string) => void;
}

export function PipelineFlow({ steps, activeStep, onStepClick }: Props) {
  return (
    <div className="sticky top-0 z-10 bg-[#0f172a] border-b border-white/5 py-4 mb-6">
      <div className="flex items-center gap-1 overflow-x-auto pb-1 px-1">
        {steps.map((step, i) => {
          const isActive = step.id === activeStep;
          const isAI = step.type === 'ai';
          return (
            <div key={step.id} className="flex items-center gap-1 flex-shrink-0">
              <button
                onClick={() => {
                  onStepClick(step.id);
                  document.getElementById(step.id)?.scrollIntoView({ behavior: 'smooth' });
                }}
                className={`flex flex-col items-start px-3 py-2 rounded-lg border text-left transition-all ${
                  isActive
                    ? 'border-blue-500 bg-blue-900/30 text-slate-100'
                    : 'border-white/10 bg-white/3 text-slate-400 hover:border-white/20 hover:text-slate-300'
                }`}
              >
                <div className="flex items-center gap-1.5 mb-0.5">
                  <span className="text-[12px] font-semibold">{step.label}</span>
                  <span
                    className={`text-[9px] font-bold px-1 py-0.5 rounded ${
                      isAI
                        ? 'bg-purple-900/50 text-purple-400'
                        : 'bg-blue-900/50 text-blue-400'
                    }`}
                  >
                    {isAI ? '🤖 KI' : '🔢'}
                  </span>
                </div>
                <span className="text-[10px] text-slate-500 max-w-[120px] truncate">
                  {step.description}
                </span>
              </button>
              {i < steps.length - 1 && (
                <span className="text-slate-600 text-xs px-0.5">→</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
