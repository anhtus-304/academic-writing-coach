"use client";

import { useEffect, useRef } from "react";
import Placeholder from "@tiptap/extension-placeholder";
import Highlight from "@tiptap/extension-highlight";
import StarterKit from "@tiptap/starter-kit";
import { EditorContent, useEditor } from "@tiptap/react";
import { BubbleMenu } from "@tiptap/react/menus";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import "@/styles/editor.css";
import { EditorToolbar } from "./EditorToolbar";
import { AIBubbleMenu } from "./AIBubbleMenu";

type TiptapEditorProps = {
  value?: string;
  onChange?: (content: string) => void;
  placeholder?: string;
  className?: string;
  editable?: boolean;
  onAskAI?: (selectedText: string) => void;
  insertReferenceHtml?: string | null;
  onReferenceInserted?: () => void;
  highlightedSentences?: string[];
  citationSuggestion?: { originalText: string; suggestedText: string } | null;
  onCitationSuggestionApplied?: () => void;
};

export function TiptapEditor({
  value = "",
  onChange,
  placeholder = "Bắt đầu viết nội dung...",
  className,
  editable = true,
  onAskAI,
  insertReferenceHtml,
  onReferenceInserted,
  highlightedSentences = [],
  citationSuggestion,
  onCitationSuggestionApplied,
}: TiptapEditorProps) {
  const highlightedKey = useRef("");
  const editor = useEditor({
    immediatelyRender: false,
    editable,
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3],
        },
      }),
      Placeholder.configure({
        placeholder,
      }),
      Highlight.configure({ multicolor: true }),
    ],
    content: value || "<p></p>",
    editorProps: {
      attributes: {
        class: cn(
          "tiptap-editor min-h-[220px] w-full bg-background px-4 py-3 text-sm leading-6 text-foreground focus:outline-none",
          className
        ),
      },
    },
    onUpdate: ({ editor }) => {
      onChange?.(editor.getHTML());
    },
  });

  useEffect(() => {
    if (!editor) {
      return;
    }

    const currentHtml = editor.getHTML();
    if (value !== currentHtml) {
      editor.commands.setContent(value || "<p></p>", { emitUpdate: false });
    }
  }, [editor, value]);

  useEffect(() => {
    if (!editor || !insertReferenceHtml) {
      return;
    }

    editor.chain().focus().insertContent(insertReferenceHtml).run();
    onReferenceInserted?.();
  }, [editor, insertReferenceHtml, onReferenceInserted]);

  useEffect(() => {
    if (!editor || highlightedSentences.length === 0) {
      return;
    }

    const sentences = highlightedSentences.filter(Boolean);
    const key = sentences.join("\u0000");
    if (key === highlightedKey.current) {
      return;
    }
    highlightedKey.current = key;
    editor.state.doc.descendants((node, position) => {
      if (!node.isText || !node.text) return;
      const sentence = sentences.find((item) => node.text?.includes(item));
      if (!sentence) return;
      const start = node.text.indexOf(sentence);
      editor.chain().setTextSelection({ from: position + start, to: position + start + sentence.length }).setHighlight({ color: "#fef08a" }).run();
    });
  }, [editor, highlightedSentences]);

  useEffect(() => {
    if (!editor || !citationSuggestion?.originalText || !citationSuggestion.suggestedText) {
      return;
    }

    let applied = false;
    editor.state.doc.descendants((node, position) => {
      if (applied || !node.isText || !node.text) return;
      const start = node.text.indexOf(citationSuggestion.originalText);
      if (start < 0) return;
      editor.commands.insertContentAt(
        { from: position + start, to: position + start + citationSuggestion.originalText.length },
        citationSuggestion.suggestedText,
      );
      applied = true;
    });
    onCitationSuggestionApplied?.();
  }, [editor, citationSuggestion, onCitationSuggestionApplied]);

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      {editor ? (
        <BubbleMenu
          editor={editor}
          shouldShow={({ editor }) => editor.state.selection.from !== editor.state.selection.to}
          className="flex items-center gap-1 rounded-lg border border-border bg-background p-1 shadow-lg"
        >
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className={cn("h-8 px-2", editor.isActive("bold") && "bg-primary text-primary-foreground")}
            onClick={() => editor.chain().focus().toggleBold().run()}
            aria-label="Bold"
          >
            Bold
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className={cn("h-8 px-2", editor.isActive("italic") && "bg-primary text-primary-foreground")}
            onClick={() => editor.chain().focus().toggleItalic().run()}
            aria-label="Italic"
          >
            Italic
          </Button>
          <AIBubbleMenu
            onAskAI={() => {
              const text = editor.state.doc.textBetween(
                editor.state.selection.from,
                editor.state.selection.to,
              );
              onAskAI?.(text.trim());
            }}
          />
        </BubbleMenu>
      ) : null}
      <EditorToolbar editor={editor} />
      <EditorContent editor={editor} className="prose prose-neutral max-w-none text-sm" />
    </div>
  );
}
