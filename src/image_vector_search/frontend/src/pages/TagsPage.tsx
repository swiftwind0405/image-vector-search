import { useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Link } from "react-router-dom";
import { useTags, useCreateTag, useRenameTag, useDeleteTag, useBulkDeleteTags, exportTagsMarkdown, useImportTags } from "@/api/tags";
import type { Tag } from "@/api/types";
import { toast } from "sonner";
import { Pencil, Trash2, ListChecks, X, Download, Upload } from "lucide-react";

export default function TagsPage() {
  const { data: tags, isLoading } = useTags();
  const createTag = useCreateTag();
  const renameTag = useRenameTag();
  const deleteTag = useDeleteTag();
  const bulkDeleteTags = useBulkDeleteTags();
  const importTags = useImportTags();

  const fileInputRef = useRef<HTMLInputElement>(null);

  const [newName, setNewName] = useState("");
  const [editingTag, setEditingTag] = useState<Tag | null>(null);
  const [editName, setEditName] = useState("");
  const [deletingTag, setDeletingTag] = useState<Tag | null>(null);

  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [showBulkDelete, setShowBulkDelete] = useState(false);

  const exitSelectMode = () => {
    setSelectMode(false);
    setSelectedIds(new Set());
  };

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (!tags) return;
    if (selectedIds.size === tags.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(tags.map((t) => t.id)));
    }
  };

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

  const handleBulkDelete = () => {
    const ids = Array.from(selectedIds);
    bulkDeleteTags.mutate(ids, {
      onSuccess: (data) => {
        setShowBulkDelete(false);
        setSelectedIds(new Set());
        setSelectMode(false);
        toast.success(`Deleted ${data.deleted} tag(s)`);
      },
      onError: () => {
        toast.error("Failed to delete tags");
      },
    });
  };

  const handleExport = async () => {
    try {
      await exportTagsMarkdown();
      toast.success("Tags exported");
    } catch {
      toast.error("Failed to export tags");
    }
  };

  const handleImportFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    importTags.mutate(file, {
      onSuccess: (data) => {
        toast.success(`Import complete: ${data.created} created, ${data.skipped} skipped`);
      },
      onError: () => {
        toast.error("Failed to import tags");
      },
    });
    // Reset so the same file can be re-selected
    e.target.value = "";
  };

  const selectedTagNames = tags
    ? tags.filter((t) => selectedIds.has(t.id)).map((t) => t.name)
    : [];

  const allSelected = !!tags && tags.length > 0 && selectedIds.size === tags.length;

  return (
    <div className="space-y-6">
      <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <Card className="rounded-[32px] border-white/10 bg-card/72 shadow-curator">
          <CardHeader>
            <CardTitle className="text-base text-white">Create Tag</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="mb-4 text-sm leading-6 text-muted-foreground">
              Add concise descriptive terms that help semantic search, filtering, and editorial review converge on the same image set.
            </p>
            <form onSubmit={handleCreate} className="flex gap-2">
            <Input
              placeholder="Tag name..."
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="max-w-sm rounded-2xl border-white/10 bg-white/[0.03]"
            />
            <Button type="submit" disabled={createTag.isPending || !newName.trim()}>
              Create
            </Button>
            </form>
            <div className="mt-4 flex gap-2">
              <Button variant="outline" size="sm" onClick={handleExport}>
                <Download className="h-3.5 w-3.5 mr-1.5" />
                Export
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => fileInputRef.current?.click()}
                disabled={importTags.isPending}
              >
                <Upload className="h-3.5 w-3.5 mr-1.5" />
                Import
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".md,text/markdown"
                className="hidden"
                onChange={handleImportFile}
              />
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-[32px] border-white/10 bg-card/72 shadow-curator">
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-base text-white">All Tags</CardTitle>
          {tags && tags.length > 0 && (
            <div className="flex items-center gap-2">
              {selectMode ? (
                <>
                  <button
                    type="button"
                    onClick={toggleSelectAll}
                    className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <Checkbox checked={allSelected} />
                    <span>{allSelected ? "Deselect all" : "Select all"}</span>
                  </button>
                  {selectedIds.size > 0 && (
                    <>
                      <span className="text-sm text-muted-foreground">
                        {selectedIds.size} selected
                      </span>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => setShowBulkDelete(true)}
                      >
                        <Trash2 className="h-3.5 w-3.5 mr-1" />
                        Delete Selected
                      </Button>
                    </>
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={exitSelectMode}
                    title="Exit selection mode"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </>
              ) : (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setSelectMode(true)}
                  title="Batch select"
                >
                  <ListChecks className="h-4 w-4" />
                </Button>
              )}
            </div>
          )}
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : !tags || tags.length === 0 ? (
            <p className="text-sm text-muted-foreground">No tags yet</p>
          ) : (
            <div className="flex flex-wrap gap-2.5">
              {tags.map((tag) => (
                <div
                  key={tag.id}
                  className={`group flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.03] py-1.5 pr-1.5 transition-colors hover:bg-white/[0.07] ${selectMode ? "pl-2.5" : "pl-4"}`}
                >
                  {selectMode && (
                    <Checkbox
                      checked={selectedIds.has(tag.id)}
                      onClick={() => toggleSelect(tag.id)}
                      className="h-3.5 w-3.5"
                    />
                  )}
                  <Link
                    className="text-sm font-medium text-white hover:underline"
                    to={`/tags/${tag.id}/images`}
                  >
                    {tag.name}
                  </Link>
                  <Badge variant="secondary" className="rounded-full border border-white/8 bg-white/[0.05] px-2 text-xs font-normal text-muted-foreground">
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
      </section>

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

      {/* Single Delete Confirmation Dialog */}
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

      {/* Bulk Delete Confirmation Dialog */}
      <Dialog
        open={showBulkDelete}
        onOpenChange={(open) => {
          if (!open) setShowBulkDelete(false);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete {selectedIds.size} Tag(s)</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">
              Are you sure you want to delete the following tags? This action cannot be undone.
            </p>
            <div className="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto">
              {selectedTagNames.map((name) => (
                <Badge key={name} variant="secondary">{name}</Badge>
              ))}
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowBulkDelete(false)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleBulkDelete}
              disabled={bulkDeleteTags.isPending}
            >
              Delete {selectedIds.size} Tag(s)
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
