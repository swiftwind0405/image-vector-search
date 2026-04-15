import { useEffect, useCallback, useMemo } from "react";
import { toast } from "sonner";
import { ChevronLeft, ChevronRight, FileSearch, FolderOpen, Images, X, Info } from "lucide-react";
import { Dialog as DialogPrimitive } from "@base-ui/react/dialog";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import ImageInfoPanel from "@/components/ImageInfoPanel";
import { useAddImagesToAlbum, useListAlbums } from "@/api/albums";
import { useOpenFile, useRevealFile } from "@/api/bulk";
import type { Album, ImageRecordWithLabels } from "@/api/types";
import { useState } from "react";

interface Props {
  image: ImageRecordWithLabels | null;
  images: ImageRecordWithLabels[];
  open: boolean;
  onClose: () => void;
  onNavigate: (hash: string) => void;
}

export default function ImageModal({ image, images, open, onClose, onNavigate }: Props) {
  const openFile = useOpenFile();
  const revealFile = useRevealFile();
  const [showInfo, setShowInfo] = useState(true);

  const currentIndex = image
    ? images.findIndex((img) => img.content_hash === image.content_hash)
    : -1;
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < images.length - 1;

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!open || !image) return;
      const target = e.target;
      const isEditableTarget =
        target instanceof HTMLElement &&
        (target.isContentEditable ||
          target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.tagName === "SELECT");

      if (e.key === "ArrowLeft" && hasPrev) {
        if (isEditableTarget) return;
        e.preventDefault();
        onNavigate(images[currentIndex - 1].content_hash);
      } else if (e.key === "ArrowRight" && hasNext) {
        if (isEditableTarget) return;
        e.preventDefault();
        onNavigate(images[currentIndex + 1].content_hash);
      } else if (e.key === "Escape") {
        onClose();
      } else if (e.key.toLowerCase() === "i" && e.shiftKey) {
        if (isEditableTarget) return;
        e.preventDefault();
        setShowInfo((v) => !v);
      }
    },
    [open, image, hasPrev, hasNext, currentIndex, images, onNavigate, onClose],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown, { capture: true });
    return () => window.removeEventListener("keydown", handleKeyDown, { capture: true });
  }, [handleKeyDown]);

  if (!image) return null;

  const filename = image.canonical_path.split("/").pop() ?? image.canonical_path;
  const imageSrc = image.file_url ?? `/api/images/${image.content_hash}/file`;

  return (
    <DialogPrimitive.Root open={open} onOpenChange={(isOpen) => { if (!isOpen) onClose(); }}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Backdrop
          className="fixed inset-0 z-50 bg-black/10 supports-backdrop-filter:backdrop-blur-xs data-open:animate-in data-open:fade-in-0 data-closed:animate-out data-closed:fade-out-0"
        />
        <DialogPrimitive.Popup
          className="fixed inset-0 z-50 flex bg-background text-foreground outline-none data-open:animate-in data-open:fade-in-0 data-closed:animate-out data-closed:fade-out-0"
        >
          {/* Top bar */}
          <div className="absolute left-0 right-0 top-0 z-10 flex h-16 items-center justify-between border-b border-border bg-background/90 px-4 backdrop-blur">
            <div className="flex items-center gap-3 min-w-0">
              <Button
                variant="ghost"
                size="icon"
                className="shrink-0"
                onClick={onClose}
              >
                <X className="h-5 w-5" />
              </Button>
              <span className="text-sm text-foreground truncate" title={filename}>
                {filename}
              </span>
              <span className="text-xs text-muted-foreground">
                {currentIndex + 1} / {images.length}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <AddToAlbumsButton contentHash={image.content_hash} />
              <Button
                variant="ghost"
                size="icon"
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
              <Button
                variant="ghost"
                size="icon"
                className={cn(showInfo && "bg-accent text-accent-foreground")}
                title="Toggle info panel (Shift+I)"
                onClick={() => setShowInfo((v) => !v)}
              >
                <Info className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Main area: image + optional info panel */}
          {/* Desktop: row (image left, info right) / Mobile: column (image top, info bottom) */}
          <div className="flex h-full w-full flex-col overflow-hidden pt-16 md:flex-row">
            <div className="relative flex min-h-0 min-w-0 flex-1 items-center justify-center overflow-hidden bg-muted/40">
              <img
                src={imageSrc}
                alt={filename}
                className="h-full w-full object-contain p-5"
              />

              {/* Prev / Next arrows */}
              {hasPrev && (
                <button
                  className="absolute left-4 top-1/2 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full border border-border bg-background/85 text-foreground shadow-sm transition-colors hover:bg-background"
                  onClick={() => onNavigate(images[currentIndex - 1].content_hash)}
                >
                  <ChevronLeft className="h-5 w-5" />
                </button>
              )}
              {hasNext && (
                <button
                  className="absolute right-4 top-1/2 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full border border-border bg-background/85 text-foreground shadow-sm transition-colors hover:bg-background"
                  onClick={() => onNavigate(images[currentIndex + 1].content_hash)}
                >
                  <ChevronRight className="h-5 w-5" />
                </button>
              )}
            </div>

            <div
              className={cn(
                "overflow-y-auto border-border bg-card transition-all duration-200",
                "md:h-full md:border-l",
                "max-md:border-t max-md:w-full",
                showInfo
                  ? "md:w-80 max-md:max-h-[40vh] max-md:min-h-[120px]"
                  : "md:w-0 md:border-l-0 max-md:max-h-0 max-md:min-h-0 max-md:border-t-0",
              )}
            >
              {showInfo && (
                <div className="md:w-80 w-full h-full">
                  <ImageInfoPanel image={image} />
                </div>
              )}
            </div>
          </div>
        </DialogPrimitive.Popup>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

