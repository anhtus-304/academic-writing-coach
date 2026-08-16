"use client";

import { useMemo, useState } from "react";

import { AIResponsePanel } from "@/components/editor/AIResponsePanel";
import { TiptapEditor } from "@/components/editor/TiptapEditor";
import { OutlineEditor, type OutlineNode } from "@/components/outline/OutlineEditor";
import { OutlinePreview } from "@/components/outline/OutlinePreview";
import { useAgent } from "@/hooks/useAgent";
import { isGoogleAuthConfigured, signInWithGoogle } from "@/lib/auth";
import { Button } from "@/components/ui/button";

const initialOutline: OutlineNode[] = [];

const initialContent = `
  <h1>Thesis introduction</h1>
  <p>Academic writing requires a clear structure with well-defined research objectives and a consistent literature review.</p>
  <h2>Key idea</h2>
  <ul>
    <li>Identify the problem.</li>
    <li>Review relevant literature.</li>
    <li>Present the methodology.</li>
  </ul>
`;

export default function Home() {
  const [editorValue, setEditorValue] = useState(initialContent);
  const [generatedOutline, setGeneratedOutline] = useState<OutlineNode[]>(initialOutline);
  const [prompt, setPrompt] = useState(
    "Mô tả chủ đề nghiên cứu để tạo dàn ý..."
  );
  const { isLoading, error, result, generateOutline } = useAgent();
  const googleConfigured = useMemo(() => isGoogleAuthConfigured(), []);

  const handleGenerateOutline = async () => {
    const nextOutline = await generateOutline(prompt);
    if (nextOutline) {
      setGeneratedOutline(nextOutline);
    }
  };

  return (
    <main className="min-h-screen bg-background px-4 py-8 text-foreground">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="space-y-2">
            <p className="text-sm font-medium uppercase tracking-[0.12em] text-muted-foreground">
              Academic Writing Coach
            </p>
            <h1 className="text-3xl font-bold tracking-tight">Outline Editor & Draft Writer</h1>
          </div>

          <Button
            type="button"
            variant={googleConfigured ? "default" : "outline"}
            size="sm"
            onClick={() => signInWithGoogle()}
            disabled={!googleConfigured}
          >
            {googleConfigured ? "Continue with Google" : "Google login not configured"}
          </Button>
        </header>

        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <section className="space-y-4">
            <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-lg font-semibold">Draft editor</h2>
                <span className="rounded-full bg-muted px-2 py-1 text-xs text-muted-foreground">
                  Tiptap
                </span>
              </div>
              <TiptapEditor value={editorValue} onChange={setEditorValue} />
            </div>
          </section>

          <section className="space-y-4">
            <AIResponsePanel
              isLoading={isLoading}
              error={error}
              title="Outline Agent"
              description="Describe the topic and the agent will generate a structured outline for your paper."
              prompt={prompt}
              onPromptChange={setPrompt}
              onGenerate={handleGenerateOutline}
              onApply={() => {
                if (result) {
                  setGeneratedOutline(result);
                }
              }}
              result={result}
              defaultActionLabel="Generate outline"
            />
          </section>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <h2 className="mb-3 text-lg font-semibold">AI integration snapshot</h2>
            <p className="text-sm text-muted-foreground">
              The outline agent generates a structured tree, then the UI lets you refine each node,
              collapse branches, and update the final draft structure.
            </p>
          </div>
          <OutlinePreview outline={generatedOutline} />
        </div>

        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <OutlineEditor
            outline={generatedOutline}
            onChange={setGeneratedOutline}
            title="AI-generated outline"
          />
        </div>
      </div>
    </main>
  );
}
