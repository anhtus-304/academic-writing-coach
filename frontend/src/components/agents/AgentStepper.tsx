"use client";

import { Check, CircleAlert, Loader2 } from "lucide-react";

type StepStatus = "pending" | "running" | "success" | "error";
export type AgentStep = { label: string; status: StepStatus };

type AgentStepperProps = { steps: AgentStep[] };

export function AgentStepper({ steps }: AgentStepperProps) {
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-gray-200 bg-white p-3">
      {steps.map((step, index) => (
        <div key={step.label} className="flex items-center gap-2 text-[11px]">
          <span className={`flex h-6 w-6 items-center justify-center rounded-full ${
            step.status === "success" ? "bg-emerald-100 text-emerald-700" :
            step.status === "running" ? "bg-purple-100 text-purple-700" :
            step.status === "error" ? "bg-red-100 text-red-700" : "bg-gray-100 text-gray-500"
          }`}>
            {step.status === "success" ? <Check className="h-3.5 w-3.5" /> :
              step.status === "running" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> :
              step.status === "error" ? <CircleAlert className="h-3.5 w-3.5" /> : index + 1}
          </span>
          <span className={step.status === "pending" ? "text-gray-500" : "font-semibold text-gray-800"}>{step.label}</span>
          {index < steps.length - 1 ? <span className="mx-1 text-gray-300">→</span> : null}
        </div>
      ))}
    </div>
  );
}
