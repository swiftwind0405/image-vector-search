import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  useCategories,
  useCreateCategory,
  useUpdateCategory,
  useDeleteCategory,
} from "@/api/categories";
import type { CategoryNode } from "@/api/types";
import CategoryTree from "@/components/CategoryTree";
import { toast } from "sonner";
import { Plus } from "lucide-react";

type MoveAction = "none" | "root" | "reparent";

export default function CategoriesPage() {
  const { data: categories, isLoading } = useCategories();
  const createCategory = useCreateCategory();
  const updateCategory = useUpdateCategory();
  const deleteCategory = useDeleteCategory();

  // Create dialog state
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [createParentId, setCreateParentId] = useState<number | null>(null);
  const [createName, setCreateName] = useState("");

  // Edit dialog state
  const [editingNode, setEditingNode] = useState<CategoryNode | null>(null);
  const [editName, setEditName] = useState("");
  const [moveAction, setMoveAction] = useState<MoveAction>("none");
  const [newParentId, setNewParentId] = useState("");

  // Delete dialog state
  const [deletingNode, setDeletingNode] = useState<CategoryNode | null>(null);

  const countChildren = (node: CategoryNode): number => {
    let count = node.children.length;
    for (const child of node.children) {
      count += countChildren(child);
    }
    return count;
  };

  const handleOpenCreate = (parentId: number | null = null) => {
    setCreateParentId(parentId);
    setCreateName("");
    setShowCreateDialog(true);
  };

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = createName.trim();
    if (!trimmed) return;
    createCategory.mutate(
      { name: trimmed, parent_id: createParentId },
      {
        onSuccess: () => {
          setShowCreateDialog(false);
          setCreateName("");
          setCreateParentId(null);
          toast.success(`Category "${trimmed}" created`);
        },
        onError: () => {
          toast.error("Failed to create category");
        },
      },
    );
  };

  const handleOpenEdit = (node: CategoryNode) => {
    setEditingNode(node);
    setEditName(node.name);
    setMoveAction("none");
    setNewParentId("");
  };

  const handleEdit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingNode) return;
    const trimmed = editName.trim();
    if (!trimmed) return;

    const payload: {
      id: number;
      name?: string;
      move_to_root?: boolean;
      move_to_parent_id?: number | null;
    } = { id: editingNode.id };

    if (trimmed !== editingNode.name) {
      payload.name = trimmed;
    }

    if (moveAction === "root") {
      payload.move_to_root = true;
    } else if (moveAction === "reparent") {
      const parsedId = parseInt(newParentId, 10);
      if (!isNaN(parsedId)) {
        payload.move_to_parent_id = parsedId;
      }
    }

    updateCategory.mutate(payload, {
      onSuccess: () => {
        setEditingNode(null);
        setEditName("");
        setMoveAction("none");
        setNewParentId("");
        toast.success(`Category "${trimmed}" updated`);
      },
      onError: () => {
        toast.error("Failed to update category");
      },
    });
  };

  const handleDelete = () => {
    if (!deletingNode) return;
    deleteCategory.mutate(deletingNode.id, {
      onSuccess: () => {
        setDeletingNode(null);
        toast.success(`Category "${deletingNode.name}" deleted`);
      },
      onError: () => {
        toast.error("Failed to delete category");
      },
    });
  };

  const childrenCount = deletingNode ? countChildren(deletingNode) : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Categories</h1>
        <Button onClick={() => handleOpenCreate(null)}>
          <Plus className="h-4 w-4 mr-2" />
          New Category
        </Button>
      </div>

      {/* Category Tree */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Category Hierarchy</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : (
            <CategoryTree
              nodes={categories ?? []}
              onEdit={handleOpenEdit}
              onDelete={(node) => setDeletingNode(node)}
              onAddChild={(parentId) => handleOpenCreate(parentId)}
            />
          )}
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <Dialog
        open={showCreateDialog}
        onOpenChange={(open) => {
          if (!open) {
            setShowCreateDialog(false);
            setCreateName("");
            setCreateParentId(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {createParentId !== null ? "Add Child Category" : "New Category"}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="create-name">Name</Label>
              <Input
                id="create-name"
                placeholder="Category name..."
                value={createName}
                onChange={(e) => setCreateName(e.target.value)}
                autoFocus
              />
            </div>
            {createParentId !== null && (
              <p className="text-sm text-muted-foreground">
                Parent category ID: <span className="font-medium text-foreground">{createParentId}</span>
              </p>
            )}
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setShowCreateDialog(false);
                  setCreateName("");
                  setCreateParentId(null);
                }}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={createCategory.isPending || !createName.trim()}
              >
                Create
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog
        open={editingNode !== null}
        onOpenChange={(open) => {
          if (!open) {
            setEditingNode(null);
            setEditName("");
            setMoveAction("none");
            setNewParentId("");
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Category</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleEdit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="edit-name">Name</Label>
              <Input
                id="edit-name"
                placeholder="Category name..."
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                autoFocus
              />
            </div>

            <div className="space-y-2">
              <Label>Move</Label>
              <div className="flex gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant={moveAction === "none" ? "default" : "outline"}
                  onClick={() => setMoveAction("none")}
                >
                  No move
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant={moveAction === "root" ? "default" : "outline"}
                  onClick={() => setMoveAction("root")}
                >
                  Move to root
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant={moveAction === "reparent" ? "default" : "outline"}
                  onClick={() => setMoveAction("reparent")}
                >
                  Reparent
                </Button>
              </div>
            </div>

            {moveAction === "reparent" && (
              <div className="space-y-2">
                <Label htmlFor="new-parent-id">Parent Category ID</Label>
                <Input
                  id="new-parent-id"
                  type="number"
                  placeholder="Parent ID..."
                  value={newParentId}
                  onChange={(e) => setNewParentId(e.target.value)}
                />
              </div>
            )}

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setEditingNode(null);
                  setEditName("");
                  setMoveAction("none");
                  setNewParentId("");
                }}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={updateCategory.isPending || !editName.trim()}
              >
                Save
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deletingNode !== null}
        onOpenChange={(open) => {
          if (!open) setDeletingNode(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Category</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Are you sure you want to delete{" "}
            <span className="font-medium text-foreground">
              "{deletingNode?.name}"
            </span>
            ?{" "}
            {childrenCount > 0 && (
              <>
                This category has{" "}
                <span className="font-medium text-foreground">
                  {childrenCount} child {childrenCount === 1 ? "category" : "categories"}
                </span>{" "}
                that will also be affected.{" "}
              </>
            )}
            This action cannot be undone.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletingNode(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteCategory.isPending}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
