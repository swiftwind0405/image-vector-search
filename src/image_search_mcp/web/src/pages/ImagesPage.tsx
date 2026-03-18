import React, { useState, useEffect } from "react";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import { useImages } from "@/api/images";
import {
  useFolders,
  useOpenFile,
  useRevealFile,
  useBulkAddTag,
  useBulkRemoveTag,
  useBulkAddCategory,
  useBulkRemoveCategory,
  useBulkFolderAddTag,
  useBulkFolderRemoveTag,
  useBulkFolderAddCategory,
  useBulkFolderRemoveCategory,
} from "@/api/bulk";
import { useTags } from "@/api/tags";
import { useCategories } from "@/api/categories";
import ImageTagEditor from "@/components/ImageTagEditor";
import FilterBar from "@/components/FilterBar";
import GalleryGrid from "@/components/GalleryGrid";
import ImageModal from "@/components/ImageModal";
import { getDescendantIds } from "@/utils/categories";
import { ChevronRight, ChevronDown, FolderOpen, FileSearch, Settings2, Tag, Layers, List, LayoutGrid } from "lucide-react";
import type { CategoryNode, ImageRecordWithLabels } from "@/api/types";

function flattenCategories(
  nodes: CategoryNode[],
  depth = 0,
): { id: number; label: string }[] {
  const result: { id: number; label: string }[] = [];
  for (const node of nodes) {
    result.push({ id: node.id, label: "\u00A0\u00A0".repeat(depth) + node.name });
    result.push(...flattenCategories(node.children, depth + 1));
  }
  return result;
}

function getStoredViewMode(): "list" | "gallery" {
  try {
    const stored = localStorage.getItem("images-view-mode");
    if (stored === "gallery") return "gallery";
  } catch {}
  return "list";
}

