"use client";

import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  GripVertical,
  Plus,
  Trash2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
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
};

const createNodeId = () =>
  `outline-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;

const normalizeOutline = (items: OutlineNode[] | undefined): OutlineNode[] => {
  if (!Array.isArray(items)) {
    return [];
  }

  return items.map((node, index) => ({
    id: node?.id ?? createNodeId(),
    title: node?.title?.trim() || `Section ${index + 1}`,
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
      const newChild: OutlineNode = {
        id: createNodeId(),
        title: "New section",
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

function findNodePath(
  nodes: OutlineNode[],
  nodeId: string,
  currentParent: OutlineNode[] | null = null
): { parent: OutlineNode[]; index: number } | null {
  for (let index = 0; index < nodes.length; index += 1) {
    const node = nodes[index];
    if (node.id === nodeId) {
      return {
        parent: currentParent ?? nodes,
        index,
      };
    }

    if (node.children?.length) {
      const found = findNodePath(node.children, nodeId, node.children);
      if (found) {
        return found;
      }
    }
  }

  return null;
}

function reorderNodes(
  nodes: OutlineNode[],
  draggedId: string,
  targetId: string
): OutlineNode[] {
  if (!draggedId || !targetId || draggedId === targetId) {
    return nodes;
  }

  const source = findNodePath(nodes, draggedId);
  const target = findNodePath(nodes, targetId);

  if (!source || !target || source.parent === target.parent) {
    return nodes;
  }

  const sourceNode = source.parent[source.index];
  const targetNode = target.parent[target.index];

  if (!sourceNode || !targetNode) {
    return nodes;
  }

  const nextSourceParent = [...source.parent];
  nextSourceParent.splice(source.index, 1);

  const nextTargetParent = [...target.parent];
  const insertionIndex = Math.min(target.index, nextTargetParent.length);
  nextTargetParent.splice(insertionIndex, 0, sourceNode);

  const result = [...nodes];

  const sourceParentId = findParentId(nodes, draggedId);
  const targetParentId = findParentId(nodes, targetId);

  if (sourceParentId === targetParentId) {
    return nodes;
  }

  if (sourceParentId && targetParentId) {
    return rehydrateTree(nodes, sourceParentId, targetParentId, sourceNode);
  }

  return result;
}

function findParentId(nodes: OutlineNode[], targetId: string): string | null {
  for (const node of nodes) {
    if (node.id === targetId) {
      return null;
    }

    if (node.children?.some((child) => child.id === targetId)) {
      return node.id;
    }

    if (node.children?.length) {
      const childParentId = findParentId(node.children, targetId);
      if (childParentId) {
        return childParentId;
      }
    }
  }

  return null;
}

function rehydrateTree(
  nodes: OutlineNode[],
  sourceParentId: string,
  targetParentId: string,
  sourceNode: OutlineNode
): OutlineNode[] {
  return nodes.map((node) => {
    if (node.id === sourceParentId) {
      return {
        ...node,
        children: (node.children ?? []).filter((child) => child.id !== sourceNode.id),
      };
    }

    if (node.id === targetParentId) {
      return {
        ...node,
        children: [...(node.children ?? []), sourceNode],
      };
    }

    if (node.children?.length) {
      return {
        ...node,
        children: rehydrateTree(node.children, sourceParentId, targetParentId, sourceNode),
      };
    }

    return node;
  });
}

export function OutlineEditor({ outline, onChange, title = "Outline" }: OutlineEditorProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [draggedId, setDraggedId] = useState<string | null>(null);

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

  const handleDrop = (targetId: string) => {
    if (!draggedId || draggedId === targetId) {
      setDraggedId(null);
      return;
    }

    const nextOutline = reorderNodes(normalizedOutline, draggedId, targetId);
    emitChange(nextOutline);
    setDraggedId(null);
  };

  const renderOutline = normalizedOutline.map((node) => (
    <OutlineNodeRow
      key={node.id}
      node={node}
      depth={0}
      expanded={expanded}
      onToggleExpand={(id) =>
        setExpanded((current) => ({
          ...current,
          [id]: !(current[id] ?? true),
        }))
      }
      onTitleChange={handleTitleChange}
      onAddChild={handleAddChild}
      onDelete={handleDeleteNode}
      onDrop={handleDrop}
      setDraggedId={setDraggedId}
      draggedId={draggedId}
    />
  ));

  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h3 className="text-base font-semibold text-foreground">{title}</h3>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => {
            const newNode: OutlineNode = {
              id: createNodeId(),
              title: "New section",
              level: 1,
              children: [],
            };
            emitChange([...normalizedOutline, newNode]);
          }}
        >
          <Plus className="mr-1 h-4 w-4" /> Add top-level section
        </Button>
      </div>

      {normalizedOutline.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border bg-muted/20 p-6 text-sm text-muted-foreground">
          Outline trống. Hãy thêm một mục mới.
        </div>
      ) : (
        <div className="space-y-3">{renderOutline}</div>
      )}
    </div>
  );
}

type OutlineNodeRowProps = {
  node: OutlineNode;
  depth: number;
  expanded: Record<string, boolean>;
  onToggleExpand: (id: string) => void;
  onTitleChange: (id: string, value: string) => void;
  onAddChild: (id: string) => void;
  onDelete: (id: string) => void;
  onDrop: (targetId: string) => void;
  setDraggedId: (id: string | null) => void;
  draggedId: string | null;
};

function OutlineNodeRow({
  node,
  depth,
  expanded,
  onToggleExpand,
  onTitleChange,
  onAddChild,
  onDelete,
  onDrop,
  setDraggedId,
  draggedId,
}: OutlineNodeRowProps) {
  const hasChildren = Boolean(node.children?.length);
  const isExpanded = expanded[node.id] ?? true;

  return (
    <div className="space-y-2">
      <div
        className={cn(
          "flex items-center gap-2 rounded-lg border border-transparent bg-muted/10 px-2 py-2 transition-colors",
          draggedId === node.id && "border-primary/40 bg-primary/5"
        )}
        draggable
        onDragStart={(event) => {
          event.dataTransfer.effectAllowed = "move";
          setDraggedId(node.id);
        }}
        onDragEnd={() => setDraggedId(null)}
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          onDrop(node.id);
        }}
        style={{ marginLeft: depth * 18 }}
      >
        <div className="flex w-4 cursor-grab justify-center text-muted-foreground">
          <GripVertical className="h-3.5 w-3.5" />
        </div>

        {hasChildren ? (
          <Button
            type="button"
            variant="ghost"
            size="icon-xs"
            onClick={() => onToggleExpand(node.id)}
            aria-label={isExpanded ? "Collapse section" : "Expand section"}
          >
            {isExpanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
          </Button>
        ) : (
          <div className="w-7" />
        )}

        <input
          value={node.title}
          onChange={(event) => onTitleChange(node.id, event.target.value)}
          className="flex-1 rounded-md border border-transparent bg-transparent px-2 py-1 text-sm font-medium text-foreground outline-none focus:border-border focus:bg-background"
        />

        <Button type="button" variant="ghost" size="icon-xs" onClick={() => onAddChild(node.id)}>
          <Plus className="h-3.5 w-3.5" />
        </Button>

        <Button type="button" variant="ghost" size="icon-xs" onClick={() => onDelete(node.id)}>
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>

      {hasChildren && isExpanded ? (
        <div className="space-y-2 border-l border-border pl-3">
          {node.children?.map((child) => (
            <OutlineNodeRow
              key={child.id}
              node={child}
              depth={depth + 1}
              expanded={expanded}
              onToggleExpand={onToggleExpand}
              onTitleChange={onTitleChange}
              onAddChild={onAddChild}
              onDelete={onDelete}
              onDrop={onDrop}
              setDraggedId={setDraggedId}
              draggedId={draggedId}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
