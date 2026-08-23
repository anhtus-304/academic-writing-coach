"use client";

import { Loader2, Sparkles, Wand2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { OutlineNode } from "@/components/outline/OutlineEditor";

type AIResponsePanelProps = {
  isLoading: boolean;
  error: string | null;
  title?: string;
  description?: string;
  prompt: string;
  onPromptChange: (value: string) => void;
  onGenerate: () => void;
  onApply?: () => void;
  result?: OutlineNode[] | null;
  defaultActionLabel?: string;
};

export function AIResponsePanel({
  isLoading,
  error,
  title = "AI assistant",
  description = "Describe your research topic to generate a structured outline.",
  prompt,
  onPromptChange,
  onGenerate,
  onApply,
  result,
  defaultActionLabel = "Generate",
}: AIResponsePanelProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-foreground">{title}</h3>
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        </div>
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Sparkles className="h-4 w-4" />
        </div>
      </div>

      <label className="mb-3 block text-sm font-medium text-foreground">
        Yêu cầu của bạn
      </label>
      <textarea
        value={prompt}
        onChange={(event) => onPromptChange(event.target.value)}
        rows={5}
        className="w-full resize-none rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground outline-none ring-0 transition focus:border-ring"
        placeholder="Ví dụ: Tạo dàn ý cho bài nghiên cứu về ứng dụng AI trong giáo dục..."
      />

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Button type="button" onClick={onGenerate} disabled={isLoading}>
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Generating outline...
            </>
          ) : (
            <>
              <Wand2 className="mr-2 h-4 w-4" />
              {defaultActionLabel}
            </>
          )}
        </Button>

        {onApply && result && result.length > 0 ? (
          <Button type="button" variant="outline" onClick={onApply}>
            Apply outline
          </Button>
        ) : null}
      </div>

      {error ? (
        <div className="mt-4 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      {!error && result && result.length > 0 ? (
        <div className="mt-4 rounded-lg border border-border bg-muted/20 p-3 text-sm text-foreground">
          <div className="mb-2 font-medium">Structured outline preview</div>
          <pre className="overflow-x-auto whitespace-pre-wrap text-xs leading-6 text-muted-foreground">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      ) : null}
    </div>
  );
}
