"use client";

import { type Editor } from "@tiptap/react";
import {
  Bold,
  Heading1,
  Heading2,
  Heading3,
  Italic,
  List,
  ListOrdered,
  Redo2,
  Undo2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type EditorToolbarProps = {
  editor: Editor | null;
};

export function EditorToolbar({ editor }: EditorToolbarProps) {
  if (!editor) {
    return (
      <div className="flex flex-wrap items-center gap-2 border-b border-border bg-muted/30 px-3 py-2">
        <div className="h-8 w-8 animate-pulse rounded-md bg-muted" />
        <div className="h-8 w-8 animate-pulse rounded-md bg-muted" />
        <div className="h-8 w-8 animate-pulse rounded-md bg-muted" />
      </div>
    );
  }

  const buttonClass = (active: boolean) =>
    cn(
      "h-8 gap-1.5 px-2.5",
      active && "bg-primary text-primary-foreground hover:bg-primary/90"
    );

  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-border bg-muted/30 px-3 py-2">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className={buttonClass(editor.isActive("bold"))}
        onClick={() => editor.chain().focus().toggleBold().run()}
        aria-label="Bold"
        title="Bold"
      >
        <Bold className="h-4 w-4" />
      </Button>

      <Button
        type="button"
        variant="ghost"
        size="sm"
        className={buttonClass(editor.isActive("italic"))}
        onClick={() => editor.chain().focus().toggleItalic().run()}
        aria-label="Italic"
        title="Italic"
      >
        <Italic className="h-4 w-4" />
      </Button>

      <Button
        type="button"
        variant="ghost"
        size="sm"
        className={buttonClass(editor.isActive("heading", { level: 1 }))}
        onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
        aria-label="Heading 1"
        title="Heading 1"
      >
        <Heading1 className="h-4 w-4" />
      </Button>

      <Button
        type="button"
        variant="ghost"
        size="sm"
        className={buttonClass(editor.isActive("heading", { level: 2 }))}
        onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
        aria-label="Heading 2"
        title="Heading 2"
      >
        <Heading2 className="h-4 w-4" />
      </Button>

      <Button
        type="button"
        variant="ghost"
        size="sm"
        className={buttonClass(editor.isActive("heading", { level: 3 }))}
        onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
        aria-label="Heading 3"
        title="Heading 3"
      >
        <Heading3 className="h-4 w-4" />
      </Button>

      <Button
        type="button"
        variant="ghost"
        size="sm"
        className={buttonClass(editor.isActive("bulletList"))}
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        aria-label="Bullet list"
        title="Bullet list"
      >
        <List className="h-4 w-4" />
      </Button>

      <Button
        type="button"
        variant="ghost"
        size="sm"
        className={buttonClass(editor.isActive("orderedList"))}
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
        aria-label="Ordered list"
        title="Ordered list"
      >
        <ListOrdered className="h-4 w-4" />
      </Button>

      <div className="mx-1 h-5 w-px bg-border" />

      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().undo().run()}
        disabled={!editor.can().undo()}
        aria-label="Undo"
        title="Undo"
      >
        <Undo2 className="h-4 w-4" />
      </Button>

      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().redo().run()}
        disabled={!editor.can().redo()}
        aria-label="Redo"
        title="Redo"
      >
        <Redo2 className="h-4 w-4" />
      </Button>
    </div>
  );
}
