import { ChevronRight, ChevronDown, Pencil, Trash2, Plus } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Button, buttonVariants } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import type { CategoryNode } from "@/api/types";

interface CategoryTreeProps {
  nodes: CategoryNode[];
  onEdit: (node: CategoryNode) => void;
  onDelete: (node: CategoryNode) => void;
  onAddChild: (parentId: number) => void;
  selectedIds?: Set<number>;
  onToggleSelect?: (id: number) => void;
}

interface TreeNodeProps {
  node: CategoryNode;
  onEdit: (node: CategoryNode) => void;
  onDelete: (node: CategoryNode) => void;
  onAddChild: (parentId: number) => void;
  selectedIds?: Set<number>;
  onToggleSelect?: (id: number) => void;
}

function TreeNode({ node, onEdit, onDelete, onAddChild, selectedIds, onToggleSelect }: TreeNodeProps) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = node.children && node.children.length > 0;
  const selectable = selectedIds !== undefined && onToggleSelect !== undefined;

  return (
    <div>
      <div className="group flex items-center gap-1 rounded px-1 py-0.5 hover:bg-muted/50">
        {selectable && (
          <Checkbox
            checked={selectedIds.has(node.id)}
            onClick={() => onToggleSelect(node.id)}
            className="h-3.5 w-3.5 mr-0.5"
          />
        )}

        {/* Expand/collapse chevron */}
        <button
          onClick={() => setExpanded((e) => !e)}
          className="h-5 w-5 flex items-center justify-center text-muted-foreground hover:text-foreground"
          aria-label={expanded ? "Collapse" : "Expand"}
          disabled={!hasChildren}
        >
          {hasChildren ? (
            expanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )
          ) : (
            <span className="h-4 w-4" />
          )}
        </button>

        {/* Category name */}
        <span className="flex-1 text-sm">
          {node.name}
          <span className="ml-1.5 text-xs text-muted-foreground">
            ({node.image_count ?? 0})
          </span>
        </span>

        {/* Hover action buttons */}
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
          <Link
            to={`/categories/${node.id}/images`}
            className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "h-6 px-2 text-xs")}
          >
            View images
          </Link>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => onAddChild(node.id)}
            title="Add child category"
          >
            <Plus className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => onEdit(node)}
            title="Edit category"
          >
            <Pencil className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => onDelete(node)}
            title="Delete category"
          >
            <Trash2 className="h-3.5 w-3.5 text-destructive" />
          </Button>
        </div>
      </div>

      {/* Children */}
      {hasChildren && expanded && (
        <div className="ml-5 pl-3 border-l border-border">
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              onEdit={onEdit}
              onDelete={onDelete}
              onAddChild={onAddChild}
              selectedIds={selectedIds}
              onToggleSelect={onToggleSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function CategoryTree({
  nodes,
  onEdit,
  onDelete,
  onAddChild,
  selectedIds,
  onToggleSelect,
}: CategoryTreeProps) {
  if (!nodes || nodes.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">No categories yet</p>
    );
  }

  return (
    <div className="space-y-0.5">
      {nodes.map((node) => (
        <TreeNode
          key={node.id}
          node={node}
          onEdit={onEdit}
          onDelete={onDelete}
          onAddChild={onAddChild}
          selectedIds={selectedIds}
          onToggleSelect={onToggleSelect}
        />
      ))}
    </div>
  );
}
