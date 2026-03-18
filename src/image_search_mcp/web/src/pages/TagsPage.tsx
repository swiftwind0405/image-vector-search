import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Link } from "react-router-dom";
import { useTags, useCreateTag, useRenameTag, useDeleteTag } from "@/api/tags";
import type { Tag } from "@/api/types";
import { toast } from "sonner";
import { Pencil, Trash2 } from "lucide-react";

export default function TagsPage() {
  const { data: tags, isLoading } = useTags();
  const createTag = useCreateTag();
  const renameTag = useRenameTag();
  const deleteTag = useDeleteTag();

  const [newName, setNewName] = useState("");
  const [editingTag, setEditingTag] = useState<Tag | null>(null);
  const [editName, setEditName] = useState("");
  const [deletingTag, setDeletingTag] = useState<Tag | null>(null);

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = newName.trim();
    if (!trimmed) return;
    createTag.mutate(trimmed, {
      onSuccess: () => {
        setNewName("");
        toast.success(`Tag "${trimmed}" created`);
      },
      onError: () => {
        toast.error("Failed to create tag");
      },
    });
  };

  const handleRename = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingTag) return;
    const trimmed = editName.trim();
    if (!trimmed) return;
    renameTag.mutate(
      { id: editingTag.id, name: trimmed },
      {
        onSuccess: () => {
          setEditingTag(null);
          setEditName("");
          toast.success(`Tag renamed to "${trimmed}"`);
        },
        onError: () => {
          toast.error("Failed to rename tag");
        },
      },
    );
  };

  const handleDelete = () => {
    if (!deletingTag) return;
    deleteTag.mutate(deletingTag.id, {
      onSuccess: () => {
        setDeletingTag(null);
        toast.success(`Tag "${deletingTag.name}" deleted`);
      },
      onError: () => {
        toast.error("Failed to delete tag");
      },
    });
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Tags</h1>

      {/* Create Tag */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Create Tag</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} className="flex gap-2">
            <Input
              placeholder="Tag name..."
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="max-w-sm"
            />
            <Button type="submit" disabled={createTag.isPending || !newName.trim()}>
              Create
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Tag List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">All Tags</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : !tags || tags.length === 0 ? (
            <p className="text-sm text-muted-foreground">No tags yet</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {tags.map((tag) => (
                <div
                  key={tag.id}
                  className="group flex items-center gap-1.5 rounded-full border bg-muted/40 py-1 pl-3 pr-1 transition-colors hover:bg-muted"
                >
                  <Link
                    className="text-sm font-medium hover:underline"
                    to={`/tags/${tag.id}/images`}
                  >
                    {tag.name}
                  </Link>
                  <Badge variant="secondary" className="rounded-full px-1.5 text-xs font-normal">
                    {tag.image_count ?? 0}
                  </Badge>
                  <div className="flex opacity-0 transition-opacity group-hover:opacity-100">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() => {
                        setEditingTag(tag);
                        setEditName(tag.name);
                      }}
                    >
                      <Pencil className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() => setDeletingTag(tag)}
                    >
                      <Trash2 className="h-3 w-3 text-destructive" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <Dialog
        open={editingTag !== null}
        onOpenChange={(open) => {
          if (!open) {
            setEditingTag(null);
            setEditName("");
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename Tag</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleRename} className="space-y-4">
            <Input
              placeholder="New tag name..."
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              autoFocus
            />
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setEditingTag(null);
                  setEditName("");
                }}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={renameTag.isPending || !editName.trim()}
              >
                Save
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deletingTag !== null}
        onOpenChange={(open) => {
          if (!open) setDeletingTag(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Tag</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Are you sure you want to delete the tag{" "}
            <span className="font-medium text-foreground">
              "{deletingTag?.name}"
            </span>
            ? This action cannot be undone.
          </p>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeletingTag(null)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteTag.isPending}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