function AddToAlbumsButton({ contentHash }: { contentHash: string }) {
  const { data: albums, isLoading } = useListAlbums();
  const addImagesToAlbum = useAddImagesToAlbum();
  const [open, setOpen] = useState(false);
  const [selectedAlbumIds, setSelectedAlbumIds] = useState<number[]>([]);

  const manualAlbums = useMemo(
    () => (albums ?? []).filter((album): album is Album => album.type === "manual"),
    [albums],
  );

  useEffect(() => {
    if (!open) {
      setSelectedAlbumIds([]);
    }
  }, [open]);

  useEffect(() => {
    setSelectedAlbumIds([]);
  }, [contentHash]);

  function toggleAlbum(albumId: number, selected: boolean) {
    setSelectedAlbumIds((current) =>
      selected
        ? Array.from(new Set([...current, albumId]))
        : current.filter((selectedAlbumId) => selectedAlbumId !== albumId),
    );
  }

  async function handleSubmit() {
    if (selectedAlbumIds.length === 0) return;

    try {
      await Promise.all(
        selectedAlbumIds.map((albumId) =>
          addImagesToAlbum.mutateAsync({
            albumId,
            contentHashes: [contentHash],
          }),
        ),
      );
      toast.success(
        selectedAlbumIds.length === 1
          ? "Image added to album"
          : `Image added to ${selectedAlbumIds.length} albums`,
      );
      setOpen(false);
    } catch {
      toast.error("Failed to add image to albums");
    }
  }

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="icon"
        aria-expanded={open}
        aria-label="Add to albums"
        title="Add to albums"
        onClick={() => setOpen((value) => !value)}
      >
        <Images className="h-4 w-4" />
      </Button>

      {open && (
        <div
          className="absolute right-0 top-10 z-20 w-72 rounded-lg border border-border bg-popover p-3 text-popover-foreground shadow-lg"
          role="dialog"
          aria-label="Add to albums"
        >
          <div className="mb-3">
            <p className="text-sm font-medium">Add to albums</p>
            <p className="text-xs text-muted-foreground">Manual albums only.</p>
          </div>

          <div className="max-h-64 space-y-1 overflow-y-auto">
            {isLoading ? (
              <p className="py-2 text-sm text-muted-foreground">Loading albums...</p>
            ) : manualAlbums.length === 0 ? (
              <p className="py-2 text-sm text-muted-foreground">No manual albums yet.</p>
            ) : (
              manualAlbums.map((album) => (
                <label
                  key={album.id}
                  className="flex cursor-pointer items-start gap-3 rounded-md px-2 py-2 hover:bg-muted"
                >
                  <Checkbox
                    aria-label={album.name}
                    checked={selectedAlbumIds.includes(album.id)}
                    onCheckedChange={(checked) => toggleAlbum(album.id, checked === true)}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm text-foreground">{album.name}</span>
                    <span className="text-xs text-muted-foreground">
                      {album.image_count ?? 0} images
                    </span>
                  </span>
                </label>
              ))
            )}
          </div>

          <div className="mt-3 flex items-center justify-end gap-2 border-t border-border pt-3">
            <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={selectedAlbumIds.length === 0 || addImagesToAlbum.isPending}
              onClick={handleSubmit}
            >
              {selectedAlbumIds.length <= 1
                ? "Add to album"
                : `Add to ${selectedAlbumIds.length} albums`}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
