import React, { useEffect, useMemo, useRef, useState } from "react";
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
import { Badge } from "@/components/ui/badge";
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
import {
  useForceEmbedImages,
  useImages,
  useImagesInfinite,
} from "@/api/images";
import {
  useFolders,
  useOpenFile,
  useRevealFile,
  useBulkAddTag,
  useBulkRemoveTag,
  useBulkFolderAddTag,
  useBulkFolderRemoveTag,
} from "@/api/bulk";
import { useTags } from "@/api/tags";
import { useCreateTag } from "@/api/tags";
import ImageTagEditor from "@/components/ImageTagEditor";
import FilterBar from "@/components/FilterBar";
import GalleryGrid from "@/components/GalleryGrid";
import ImageModal from "@/components/ImageModal";
import TagSelect from "@/components/TagSelect";
import {
  ChevronRight,
  ChevronDown,
  FolderOpen,
  FileSearch,
  Settings2,
  Tag,
  List,
  LayoutGrid,
} from "lucide-react";
import type { ImageRecordWithLabels } from "@/api/types";

interface ImageBrowserProps {
  title: string;
  subtitle?: React.ReactNode;
  breadcrumb?: React.ReactNode;
  hideTitle?: boolean;
  queryScope?: {
    tagId?: number;
  };
  emptyMessage?: string;
  includeAllImages?: boolean;
}

function getStoredViewMode(): "list" | "gallery" {
  try {
    const stored = localStorage.getItem("images-view-mode");
    if (stored === "gallery") return "gallery";
  } catch {}
  return "list";
}

