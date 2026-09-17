"use client";

import { useEffect, useRef, useState } from "react";
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

// Mở rộng Table để hỗ trợ class và inline style cho Mục Lục & Bảng học thuật
const CustomTable = Table.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      class: {
        default: null,
        parseHTML: (element) => element.getAttribute("class"),
        renderHTML: (attributes) => {
          if (!attributes.class) return {};
          return { class: attributes.class };
        },
      },
      style: {
        default: null,
        parseHTML: (element) => element.getAttribute("style"),
        renderHTML: (attributes) => {
          if (!attributes.style) return {};
          return { style: attributes.style };
        },
      },
    };
  },
}).configure({
  resizable: true,
});

const CustomTableCell = TableCell.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      style: {
        default: null,
        parseHTML: (element) => element.getAttribute("style"),
        renderHTML: (attributes) => {
          if (!attributes.style) return {};
          return { style: attributes.style };
        },
      },
    };
  },
});

const CustomTableHeader = TableHeader.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      style: {
        default: null,
        parseHTML: (element) => element.getAttribute("style"),
        renderHTML: (attributes) => {
          if (!attributes.style) return {};
          return { style: attributes.style };
        },
      },
    };
  },
});

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
  isA4Mode?: boolean;
  onToggleA4Mode?: () => void;
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
  isA4Mode,
  onToggleA4Mode,
}: TiptapEditorProps) {
  const highlightedKey = useRef("");
  const [internalA4Mode, setInternalA4Mode] = useState(true);
  const currentA4Mode = isA4Mode !== undefined ? isA4Mode : internalA4Mode;
  const toggleA4Mode = onToggleA4Mode || (() => setInternalA4Mode(!internalA4Mode));

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
      CustomTable,
      TableRow,
      CustomTableHeader,
      CustomTableCell,
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
          "tiptap-editor min-h-[350px] w-full bg-transparent text-sm leading-relaxed text-gray-900 focus:outline-none",
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

      <EditorToolbar
        editor={editor}
        onInsertToc={onInsertToc}
        isA4Mode={currentA4Mode}
        onToggleA4Mode={toggleA4Mode}
      />
      <div
        className={cn(
          "w-full transition-colors duration-200",
          currentA4Mode
            ? "bg-slate-100/80 py-8 px-4 flex flex-col items-center min-h-[750px]"
            : "bg-white p-4 sm:p-6"
        )}
      >
        {currentA4Mode && (
          <div className="mb-3 text-[11px] font-medium text-gray-500 flex items-center gap-2 select-none">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Khổ giấy A4 (210 × 297 mm) — Canh lề chuẩn NĐ 30/2020/NĐ-CP (Trái 30mm, Phải 20mm, Trên/Dưới 25mm)</span>
          </div>
        )}
        <div
          className={cn(
            "w-full transition-all duration-200",
            currentA4Mode
              ? "max-w-[210mm] min-h-[297mm] bg-white shadow-xl border border-gray-300/80 rounded-[2px] p-[25mm_20mm_25mm_30mm]"
              : "w-full"
          )}
        >
          <EditorContent editor={editor} className="prose prose-neutral max-w-none" />
        </div>
      </div>
    </div>
  );
}

export default TiptapEditor;
