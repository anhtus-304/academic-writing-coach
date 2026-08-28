"use client";

import { useEffect } from "react";
import Placeholder from "@tiptap/extension-placeholder";
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
};

export function TiptapEditor({
  value = "",
  onChange,
  placeholder = "Bắt đầu viết nội dung...",
  className,
  editable = true,
  onAskAI,
}: TiptapEditorProps) {
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

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      {editor ? (
        <BubbleMenu
          editor={editor}
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
              const selectedText = editor.state.doc.textBetween(
                editor.state.selection.from,
                editor.state.selection.to,
                " "
              ).trim();

              if (selectedText) {
                onAskAI?.(selectedText);
              }
            }}
          />
        </BubbleMenu>
      ) : null}
      <EditorToolbar editor={editor} />
      <EditorContent editor={editor} className="prose prose-neutral max-w-none text-sm" />
    </div>
  );
}