export default function ImageBrowser({
  title,
  subtitle,
  breadcrumb,
  hideTitle,
  queryScope,
  emptyMessage = "No images indexed yet",
  includeAllImages = false,
}: ImageBrowserProps) {
  const [folder, setFolder] = useState<string | undefined>(undefined);
  const [embeddingStatus, setEmbeddingStatus] = useState<string>("all");
  const [expandedHash, setExpandedHash] = useState<string | null>(null);
  const [selectedHashes, setSelectedHashes] = useState<Set<string>>(new Set());
  const [bulkTagId, setBulkTagId] = useState<string>("");
  const [folderTagId, setFolderTagId] = useState<string>("");
  const [bulkTagDialogOpen, setBulkTagDialogOpen] = useState(false);
  const [viewMode, setViewMode] = useState<"list" | "gallery">(getStoredViewMode);
  const [activeTags, setActiveTags] = useState<string[]>([]);
  const [modalHash, setModalHash] = useState<string | null>(null);
  const loadMoreRef = useRef<HTMLDivElement | null>(null);

  const imageQueryOptions = {
    folder,
    tagId: queryScope?.tagId,
    includeInactive: includeAllImages,
    embeddingStatus: embeddingStatus === "all" ? undefined : embeddingStatus,
  };
  const standardImagesQuery = useImages(imageQueryOptions);
  const infiniteImagesQuery = useImagesInfinite({
    ...imageQueryOptions,
    limit: 200,
  });
  const images = includeAllImages
    ? (infiniteImagesQuery.data?.pages.flatMap((page) => page.items) ?? [])
    : (standardImagesQuery.data ?? []);
  const isLoading = includeAllImages
    ? infiniteImagesQuery.isLoading
    : standardImagesQuery.isLoading;
  const { data: folders } = useFolders();
  const { data: allTags } = useTags();
  const createTag = useCreateTag();

  const openFile = useOpenFile();
  const revealFile = useRevealFile();
  const bulkAddTag = useBulkAddTag();
  const bulkRemoveTag = useBulkRemoveTag();
  const bulkFolderAddTag = useBulkFolderAddTag();
  const bulkFolderRemoveTag = useBulkFolderRemoveTag();
  const forceEmbedImages = useForceEmbedImages();

  useEffect(() => {
    setSelectedHashes(new Set());
    setExpandedHash(null);
  }, [
    folder,
    embeddingStatus,
    queryScope?.tagId,
  ]);

  useEffect(() => {
    try {
      localStorage.setItem("images-view-mode", viewMode);
    } catch {}
  }, [viewMode]);

  const filteredImages: ImageRecordWithLabels[] = (images ?? []).filter((img) => {
    if (activeTags.length > 0) {
      const imageTagNames = img.tags.map((t) => t.name);
      if (!activeTags.every((name) => imageTagNames.includes(name))) return false;
    }
    return true;
  });

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

  const handleClearFilters = () => {
    setActiveTags([]);
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

  const handleCreateTagOption = async (name: string) => {
    const created = await createTag.mutateAsync(name);
    const createdId = String(created.id);
    setBulkTagId(createdId);
    setFolderTagId(createdId);
    return createdId;
  };

  const modalImage = modalHash
    ? filteredImages.find((img) => img.content_hash === modalHash) ?? null
    : null;
  const eligibleSelectedHashes = useMemo(
    () =>
      filteredImages
        .filter(
          (img) =>
            selectedHashes.has(img.content_hash) &&
            img.embedding_status !== "embedded",
        )
        .map((img) => img.content_hash),
    [filteredImages, selectedHashes],
  );

  useEffect(() => {
    if (!includeAllImages) {
      return;
    }
    const node = loadMoreRef.current;
    if (!node) {
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      if (
        entries.some((entry) => entry.isIntersecting) &&
        infiniteImagesQuery.hasNextPage &&
        !infiniteImagesQuery.isFetchingNextPage
      ) {
        infiniteImagesQuery.fetchNextPage();
      }
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [
    includeAllImages,
    infiniteImagesQuery,
    filteredImages.length,
  ]);

  const formatFileSizeMb = (bytes: number) => `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  const renderStatusBadge = (image: ImageRecordWithLabels) => {
    if (image.embedding_status === "embedded") {
      return <span className="text-emerald-200">已向量化</span>;
    }
    if (image.embedding_status === "skipped_oversized") {
      return <span className="text-amber-200">超大 ({formatFileSizeMb(image.file_size)})</span>;
    }
    if (image.embedding_status === "failed") {
      return <span className="text-rose-200">嵌入失败</span>;
    }
    return <span className="text-zinc-200">待处理</span>;
  };

  const handleForceEmbed = (contentHashes: string[]) => {
    if (contentHashes.length === 0) {
      return;
    }
    forceEmbedImages.mutate(
      { content_hashes: contentHashes },
      {
        onSuccess: () => {
          toast.success(`已提交 ${contentHashes.length} 张图片的向量化任务`);
        },
        onError: () => {
          toast.error("提交向量化任务失败");
        },
      },
    );
  };

  const renderForceEmbedAction = (image: ImageRecordWithLabels) => {
    if (image.embedding_status !== "skipped_oversized" && image.embedding_status !== "failed") {
      return null;
    }
    return (
      <Button
        variant="outline"
        size="sm"
        className="h-7 rounded-full border-0 bg-black/50 px-2 text-[11px] text-white hover:bg-black/70"
        onClick={(event) => {
          event.stopPropagation();
          handleForceEmbed([image.content_hash]);
        }}
      >
        重新向量化
      </Button>
    );
  };

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        {breadcrumb}
        {!hideTitle && title && <h1 className="text-2xl font-semibold text-foreground">{title}</h1>}
        {subtitle ? <div className="text-sm text-muted-foreground">{subtitle}</div> : null}
      </div>

      <div className="rounded-lg border border-border bg-card p-4">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center">
        <Select
          value={folder ?? "All folders"}
          onValueChange={(v) => setFolder(v === "All folders" || v == null ? undefined : v)}
        >
          <SelectTrigger className="w-full rounded-md border-border bg-[#f9f9fa] xl:w-64">
            <SelectValue placeholder="All folders" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="All folders">All folders</SelectItem>
            {(folders ?? []).map((f) => (
              <SelectItem key={f} value={f}>
                {f}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {includeAllImages && (
          <Select
            value={embeddingStatus}
            onValueChange={(value) => setEmbeddingStatus(value ?? "all")}
          >
            <SelectTrigger className="w-full rounded-md border-border bg-[#f9f9fa] xl:w-56">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部状态</SelectItem>
              <SelectItem value="embedded">已向量化</SelectItem>
              <SelectItem value="skipped_oversized">超大</SelectItem>
              <SelectItem value="failed">嵌入失败</SelectItem>
              <SelectItem value="pending">待处理</SelectItem>
            </SelectContent>
          </Select>
        )}

        {images && (
          <span className="text-sm text-muted-foreground">
            {images.length} images
          </span>
        )}

        {folder && (
          <Dialog>
            <DialogTrigger
              render={
                <Button variant="outline" size="sm" className="rounded-md border-border bg-[#f9f9fa] text-foreground hover:bg-[#f1f1f3]">
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
                <div className="space-y-2">
                  <p className="text-sm font-medium">Tags</p>
                  <div className="flex items-center gap-2">
                    <TagSelect
                      tags={allTags ?? []}
                      value={folderTagId}
                      onValueChange={setFolderTagId}
                      onCreate={handleCreateTagOption}
                      triggerClassName="flex-1"
                      creating={createTag.isPending}
                    />
                    <Button size="sm" onClick={handleFolderAddTag} disabled={!folderTagId}>
                      Add
                    </Button>
                    <Button size="sm" variant="outline" onClick={handleFolderRemoveTag} disabled={!folderTagId}>
                      Remove
                    </Button>
                  </div>
                </div>
              </div>
              <DialogFooter showCloseButton />
            </DialogContent>
          </Dialog>
        )}

        <div className="ml-auto flex flex-wrap items-center gap-2">
          {selectedCount > 0 && (
            <span className="text-sm text-muted-foreground">{selectedCount} selected</span>
          )}

          {includeAllImages && (
            <>
              <Button
                variant="outline"
                size="sm"
                disabled={eligibleSelectedHashes.length === 0 || forceEmbedImages.isPending}
                className="rounded-md border-border bg-[#f9f9fa] text-foreground hover:bg-[#f1f1f3]"
                onClick={() => handleForceEmbed(eligibleSelectedHashes)}
              >
                强制向量化
              </Button>
              {selectedCount > 0 && (
                <span className="text-xs text-muted-foreground">
                  无限滚动下“全选”仅包含当前已加载结果
                </span>
              )}
            </>
          )}

          <Dialog open={bulkTagDialogOpen} onOpenChange={setBulkTagDialogOpen}>
            <DialogTrigger
              render={
                <Button variant="outline" size="sm" disabled={selectedCount === 0} className="rounded-md border-border bg-[#f9f9fa] text-foreground hover:bg-[#f1f1f3]">
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
                  <TagSelect
                    tags={allTags ?? []}
                    value={bulkTagId}
                    onValueChange={setBulkTagId}
                    onCreate={handleCreateTagOption}
                    triggerClassName="flex-1"
                    creating={createTag.isPending}
                  />
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

          <div className="flex items-center overflow-hidden rounded-md border border-border bg-[#f9f9fa]">
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
      </div>

      <FilterBar
        tags={allTags ?? []}
        activeTags={activeTags}
        onTagToggle={handleTagToggle}
        onClear={handleClearFilters}
      />

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : viewMode === "gallery" ? (
        <>
          {filteredImages.length === 0 ? (
            <Card className="rounded-lg border-border bg-card">
              <CardContent className="p-5">
                <p className="text-sm text-muted-foreground">
                  {!images || images.length === 0 ? emptyMessage : "No images match the active filters."}
                </p>
              </CardContent>
            </Card>
          ) : (
            <>
              <GalleryGrid
                images={filteredImages}
                onOpen={(hash) => setModalHash(hash)}
                selectedHashes={selectedHashes}
                onSelect={toggleSelect}
                renderStatusBadge={renderStatusBadge}
                renderAction={renderForceEmbedAction}
              />
              <div className="flex items-center justify-between pt-2">
                <p className="text-sm text-muted-foreground">
                  {filteredImages.length} images{activeTags.length > 0 && " (filtered)"}
                  {images && filteredImages.length !== images.length && ` of ${images.length} total`}
                </p>
              </div>
            </>
          )}
        </>
      ) : (
        <Card className="rounded-lg border-border bg-card">
          <CardContent className="p-0">
            {!images || images.length === 0 ? (
              <p className="text-sm text-muted-foreground p-4">{emptyMessage}</p>
            ) : filteredImages.length === 0 ? (
              <p className="text-sm text-muted-foreground p-4">No images match the active filters.</p>
            ) : (
              <>
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
                          className="cursor-pointer hover:bg-[#f9f9fa]"
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
                          <TableCell className="text-sm">
                            <div className="space-y-1">
                              <div>{image.mime_type}</div>
                              <Badge variant="outline" className="border-border bg-[#f9f9fa]">
                                {renderStatusBadge(image)}
                              </Badge>
                            </div>
                          </TableCell>
                          <TableCell className="text-sm">
                            <div className="space-y-1">
                              <div>{image.width}x{image.height}</div>
                              {!image.is_active && (
                                <div className="text-xs text-amber-300">inactive</div>
                              )}
                            </div>
                          </TableCell>
                          <TableCell onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center gap-1">
                              {renderForceEmbedAction(image)}
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
                            <TableCell colSpan={7} className="bg-[#fbfbfc] p-0">
                              <ImageTagEditor contentHash={image.content_hash} />
                            </TableCell>
                          </TableRow>
                        )}
                      </React.Fragment>
                    ))}
                  </TableBody>
                </Table>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {includeAllImages && (
        <div ref={loadMoreRef} className="flex min-h-10 items-center justify-center">
          {infiniteImagesQuery.isFetchingNextPage ? (
            <p className="text-sm text-muted-foreground">Loading more images...</p>
          ) : infiniteImagesQuery.hasNextPage ? (
            <p className="text-sm text-muted-foreground">Scroll to load more</p>
          ) : (
            <p className="text-sm text-muted-foreground">已加载全部</p>
          )}
        </div>
      )}

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
