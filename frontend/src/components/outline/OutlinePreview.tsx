import type { OutlineNode } from "./OutlineEditor";

type OutlinePreviewProps = {
  outline: OutlineNode[];
};

export function OutlinePreview({ outline }: OutlinePreviewProps) {
  const renderNode = (node: OutlineNode, depth = 0) => (
    <div key={node.id} className="space-y-2">
      <div className="flex items-center gap-2" style={{ marginLeft: depth * 16 }}>
        <span className="text-sm font-medium text-foreground">{node.title}</span>
      </div>
      {node.children?.map((child) => renderNode(child, depth + 1))}
    </div>
  );

  return (
    <div className="rounded-xl border border-border bg-muted/10 p-4">
      <h4 className="mb-3 text-sm font-semibold uppercase tracking-[0.08em] text-muted-foreground">
        Updated outline
      </h4>
      <div className="space-y-3">{outline.length > 0 ? outline.map((node) => renderNode(node)) : <p className="text-sm text-muted-foreground">No content yet.</p>}</div>
    </div>
  );
}
