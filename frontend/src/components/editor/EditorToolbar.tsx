"use client";

import { useState } from "react";
import { type Editor } from "@tiptap/react";
import {
  Bold,
  Italic,
  Underline as UnderlineIcon,
  Heading1,
  Heading2,
  Heading3,
  List,
  ListOrdered,
  AlignLeft,
  AlignCenter,
  AlignRight,
  AlignJustify,
  Table as TableIcon,
  Plus,
  Trash2,
  Redo2,
  Undo2,
  ChevronDown,
  LayoutTemplate,
  FileText,
  BookOpen,
  Maximize2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type EditorToolbarProps = {
  editor: Editor | null;
  onInsertToc?: () => void;
  isA4Mode?: boolean;
  onToggleA4Mode?: () => void;
};

const FONT_FAMILIES = [
  { label: "Times New Roman (Chuẩn VN)", value: "Times New Roman, serif" },
  { label: "Arial", value: "Arial, sans-serif" },
  { label: "Roboto", value: "Roboto, sans-serif" },
];

const FONT_SIZES = [
  { label: "11pt (Chú thích / Bảng)", value: "11pt" },
  { label: "12pt (Tham khảo)", value: "12pt" },
  { label: "13pt (Chuẩn Luận Văn VN)", value: "13pt" },
  { label: "14pt (Mục Cấp 2)", value: "14pt" },
  { label: "16pt (Chương / H1)", value: "16pt" },
  { label: "18pt (Tên Đề Tài)", value: "18pt" },
  { label: "20pt", value: "20pt" },
];

export function EditorToolbar({
  editor,
  onInsertToc,
  isA4Mode,
  onToggleA4Mode,
}: EditorToolbarProps) {
  const [isTableMenuOpen, setIsTableMenuOpen] = useState(false);

  if (!editor) {
    return (
      <div className="flex flex-wrap items-center gap-1.5 border-b border-border bg-gray-50/50 px-3 py-2">
        <div className="h-7 w-24 animate-pulse rounded bg-gray-200" />
        <div className="h-7 w-16 animate-pulse rounded bg-gray-200" />
        <div className="h-7 w-7 animate-pulse rounded bg-gray-200" />
      </div>
    );
  }

  const isTableActive = editor.isActive("table");

  const buttonClass = (active: boolean) =>
    cn(
      "h-7 w-7 p-0 rounded hover:bg-gray-200 text-gray-700 transition",
      active && "bg-purple-100 text-purple-800 font-bold hover:bg-purple-200"
    );

  const handleFontFamilyChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    if (val) {
      editor.chain().focus().setFontFamily(val).run();
    }
  };

  const handleFontSizeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    if (val) {
      editor.chain().focus().setFontSize(val).run();
    }
  };

  const handleInsertHeader = () => {
    editor
      .chain()
      .focus()
      .insertContent(
        `<div class="academic-header"><span>[TIÊU ĐỀ ĐẦU TRANG: TÊN ĐỀ TÀI / CHƯƠNG]</span><span>HỌC KỲ / NĂM HỌC</span></div><p></p>`
      )
      .run();
  };

  const handleInsertFooter = () => {
    editor
      .chain()
      .focus()
      .insertContent(
        `<p></p><div class="academic-footer"><span>[TIÊU ĐỀ CHÂN TRANG: HỌ TÊN TÁC GIẢ]</span><span>TRANG 1</span></div><p></p>`
      )
      .run();
  };

  return (
    <div className="flex flex-wrap items-center gap-1 border-b border-gray-200 bg-gray-50/80 px-3 py-1.5 text-xs select-none">
      {/* 1. Nhóm Font chữ học thuật */}
      <div className="flex items-center gap-1 mr-1">
        <select
          aria-label="Chọn font chữ"
          onChange={handleFontFamilyChange}
          defaultValue="Times New Roman, serif"
          className="h-7 bg-white border border-gray-200 rounded px-2 text-xs font-medium text-gray-800 outline-none focus:border-purple-500 hover:border-gray-300 transition"
        >
          {FONT_FAMILIES.map((f) => (
            <option key={f.value} value={f.value}>
              {f.label}
            </option>
          ))}
        </select>

        {/* 2. Nhóm Kích thước chữ (Font Size) */}
        <select
          aria-label="Chọn kích thước chữ"
          onChange={handleFontSizeChange}
          defaultValue="13pt"
          className="h-7 bg-white border border-gray-200 rounded px-2 text-xs font-medium text-gray-800 outline-none focus:border-purple-500 hover:border-gray-300 transition"
        >
          {FONT_SIZES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      <div className="mx-1 h-4 w-px bg-gray-200" />

      {/* 3. Nhóm Định dạng chữ: Bold, Italic, Underline */}
      <div className="flex items-center gap-0.5">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className={buttonClass(editor.isActive("bold"))}
          onClick={() => editor.chain().focus().toggleBold().run()}
          title="In đậm (Ctrl+B)"
        >
          <Bold className="h-3.5 w-3.5" />
        </Button>

        <Button
          type="button"
          variant="ghost"
          size="sm"
          className={buttonClass(editor.isActive("italic"))}
          onClick={() => editor.chain().focus().toggleItalic().run()}
          title="In nghiêng (Ctrl+I)"
        >
          <Italic className="h-3.5 w-3.5" />
        </Button>

        <Button
          type="button"
          variant="ghost"
          size="sm"
          className={buttonClass(editor.isActive("underline"))}
          onClick={() => editor.chain().focus().toggleUnderline().run()}
          title="Gạch chân (Ctrl+U)"
        >
          <UnderlineIcon className="h-3.5 w-3.5" />
        </Button>
      </div>

      <div className="mx-1 h-4 w-px bg-gray-200" />

      {/* 4. Nhóm Tiêu đề (Headings) */}
      <div className="flex items-center gap-0.5">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className={buttonClass(editor.isActive("heading", { level: 1 }))}
          onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
          title="Tiêu đề 1 (Chương lớn)"
        >
          <Heading1 className="h-3.5 w-3.5" />
        </Button>

        <Button
          type="button"
          variant="ghost"
          size="sm"
          className={buttonClass(editor.isActive("heading", { level: 2 }))}
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
          title="Tiêu đề 2 (Mục 1.1)"
        >
          <Heading2 className="h-3.5 w-3.5" />
        </Button>

        <Button
          type="button"
          variant="ghost"
          size="sm"
          className={buttonClass(editor.isActive("heading", { level: 3 }))}
          onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
          title="Tiêu đề 3 (Tiểu mục 1.1.1)"
        >
          <Heading3 className="h-3.5 w-3.5" />
        </Button>
      </div>

      <div className="mx-1 h-4 w-px bg-gray-200" />

      {/* 5. Nhóm Canh lề (Text Alignments - bao gồm Justify) */}
      <div className="flex items-center gap-0.5">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className={buttonClass(editor.isActive({ textAlign: "left" }))}
          onClick={() => editor.chain().focus().setTextAlign("left").run()}
          title="Canh lề trái"
        >
          <AlignLeft className="h-3.5 w-3.5" />
        </Button>

        <Button
          type="button"
          variant="ghost"
          size="sm"
          className={buttonClass(editor.isActive({ textAlign: "center" }))}
          onClick={() => editor.chain().focus().setTextAlign("center").run()}
          title="Canh giữa (Tiêu đề, Bảng, Hình ảnh)"
        >
          <AlignCenter className="h-3.5 w-3.5" />
        </Button>

        <Button
          type="button"
          variant="ghost"
          size="sm"
          className={buttonClass(editor.isActive({ textAlign: "right" }))}
          onClick={() => editor.chain().focus().setTextAlign("right").run()}
          title="Canh lề phải"
        >
          <AlignRight className="h-3.5 w-3.5" />
        </Button>

        <Button
          type="button"
          variant="ghost"
          size="sm"
          className={buttonClass(editor.isActive({ textAlign: "justify" }))}
          onClick={() => editor.chain().focus().setTextAlign("justify").run()}
          title="Căn đều hai bên (Chuẩn văn bản học thuật)"
        >
          <AlignJustify className="h-3.5 w-3.5" />
        </Button>
      </div>

      <div className="mx-1 h-4 w-px bg-gray-200" />

      {/* 6. Nhóm Danh sách (Bullets & Numbers) */}
      <div className="flex items-center gap-0.5">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className={buttonClass(editor.isActive("bulletList"))}
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          title="Danh sách dấu chấm"
        >
          <List className="h-3.5 w-3.5" />
        </Button>

        <Button
          type="button"
          variant="ghost"
          size="sm"
          className={buttonClass(editor.isActive("orderedList"))}
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          title="Danh sách số thứ tự"
        >
          <ListOrdered className="h-3.5 w-3.5" />
        </Button>
      </div>

      <div className="mx-1 h-4 w-px bg-gray-200" />

      {/* 7. Nhóm Bảng biểu (Table Controls) */}
      <div className="relative">
        <div className="flex items-center">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className={cn(
              buttonClass(isTableActive),
              "w-auto px-1.5 gap-1 text-[11px] font-medium"
            )}
            onClick={() => {
              if (!isTableActive) {
                editor
                  .chain()
                  .focus()
                  .insertTable({ rows: 3, cols: 3, withHeaderRow: true })
                  .run();
              } else {
                setIsTableMenuOpen(!isTableMenuOpen);
              }
            }}
            title={isTableActive ? "Tùy chọn bảng biểu" : "Chèn bảng mới (3x3)"}
          >
            <TableIcon className="h-3.5 w-3.5" />
            <span>Bảng</span>
            <ChevronDown className="h-2.5 w-2.5 opacity-60" />
          </Button>
        </div>

        {/* Dropdown menu thao tác bảng */}
        {isTableMenuOpen && isTableActive && (
          <div className="absolute top-full left-0 mt-1 z-50 bg-white border border-gray-200 rounded-lg shadow-lg p-1.5 w-44 space-y-0.5 text-xs text-gray-700">
            <button
              type="button"
              onClick={() => {
                editor.chain().focus().addRowBefore().run();
                setIsTableMenuOpen(false);
              }}
              className="w-full text-left px-2 py-1 hover:bg-purple-50 rounded flex items-center gap-1.5"
            >
              <Plus className="h-3 w-3 text-purple-600" /> Thêm hàng trên
            </button>
            <button
              type="button"
              onClick={() => {
                editor.chain().focus().addRowAfter().run();
                setIsTableMenuOpen(false);
              }}
              className="w-full text-left px-2 py-1 hover:bg-purple-50 rounded flex items-center gap-1.5"
            >
              <Plus className="h-3 w-3 text-purple-600" /> Thêm hàng dưới
            </button>
            <div className="h-px bg-gray-100 my-1" />
            <button
              type="button"
              onClick={() => {
                editor.chain().focus().addColumnBefore().run();
                setIsTableMenuOpen(false);
              }}
              className="w-full text-left px-2 py-1 hover:bg-purple-50 rounded flex items-center gap-1.5"
            >
              <Plus className="h-3 w-3 text-purple-600" /> Thêm cột trái
            </button>
            <button
              type="button"
              onClick={() => {
                editor.chain().focus().addColumnAfter().run();
                setIsTableMenuOpen(false);
              }}
              className="w-full text-left px-2 py-1 hover:bg-purple-50 rounded flex items-center gap-1.5"
            >
              <Plus className="h-3 w-3 text-purple-600" /> Thêm cột phải
            </button>
            <div className="h-px bg-gray-100 my-1" />
            <button
              type="button"
              onClick={() => {
                editor.chain().focus().deleteRow().run();
                setIsTableMenuOpen(false);
              }}
              className="w-full text-left px-2 py-1 hover:bg-red-50 text-red-600 rounded flex items-center gap-1.5"
            >
              <Trash2 className="h-3 w-3" /> Xóa hàng này
            </button>
            <button
              type="button"
              onClick={() => {
                editor.chain().focus().deleteColumn().run();
                setIsTableMenuOpen(false);
              }}
              className="w-full text-left px-2 py-1 hover:bg-red-50 text-red-600 rounded flex items-center gap-1.5"
            >
              <Trash2 className="h-3 w-3" /> Xóa cột này
            </button>
            <button
              type="button"
              onClick={() => {
                editor.chain().focus().deleteTable().run();
                setIsTableMenuOpen(false);
              }}
              className="w-full text-left px-2 py-1 hover:bg-red-50 text-red-600 rounded font-semibold flex items-center gap-1.5"
            >
              <Trash2 className="h-3 w-3" /> Xóa toàn bộ bảng
            </button>
          </div>
        )}
      </div>

      <div className="mx-1 h-4 w-px bg-gray-200" />

      {/* 8. Nhóm Header & Footer Học Thuật */}
      <div className="flex items-center gap-0.5">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-[11px] font-medium text-gray-700 hover:bg-gray-200 flex items-center gap-1"
          onClick={handleInsertHeader}
          title="Chèn khung Tiêu đề Đầu trang (Header)"
        >
          <LayoutTemplate className="h-3.5 w-3.5 text-purple-600" />
          <span>Đầu trang</span>
        </Button>

        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-[11px] font-medium text-gray-700 hover:bg-gray-200 flex items-center gap-1"
          onClick={handleInsertFooter}
          title="Chèn khung Tiêu đề Chân trang (Footer)"
        >
          <LayoutTemplate className="h-3.5 w-3.5 text-purple-600 rotate-180" />
          <span>Chân trang</span>
        </Button>
      </div>

      <div className="mx-1 h-4 w-px bg-gray-200" />

      {/* 9. Nút Mục Lục (Table of Contents) */}
      {onInsertToc && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-[11px] font-medium bg-purple-50 text-purple-700 hover:bg-purple-100 flex items-center gap-1 border border-purple-200 rounded"
          onClick={onInsertToc}
          title="Chèn Mục Lục chuẩn học thuật từ Dàn ý"
        >
          <FileText className="h-3.5 w-3.5" />
          <span>Mục lục</span>
        </Button>
      )}

      {/* 10. Nút Khổ A4 vs Toàn màn hình */}
      {onToggleA4Mode && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className={cn(
            "h-7 px-2 text-[11px] font-medium flex items-center gap-1 border rounded transition",
            isA4Mode
              ? "bg-purple-100/90 text-purple-800 border-purple-300 font-semibold"
              : "bg-white text-gray-700 hover:bg-gray-100 border-gray-200"
          )}
          onClick={onToggleA4Mode}
          title={
            isA4Mode
              ? "Đang ở chế độ xem Khổ A4 chuẩn học thuật (Click để chuyển Tràn viền)"
              : "Đang ở chế độ Tràn viền (Click để chuyển xem Khổ A4 chuẩn học thuật)"
          }
        >
          {isA4Mode ? (
            <>
              <BookOpen className="h-3.5 w-3.5 text-purple-700" />
              <span>Khổ A4</span>
            </>
          ) : (
            <>
              <Maximize2 className="h-3.5 w-3.5 text-gray-600" />
              <span>Tràn viền</span>
            </>
          )}
        </Button>
      )}

      {/* 10. Nhóm Undo / Redo */}
      <div className="ml-auto flex items-center gap-0.5">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0"
          onClick={() => editor.chain().focus().undo().run()}
          disabled={!editor.can().undo()}
          title="Hoàn tác (Ctrl+Z)"
        >
          <Undo2 className="h-3.5 w-3.5" />
        </Button>

        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0"
          onClick={() => editor.chain().focus().redo().run()}
          disabled={!editor.can().redo()}
          title="Làm lại (Ctrl+Y)"
        >
          <Redo2 className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}

export default EditorToolbar;
