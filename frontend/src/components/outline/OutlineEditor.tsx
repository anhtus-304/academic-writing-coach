"use client";

import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Plus,
  Trash2,
  Edit2,
  Check,
  X,
  FileText,
  Bookmark,
} from "lucide-react";
import { cn } from "@/lib/utils";

export type OutlineNode = {
  id: string;
  title: string;
  level: number;
  children?: OutlineNode[];
};

type OutlineEditorProps = {
  outline: OutlineNode[];
  onChange?: (outline: OutlineNode[]) => void;
  title?: string;
  onNavigateToSection?: (sectionTitle: string) => void;
  onInsertTableOfContents?: (tocHtml: string) => void;
};

const createNodeId = () =>
  `outline-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;

const normalizeOutline = (items: OutlineNode[] | undefined): OutlineNode[] => {
  if (!Array.isArray(items)) {
    return [];
  }

  return items.map((node, index) => ({
    id: node?.id ?? createNodeId(),
    title: node?.title?.trim() || `Chương ${index + 1}`,
    level: typeof node?.level === "number" ? node.level : 0,
    children: normalizeOutline(node?.children),
  }));
};

function updateNodeById(
  nodes: OutlineNode[],
  nodeId: string,
  updater: (node: OutlineNode) => OutlineNode
): OutlineNode[] {
  return nodes.map((node) => {
    if (node.id === nodeId) {
      return updater(node);
    }

    if (node.children?.length) {
      return {
        ...node,
        children: updateNodeById(node.children, nodeId, updater),
      };
    }

    return node;
  });
}

function removeNodeById(nodes: OutlineNode[], nodeId: string): OutlineNode[] {
  return nodes
    .filter((node) => node.id !== nodeId)
    .map((node) => ({
      ...node,
      children: node.children ? removeNodeById(node.children, nodeId) : undefined,
    }));
}

function addChildNode(nodes: OutlineNode[], parentId: string): OutlineNode[] {
  return nodes.map((node) => {
    if (node.id === parentId) {
      const nextIndex = (node.children?.length || 0) + 1;
      const newChild: OutlineNode = {
        id: createNodeId(),
        title: `Mục mới ${nextIndex}`,
        level: (node.level ?? 0) + 1,
        children: [],
      };

      return {
        ...node,
        children: [...(node.children ?? []), newChild],
      };
    }

    if (node.children?.length) {
      return {
        ...node,
        children: addChildNode(node.children, parentId),
      };
    }

    return node;
  });
}

/**
 * Sinh chuỗi HTML Mục Lục chuẩn học thuật với dải chấm leader dots
 */
export function generateTableOfContentsHtml(nodes: OutlineNode[]): string {
  if (!nodes || nodes.length === 0) return "";

  let estimatedPage = 1;
  let itemsHtml = "";

  function traverse(list: OutlineNode[], prefix = "") {
    list.forEach((node, index) => {
      const currentNumber = prefix ? `${prefix}.${index + 1}` : `${index + 1}`;
      const isTopLevel = !prefix;
      const indentPx = prefix ? (prefix.split(".").length * 16) : 0;
      const pageNum = estimatedPage;
      estimatedPage += isTopLevel ? 3 : 1;

      itemsHtml += `
        <div class="toc-item" style="display: flex; align-items: baseline; margin-bottom: 6px; padding-left: ${indentPx}px; font-size: ${isTopLevel ? "13pt" : "12pt"}; font-weight: ${isTopLevel ? "bold" : "normal"};">
          <span class="toc-title" style="white-space: nowrap; max-width: 75%; overflow: hidden; text-overflow: ellipsis;">
            ${currentNumber}. ${node.title}
          </span>
          <span class="toc-dots" style="flex: 1; border-bottom: 1px dotted #666; margin: 0 8px; height: 1em; min-width: 20px;"></span>
          <span class="toc-page" style="font-family: monospace; font-size: 11pt;">${pageNum}</span>
        </div>
      `;

      if (node.children && node.children.length > 0) {
        traverse(node.children, currentNumber);
      }
    });
  }

  traverse(nodes);

  return `
    <div class="table-of-contents-block" style="margin: 24px 0; padding: 18px 24px; background-color: #fafafa; border: 1px solid #e5e7eb; border-radius: 8px; font-family: 'Times New Roman', serif;">
      <h2 style="text-align: center; font-weight: bold; text-transform: uppercase; font-size: 15pt; margin-bottom: 16px; color: #111827; letter-spacing: 0.5px;">
        MỤC LỤC
      </h2>
      <div class="toc-list" style="line-height: 1.6;">
        ${itemsHtml}
      </div>
    </div>
    <p></p>
  `;
}

export function OutlineEditor({
  outline,
  onChange,
  title = "Cấu trúc dàn ý",
  onNavigateToSection,
  onInsertTableOfContents,
}: OutlineEditorProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const normalizedOutline = normalizeOutline(outline);

  const emitChange = (nextOutline: OutlineNode[]) => {
    onChange?.(normalizeOutline(nextOutline));
  };

  const handleTitleChange = (nodeId: string, value: string) => {
    const nextOutline = updateNodeById(normalizedOutline, nodeId, (node) => ({
      ...node,
      title: value,
    }));
    emitChange(nextOutline);
  };

  const handleAddChild = (nodeId: string) => {
    const nextOutline = addChildNode(normalizedOutline, nodeId);
    emitChange(nextOutline);
    setExpanded((current) => ({ ...current, [nodeId]: true }));
  };

  const handleDeleteNode = (nodeId: string) => {
    const nextOutline = removeNodeById(normalizedOutline, nodeId);
    emitChange(nextOutline);
  };

  const handleInsertToc = () => {
    if (onInsertTableOfContents) {
      const html = generateTableOfContentsHtml(normalizedOutline);
      onInsertTableOfContents(html);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg border border-gray-200 overflow-hidden shadow-xs">
      {/* Header Bar */}
      <div className="p-3 border-b border-gray-100 bg-gray-50/70 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 text-xs font-bold text-gray-800">
          <Bookmark className="w-3.5 h-3.5 text-purple-600" />
          <span>{title}</span>
          <span className="text-[10px] bg-purple-100 text-purple-700 px-1.5 py-0.2 rounded-full font-normal">
            {normalizedOutline.length} mục
          </span>
        </div>

        <div className="flex items-center gap-1">
          {onInsertTableOfContents && (
            <button
              type="button"
              onClick={handleInsertToc}
              title="Chèn toàn bộ cây Mục Lục vào vị trí con trỏ trong bài viết"
              className="inline-flex items-center gap-1 text-[11px] font-medium bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200 px-2 py-1 rounded transition active:scale-95"
            >
              <FileText className="w-3 h-3" />
              <span>Chèn Mục Lục</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => {
              const nextNumber = normalizedOutline.length + 1;
              const newNode: OutlineNode = {
                id: createNodeId(),
                title: `Chương ${nextNumber}: Tiêu đề mới`,
                level: 1,
                children: [],
              };
              emitChange([...normalizedOutline, newNode]);
            }}
            title="Thêm một chương chính"
            className="inline-flex items-center gap-1 text-[11px] font-medium bg-white text-gray-700 hover:bg-gray-100 border border-gray-200 px-2 py-1 rounded transition"
          >
            <Plus className="w-3 h-3" />
            <span>Thêm chương</span>
          </button>
        </div>
      </div>

      {/* Outline Content Body */}
      <div className="p-2 overflow-y-auto max-h-[calc(100vh-280px)] space-y-1">
        {normalizedOutline.length === 0 ? (
          <div className="text-center py-8 px-4 text-xs text-gray-400">
            Dàn ý đang trống. Hãy nhấn &quot;Sinh dàn ý AI&quot; hoặc &quot;Thêm chương&quot; để bắt đầu xây dựng cấu trúc.
          </div>
        ) : (
          normalizedOutline.map((node, index) => (
            <OutlineItem
              key={node.id}
              node={node}
              index={index + 1}
              prefix=""
              depth={0}
              expanded={expanded}
              onToggleExpand={(id) =>
                setExpanded((curr) => ({ ...curr, [id]: !(curr[id] ?? true) }))
              }
              onTitleChange={handleTitleChange}
              onAddChild={handleAddChild}
              onDelete={handleDeleteNode}
              onNavigate={onNavigateToSection}
            />
          ))
        )}
      </div>
    </div>
  );
}

interface OutlineItemProps {
  node: OutlineNode;
  index: number;
  prefix: string;
  depth: number;
  expanded: Record<string, boolean>;
  onToggleExpand: (id: string) => void;
  onTitleChange: (id: string, value: string) => void;
  onAddChild: (id: string) => void;
  onDelete: (id: string) => void;
  onNavigate?: (title: string) => void;
}

function OutlineItem({
  node,
  index,
  prefix,
  depth,
  expanded,
  onToggleExpand,
  onTitleChange,
  onAddChild,
  onDelete,
  onNavigate,
}: OutlineItemProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [titleValue, setTitleValue] = useState(node.title);
  const hasChildren = Boolean(node.children?.length);
  const isExpanded = expanded[node.id] ?? true;

  const currentNumber = prefix ? `${prefix}.${index}` : `${index}`;
  const isTopLevel = depth === 0;

  const handleSaveTitle = () => {
    if (titleValue.trim()) {
      onTitleChange(node.id, titleValue.trim());
    } else {
      setTitleValue(node.title);
    }
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setTitleValue(node.title);
    setIsEditing(false);
  };

  return (
    <div className="group/item text-xs select-none">
      <div
        className={cn(
          "flex items-center gap-1.5 py-1.5 px-2 rounded-md transition-colors hover:bg-purple-50/60",
          isTopLevel ? "font-semibold text-gray-900" : "text-gray-700 font-normal"
        )}
        style={{ paddingLeft: `${Math.max(6, depth * 12 + 6)}px` }}
      >
        {/* Toggle Expand Icon */}
        {hasChildren ? (
          <button
            type="button"
            onClick={() => onToggleExpand(node.id)}
            className="w-4 h-4 flex items-center justify-center text-gray-400 hover:text-gray-700 transition"
            title={isExpanded ? "Thu gọn" : "Mở rộng"}
          >
            {isExpanded ? (
              <ChevronDown className="w-3.5 h-3.5" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5" />
            )}
          </button>
        ) : (
          <div className="w-4 h-4 flex items-center justify-center text-gray-300">
            <span className="w-1.5 h-1.5 rounded-full bg-gray-300" />
          </div>
        )}

        {/* Number Badge */}
        <span
          className={cn(
            "font-mono text-[11px] shrink-0",
            isTopLevel ? "text-purple-700 font-bold" : "text-gray-500"
          )}
        >
          {currentNumber}.
        </span>

        {/* Title Content / Inline Input */}
        {isEditing ? (
          <div className="flex-1 flex items-center gap-1">
            <input
              type="text"
              value={titleValue}
              onChange={(e) => setTitleValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSaveTitle();
                if (e.key === "Escape") handleCancelEdit();
              }}
              autoFocus
              className="flex-1 bg-white border border-purple-400 rounded px-1.5 py-0.5 text-xs text-gray-900 outline-none focus:ring-1 focus:ring-purple-500"
            />
            <button
              type="button"
              onClick={handleSaveTitle}
              className="p-1 text-emerald-600 hover:bg-emerald-50 rounded"
              title="Lưu"
            >
              <Check className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={handleCancelEdit}
              className="p-1 text-gray-400 hover:bg-gray-100 rounded"
              title="Hủy"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <span
            onClick={() => onNavigate?.(node.title)}
            onDoubleClick={() => setIsEditing(true)}
            title="Nhấp để cuộn tới tiêu đề trong bài viết; Nhấp đúp để sửa"
            className="flex-1 truncate cursor-pointer hover:text-purple-700 hover:underline transition"
          >
            {node.title}
          </span>
        )}

        {/* Action Buttons (Hover visible) */}
        {!isEditing && (
          <div className="opacity-0 group-hover/item:opacity-100 flex items-center gap-0.5 transition shrink-0">
            <button
              type="button"
              onClick={() => setIsEditing(true)}
              className="p-1 text-gray-400 hover:text-purple-600 hover:bg-purple-100/50 rounded transition"
              title="Đổi tên"
            >
              <Edit2 className="w-3 h-3" />
            </button>
            <button
              type="button"
              onClick={() => onAddChild(node.id)}
              className="p-1 text-gray-400 hover:text-purple-600 hover:bg-purple-100/50 rounded transition"
              title="Thêm mục con"
            >
              <Plus className="w-3 h-3" />
            </button>
            <button
              type="button"
              onClick={() => onDelete(node.id)}
              className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition"
              title="Xóa mục này"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        )}
      </div>

      {/* Subsections Recursive */}
      {hasChildren && isExpanded && (
        <div className="border-l border-gray-100 ml-3.5 my-0.5 space-y-0.5">
          {node.children?.map((child, childIdx) => (
            <OutlineItem
              key={child.id}
              node={child}
              index={childIdx + 1}
              prefix={currentNumber}
              depth={depth + 1}
              expanded={expanded}
              onToggleExpand={onToggleExpand}
              onTitleChange={onTitleChange}
              onAddChild={onAddChild}
              onDelete={onDelete}
              onNavigate={onNavigate}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default OutlineEditor;
