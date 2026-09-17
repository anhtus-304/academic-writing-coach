"use client";

import { useEffect, useRef } from "react";
import Placeholder from "@tiptap/extension-placeholder";
import Highlight from "@tiptap/extension-highlight";
import StarterKit from "@tiptap/starter-kit";
import { EditorContent, useEditor } from "@tiptap/react";
import { BubbleMenu } from "@tiptap/react/menus";

// Tiptap Extensions bổ sung theo yêu cầu học thuật
import { Table } from "@tiptap/extension-table";
import { TableRow } from "@tiptap/extension-table-row";
import { TableHeader } from "@tiptap/extension-table-header";
import { TableCell } from "@tiptap/extension-table-cell";
import { TextAlign } from "@tiptap/extension-text-align";
import { Underline } from "@tiptap/extension-underline";
import { TextStyle } from "@tiptap/extension-text-style";
import { FontFamily } from "@tiptap/extension-font-family";
import { FontSize } from "./extensions/FontSize";

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
  scrollToHeadingText?: string | null;
  onInsertToc?: () => void;
  highlightedSentences?: string[];
  citationSuggestion?: { originalText: string; suggestedText: string } | null;
  onCitationSuggestionApplied?: () => void;
};

export function TiptapEditor({
  value = "",
  onChange,
  placeholder = "Bắt đầu viết nội dung nghiên cứu...",
  className,
  editable = true,
  onAskAI,
  insertReferenceHtml,
  onReferenceInserted,
  scrollToHeadingText,
  onInsertToc,
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
      Table.configure({
        resizable: true,
      }),
      TableRow,
      TableHeader,
      TableCell,
      TextAlign.configure({
        types: ["heading", "paragraph"],
      }),
      TextStyle,
      FontFamily,
      FontSize,
      Underline,
      Highlight.configure({ multicolor: true }),
    ],
    content: value || "<p></p>",
    editorProps: {
      attributes: {
        class: cn(
          "tiptap-editor min-h-[350px] w-full bg-white px-6 py-6 text-sm leading-relaxed text-gray-900 focus:outline-none",
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

  // Cuộn đến tiêu đề tương ứng khi người dùng click vào một mục trong Dàn ý
  useEffect(() => {
    if (!editor || !scrollToHeadingText) return;

    const dom = editor.view.dom;
    const elements = dom.querySelectorAll("h1, h2, h3, p");
    const normalizedTarget = scrollToHeadingText.toLowerCase().trim();

    for (const el of Array.from(elements)) {
      const text = el.textContent?.toLowerCase().trim() || "";
      if (text.includes(normalizedTarget) || normalizedTarget.includes(text)) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        el.classList.add("bg-purple-100", "transition-colors", "duration-500");
        setTimeout(() => {
          el.classList.remove("bg-purple-100");
        }, 1800);
        break;
      }
    }
  }, [editor, scrollToHeadingText]);

  // FE 2: Tô màu các đoạn văn được Citation Agent cảnh báo "Thiếu nguồn"
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
      editor
        .chain()
        .setTextSelection({ from: position + start, to: position + start + sentence.length })
        .setHighlight({ color: "#fef08a" })
        .run();
    });
  }, [editor, highlightedSentences]);

  // FE 2: Nút "Chấp nhận gợi ý AI" tự động thay thế văn bản trong Tiptap
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
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      {editor ? (
        <BubbleMenu
          editor={editor}
          shouldShow={({ editor }) => editor.state.selection.from !== editor.state.selection.to}
          className="flex items-center gap-1 rounded-lg border border-gray-200 bg-white p-1 shadow-xl z-30"
        >
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className={cn("h-7 px-2 text-xs", editor.isActive("bold") && "bg-purple-100 text-purple-700 font-bold")}
            onClick={() => editor.chain().focus().toggleBold().run()}
            aria-label="Bold"
          >
            Bold
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className={cn("h-7 px-2 text-xs", editor.isActive("italic") && "bg-purple-100 text-purple-700 font-bold")}
            onClick={() => editor.chain().focus().toggleItalic().run()}
            aria-label="Italic"
          >
            Italic
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className={cn("h-7 px-2 text-xs", editor.isActive("underline") && "bg-purple-100 text-purple-700 font-bold")}
            onClick={() => editor.chain().focus().toggleUnderline().run()}
            aria-label="Underline"
          >
            Underline
          </Button>
          <AIBubbleMenu
            onAskAI={() => {
              const text = editor.state.doc.textBetween(
                editor.state.selection.from,
                editor.state.selection.to
              );
              onAskAI?.(text.trim());
            }}
          />
        </BubbleMenu>
      ) : null}

      <EditorToolbar editor={editor} onInsertToc={onInsertToc} />
      <EditorContent editor={editor} className="prose prose-neutral max-w-none" />
    </div>
  );
}

export default TiptapEditor;