export default function ImagesPage() {
  const [folder, setFolder] = useState<string | undefined>(undefined);
  const [expandedHash, setExpandedHash] = useState<string | null>(null);
  const [selectedHashes, setSelectedHashes] = useState<Set<string>>(new Set());
  const [bulkTagId, setBulkTagId] = useState<string>("");
  const [bulkCategoryId, setBulkCategoryId] = useState<string>("");
  const [folderTagId, setFolderTagId] = useState<string>("");
  const [folderCategoryId, setFolderCategoryId] = useState<string>("");
  const [bulkTagDialogOpen, setBulkTagDialogOpen] = useState(false);
  const [bulkCategoryDialogOpen, setBulkCategoryDialogOpen] = useState(false);
  const [viewMode, setViewMode] = useState<"list" | "gallery">(getStoredViewMode);
  const [activeTags, setActiveTags] = useState<string[]>([]);
  const [activeCategoryId, setActiveCategoryId] = useState<number | null>(null);
  const [modalHash, setModalHash] = useState<string | null>(null);

  const { data: images, isLoading } = useImages(folder);
  const { data: folders } = useFolders();
  const { data: allTags } = useTags();
  const { data: allCategories } = useCategories();

  const openFile = useOpenFile();
  const revealFile = useRevealFile();
  const bulkAddTag = useBulkAddTag();
  const bulkRemoveTag = useBulkRemoveTag();
  const bulkAddCategory = useBulkAddCategory();
  const bulkRemoveCategory = useBulkRemoveCategory();
  const bulkFolderAddTag = useBulkFolderAddTag();
  const bulkFolderRemoveTag = useBulkFolderRemoveTag();
  const bulkFolderAddCategory = useBulkFolderAddCategory();
  const bulkFolderRemoveCategory = useBulkFolderRemoveCategory();

  const flatCategories = flattenCategories(allCategories ?? []);

  // Clear selection when folder changes
  useEffect(() => {
    setSelectedHashes(new Set());
  }, [folder]);

  // Persist view mode
  useEffect(() => {
    try { localStorage.setItem("images-view-mode", viewMode); } catch {}
  }, [viewMode]);

  // Compute filtered images (client-side AND-filter)
  const filteredImages: ImageRecordWithLabels[] = (images ?? []).filter((img) => {
    if (activeTags.length > 0) {
      const imageTagNames = img.tags.map((t) => t.name);
      if (!activeTags.every((name) => imageTagNames.includes(name))) return false;
    }
    if (activeCategoryId !== null) {
      const descendantIds = getDescendantIds(allCategories ?? [], activeCategoryId);
      const imageCategoryIds = img.categories.map((c) => c.id);
      if (!imageCategoryIds.some((id) => descendantIds.includes(id))) return false;
    }
    return true;
  });

  // Close modal when current image is filtered out
  useEffect(() => {
    if (modalHash && !filteredImages.find((img) => img.content_hash === modalHash)) {
      setModalHash(null);
    }
  }, [filteredImages, modalHash]);

  const toggleExpand = (hash: string) => {
    setExpandedHash((prev) => (prev === hash ? null : hash));
  };

  const allHashes = filteredImages.map((img) => img.content_hash);
  const allSelected = allHashes.length > 0 && allHashes.every((h) => selectedHashes.has(h));
  const someSelected = allHashes.some((h) => selectedHashes.has(h)) && !allSelected;

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelectedHashes(new Set());
    } else {
      setSelectedHashes(new Set(allHashes));
    }
  };

  const toggleSelect = (hash: string) => {
    setSelectedHashes((prev) => {
      const next = new Set(prev);
      if (next.has(hash)) {
        next.delete(hash);
      } else {
        next.add(hash);
      }
      return next;
    });
  };

  const selectedCount = selectedHashes.size;

  const handleTagToggle = (name: string) => {
    setActiveTags((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name],
    );
  };

  const handleCategoryToggle = (id: number) => {
    setActiveCategoryId((prev) => (prev === id ? null : id));
  };

  const handleClearFilters = () => {
    setActiveTags([]);
    setActiveCategoryId(null);
  };

  const handleBulkAddTag = () => {
    if (!bulkTagId) return;
    const tagId = parseInt(bulkTagId, 10);
    bulkAddTag.mutate(
      { content_hashes: Array.from(selectedHashes), tag_id: tagId },
      {
        onSuccess: (data) => toast.success(`Tag added to ${data.affected} images`),
        onError: () => toast.error("Failed to add tag"),
      },
    );
  };

  const handleBulkRemoveTag = () => {
    if (!bulkTagId) return;
    const tagId = parseInt(bulkTagId, 10);
    bulkRemoveTag.mutate(
      { content_hashes: Array.from(selectedHashes), tag_id: tagId },
      {
        onSuccess: (data) => toast.success(`Tag removed from ${data.affected} images`),
        onError: () => toast.error("Failed to remove tag"),
      },
    );
  };

  const handleBulkAddCategory = () => {
    if (!bulkCategoryId) return;
    const categoryId = parseInt(bulkCategoryId, 10);
    bulkAddCategory.mutate(
      { content_hashes: Array.from(selectedHashes), category_id: categoryId },
      {
        onSuccess: (data) => toast.success(`Category added to ${data.affected} images`),
        onError: () => toast.error("Failed to add category"),
      },
    );
  };

  const handleBulkRemoveCategory = () => {
    if (!bulkCategoryId) return;
    const categoryId = parseInt(bulkCategoryId, 10);
    bulkRemoveCategory.mutate(
      { content_hashes: Array.from(selectedHashes), category_id: categoryId },
      {
        onSuccess: (data) => toast.success(`Category removed from ${data.affected} images`),
        onError: () => toast.error("Failed to remove category"),
      },
    );
  };

  const handleFolderAddTag = () => {
    if (!folder || !folderTagId) return;
    const tagId = parseInt(folderTagId, 10);
    bulkFolderAddTag.mutate(
      { folder, tag_id: tagId },
      {
        onSuccess: (data) => toast.success(`Tag added to ${data.affected} images`),
        onError: () => toast.error("Failed to add tag to folder"),
      },
    );
  };

  const handleFolderRemoveTag = () => {
    if (!folder || !folderTagId) return;
    const tagId = parseInt(folderTagId, 10);
    bulkFolderRemoveTag.mutate(
      { folder, tag_id: tagId },
      {
        onSuccess: (data) => toast.success(`Tag removed from ${data.affected} images`),
        onError: () => toast.error("Failed to remove tag from folder"),
      },
    );
  };

  const handleFolderAddCategory = () => {
    if (!folder || !folderCategoryId) return;
    const categoryId = parseInt(folderCategoryId, 10);
    bulkFolderAddCategory.mutate(
      { folder, category_id: categoryId },
      {
        onSuccess: (data) => toast.success(`Category added to ${data.affected} images`),
        onError: () => toast.error("Failed to add category to folder"),
      },
    );
  };

  const handleFolderRemoveCategory = () => {
    if (!folder || !folderCategoryId) return;
    const categoryId = parseInt(folderCategoryId, 10);
    bulkFolderRemoveCategory.mutate(
      { folder, category_id: categoryId },
      {
        onSuccess: (data) => toast.success(`Category removed from ${data.affected} images`),
        onError: () => toast.error("Failed to remove category from folder"),
      },
    );
  };

  const modalImage = modalHash
    ? filteredImages.find((img) => img.content_hash === modalHash) ?? null
    : null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Images</h1>

      {/* Toolbar: folder filter + folder actions + view toggle */}
      <div className="flex items-center gap-3">
        <Select
          value={folder ?? "__all__"}
          onValueChange={(v) => setFolder(v === "__all__" || v == null ? undefined : v)}
        >
          <SelectTrigger className="w-64">
            <SelectValue placeholder="All folders" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">All folders</SelectItem>
            {(folders ?? []).map((f) => (
              <SelectItem key={f} value={f}>
                {f}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {images && (
          <span className="text-sm text-muted-foreground">
            {images.length} images
          </span>
        )}

        {folder && (
          <Dialog>
            <DialogTrigger
              render={
                <Button variant="outline" size="sm">
                  <Settings2 className="h-4 w-4 mr-2" />
                  Folder Actions
                </Button>
              }
            />
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Folder Actions: {folder}</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-2">
                {/* Folder tag actions */}
                <div className="space-y-2">
                  <p className="text-sm font-medium">Tags</p>
                  <div className="flex items-center gap-2">
                    <Select value={folderTagId} onValueChange={(v) => setFolderTagId(v ?? "")}>
                      <SelectTrigger className="flex-1">
                        <SelectValue placeholder="Select tag..." />
                      </SelectTrigger>
                      <SelectContent>
                        {(allTags ?? []).map((tag) => (
                          <SelectItem key={tag.id} value={String(tag.id)}>
                            {tag.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button size="sm" onClick={handleFolderAddTag} disabled={!folderTagId}>
                      Add
                    </Button>
                    <Button size="sm" variant="outline" onClick={handleFolderRemoveTag} disabled={!folderTagId}>
                      Remove
                    </Button>
                  </div>
                </div>

                {/* Folder category actions */}
                <div className="space-y-2">
                  <p className="text-sm font-medium">Categories</p>
                  <div className="flex items-center gap-2">
                    <Select value={folderCategoryId} onValueChange={(v) => setFolderCategoryId(v ?? "")}>
                      <SelectTrigger className="flex-1">
                        <SelectValue placeholder="Select category..." />
                      </SelectTrigger>
                      <SelectContent>
                        {flatCategories.map((cat) => (
                          <SelectItem key={cat.id} value={String(cat.id)}>
                            {cat.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button size="sm" onClick={handleFolderAddCategory} disabled={!folderCategoryId}>
                      Add
                    </Button>
                    <Button size="sm" variant="outline" onClick={handleFolderRemoveCategory} disabled={!folderCategoryId}>
                      Remove
                    </Button>
                  </div>
                </div>
              </div>
              <DialogFooter showCloseButton />
            </DialogContent>
          </Dialog>
        )}

        {/* Right side: bulk ops + view toggle */}
        <div className="ml-auto flex items-center gap-2">
          {selectedCount > 0 && (
            <span className="text-sm text-muted-foreground">{selectedCount} selected</span>
          )}

          {/* Bulk Tags dialog */}
          <Dialog open={bulkTagDialogOpen} onOpenChange={setBulkTagDialogOpen}>
            <DialogTrigger
              render={
                <Button variant="outline" size="sm" disabled={selectedCount === 0}>
                  <Tag className="h-4 w-4 mr-2" />
                  Bulk Tags
                </Button>
              }
            />
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Bulk Tags · {selectedCount} selected</DialogTitle>
              </DialogHeader>
              <div className="space-y-2 py-2">
                <div className="flex items-center gap-2">
                  <Select value={bulkTagId} onValueChange={(v) => setBulkTagId(v ?? "")}>
                    <SelectTrigger className="flex-1">
                      <SelectValue placeholder="Select tag..." />
                    </SelectTrigger>
                    <SelectContent>
                      {(allTags ?? []).map((tag) => (
                        <SelectItem key={tag.id} value={String(tag.id)}>
                          {tag.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button size="sm" onClick={handleBulkAddTag} disabled={!bulkTagId}>
                    Add
                  </Button>
                  <Button size="sm" variant="outline" onClick={handleBulkRemoveTag} disabled={!bulkTagId}>
                    Remove
                  </Button>
                </div>
              </div>
              <DialogFooter>
                <Button variant="ghost" size="sm" onClick={() => { setSelectedHashes(new Set()); setBulkTagDialogOpen(false); }}>
                  Clear Selection
                </Button>
                <Button variant="outline" size="sm" onClick={() => setBulkTagDialogOpen(false)}>
                  Close
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          {/* Bulk Categories dialog */}
          <Dialog open={bulkCategoryDialogOpen} onOpenChange={setBulkCategoryDialogOpen}>
            <DialogTrigger
              render={
                <Button variant="outline" size="sm" disabled={selectedCount === 0}>
                  <Layers className="h-4 w-4 mr-2" />
                  Bulk Categories
                </Button>
              }
            />
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Bulk Categories · {selectedCount} selected</DialogTitle>
              </DialogHeader>
              <div className="space-y-2 py-2">
                <div className="flex items-center gap-2">
                  <Select value={bulkCategoryId} onValueChange={(v) => setBulkCategoryId(v ?? "")}>
                    <SelectTrigger className="flex-1">
                      <SelectValue placeholder="Select category..." />
                    </SelectTrigger>
                    <SelectContent>
                      {flatCategories.map((cat) => (
                        <SelectItem key={cat.id} value={String(cat.id)}>
                          {cat.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button size="sm" onClick={handleBulkAddCategory} disabled={!bulkCategoryId}>
                    Add
                  </Button>
                  <Button size="sm" variant="outline" onClick={handleBulkRemoveCategory} disabled={!bulkCategoryId}>
                    Remove
                  </Button>
                </div>
              </div>
              <DialogFooter>
                <Button variant="ghost" size="sm" onClick={() => { setSelectedHashes(new Set()); setBulkCategoryDialogOpen(false); }}>
                  Clear Selection
                </Button>
                <Button variant="outline" size="sm" onClick={() => setBulkCategoryDialogOpen(false)}>
                  Close
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          {/* View toggle */}
          <div className="flex items-center border rounded-md overflow-hidden">
            <Button
              variant={viewMode === "list" ? "default" : "ghost"}
              size="sm"
              className="rounded-none"
              onClick={() => setViewMode("list")}
              title="List view"
            >
              <List className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === "gallery" ? "default" : "ghost"}
              size="sm"
              className="rounded-none"
              onClick={() => setViewMode("gallery")}
              title="Gallery view"
            >
              <LayoutGrid className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Filter bar (both modes) */}
      <FilterBar
        tags={allTags ?? []}
        categories={allCategories ?? []}
        activeTags={activeTags}
        activeCategoryId={activeCategoryId}
        onTagToggle={handleTagToggle}
        onCategoryToggle={handleCategoryToggle}
        onClear={handleClearFilters}
      />

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : viewMode === "gallery" ? (
        <>
          <GalleryGrid
            images={filteredImages}
            onOpen={(hash) => setModalHash(hash)}
            selectedHashes={selectedHashes}
            onSelect={toggleSelect}
          />
          {images && (
            <p className="text-sm text-muted-foreground text-center">
              Showing {filteredImages.length} of {images.length} images
              {(activeTags.length > 0 || activeCategoryId !== null) && " (filtered)"}
            </p>
          )}
        </>
      ) : (
        <Card>
          <CardContent className="p-0">
            {!images || images.length === 0 ? (
              <p className="text-sm text-muted-foreground p-4">No images indexed yet</p>
            ) : filteredImages.length === 0 ? (
              <p className="text-sm text-muted-foreground p-4">No images match the active filters.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-8">
                      <Checkbox
                        checked={allSelected}
                        indeterminate={someSelected}
                        onCheckedChange={toggleSelectAll}
                      />
                    </TableHead>
                    <TableHead className="w-8" />
                    <TableHead>Content Hash</TableHead>
                    <TableHead>Path</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Size</TableHead>
                    <TableHead className="w-20">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredImages.map((image) => (
                    <React.Fragment key={image.content_hash}>
                      <TableRow
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => toggleExpand(image.content_hash)}
                      >
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          <Checkbox
                            checked={selectedHashes.has(image.content_hash)}
                            onCheckedChange={() => toggleSelect(image.content_hash)}
                          />
                        </TableCell>
                        <TableCell>
                          {expandedHash === image.content_hash ? (
                            <ChevronDown className="h-4 w-4 text-muted-foreground" />
                          ) : (
                            <ChevronRight className="h-4 w-4 text-muted-foreground" />
                          )}
                        </TableCell>
                        <TableCell className="font-mono text-sm">
                          {image.content_hash.slice(0, 16)}...
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground max-w-xs truncate">
                          {image.canonical_path}
                        </TableCell>
                        <TableCell className="text-sm">{image.mime_type}</TableCell>
                        <TableCell className="text-sm">
                          {image.width}x{image.height}
                        </TableCell>
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              title="Open file"
                              onClick={() =>
                                openFile.mutate(
                                  { path: image.canonical_path },
                                  { onError: () => toast.error("Failed to open file") },
                                )
                              }
                            >
                              <FileSearch className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              title="Reveal in finder"
                              onClick={() =>
                                revealFile.mutate(
                                  { path: image.canonical_path },
                                  { onError: () => toast.error("Failed to reveal file") },
                                )
                              }
                            >
                              <FolderOpen className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                      {expandedHash === image.content_hash && (
                        <TableRow>
                          <TableCell colSpan={7} className="bg-muted/30 p-0">
                            <ImageTagEditor contentHash={image.content_hash} />
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

      {/* Image modal (gallery mode) */}
      <ImageModal
        image={modalImage}
        images={filteredImages}
        open={modalHash !== null}
        onClose={() => setModalHash(null)}
        onNavigate={(hash) => setModalHash(hash)}
      />
    </div>
  );
}
