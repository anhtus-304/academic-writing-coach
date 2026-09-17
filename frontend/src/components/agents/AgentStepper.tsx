"use client";

import { Check, CircleAlert, Loader2, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

type StepStatus = "pending" | "running" | "success" | "error";
export type AgentStep = { label: string; status: StepStatus };

type AgentStepperProps = { steps: AgentStep[]; className?: string };

export function AgentStepper({ steps, className }: AgentStepperProps) {
  return (
    <nav
      aria-label="Tiến trình Agent"
      className={cn(
        "w-full overflow-x-auto scrollbar-none rounded-xl border border-gray-200/90 bg-white/95 px-3.5 py-1.5 shadow-2xs backdrop-blur-xs",
        className
      )}
    >
      <div className="flex items-center justify-between min-w-max gap-1 sm:gap-2">
        {steps.map((step, index) => {
          const isSuccess = step.status === "success";
          const isRunning = step.status === "running";
          const isError = step.status === "error";
          const isPending = step.status === "pending";

          return (
            <div key={step.label} className="flex items-center gap-1 sm:gap-1.5 shrink-0">
              <div
                className={cn(
                  "flex items-center gap-1.5 rounded-lg px-2 py-1 transition-all duration-200",
                  isRunning && "bg-purple-50 ring-1 ring-purple-300 shadow-2xs",
                  isSuccess && "bg-emerald-50/60 text-emerald-950",
                  isPending && "opacity-75 hover:opacity-100"
                )}
              >
                <span
                  className={cn(
                    "flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold transition-all",
                    isSuccess && "bg-emerald-600 text-white shadow-2xs",
                    isRunning && "bg-purple-600 text-white shadow-2xs animate-pulse",
                    isError && "bg-red-600 text-white",
                    isPending && "bg-gray-100 text-gray-500 font-medium"
                  )}
                >
                  {isSuccess ? (
                    <Check className="h-3 w-3 stroke-[2.5]" />
                  ) : isRunning ? (
                    <Loader2 className="h-3 w-3 animate-spin stroke-[2.5]" />
                  ) : isError ? (
                    <CircleAlert className="h-3 w-3" />
                  ) : (
                    index + 1
                  )}
                </span>
                <span
                  className={cn(
                    "text-[11.5px] whitespace-nowrap transition-colors",
                    isRunning && "font-bold text-purple-900",
                    isSuccess && "font-semibold text-emerald-900",
                    isError && "font-medium text-red-700",
                    isPending && "text-gray-500 font-normal"
                  )}
                >
                  {step.label}
                </span>
              </div>

              {index < steps.length - 1 && (
                <ChevronRight className="h-3.5 w-3.5 text-gray-300 shrink-0 mx-0.5" />
              )}
            </div>
          );
        })}
      </div>
    </nav>
  );
}

export default AgentStepper;
