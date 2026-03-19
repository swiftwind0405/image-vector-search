import { useEffect, useCallback } from "react";
import { toast } from "sonner";
import { ChevronLeft, ChevronRight, FileSearch, FolderOpen, X, Info } from "lucide-react";
import { Dialog as DialogPrimitive } from "@base-ui/react/dialog";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import ImageInfoPanel from "@/components/ImageInfoPanel";
import { useOpenFile, useRevealFile } from "@/api/bulk";
import type { ImageRecordWithLabels } from "@/api/types";
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
      if (e.key === "ArrowLeft" && hasPrev) {
        onNavigate(images[currentIndex - 1].content_hash);
      } else if (e.key === "ArrowRight" && hasNext) {
        onNavigate(images[currentIndex + 1].content_hash);
      } else if (e.key === "Escape") {
        onClose();
      } else if (e.key === "i") {
        setShowInfo((v) => !v);
      }
    },
    [open, image, hasPrev, hasNext, currentIndex, images, onNavigate, onClose],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  if (!image) return null;

  const filename = image.canonical_path.split("/").pop() ?? image.canonical_path;

  return (
    <DialogPrimitive.Root open={open} onOpenChange={(isOpen) => { if (!isOpen) onClose(); }}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Backdrop
          className="fixed inset-0 z-50 bg-black/90 data-open:animate-in data-open:fade-in-0 data-closed:animate-out data-closed:fade-out-0"
        />
        <DialogPrimitive.Popup
          className="fixed inset-0 z-50 flex outline-none data-open:animate-in data-open:fade-in-0 data-closed:animate-out data-closed:fade-out-0"
        >
          {/* Top bar */}
          <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between px-4 h-14 bg-gradient-to-b from-black/60 to-transparent">
            <div className="flex items-center gap-3 min-w-0">
              <Button
                variant="ghost"
                size="icon"
                className="text-white hover:bg-white/10 shrink-0"
                onClick={onClose}
              >
                <X className="h-5 w-5" />
              </Button>
              <span className="text-sm text-white/90 truncate" title={filename}>
                {filename}
              </span>
              <span className="text-xs text-white/50">
                {currentIndex + 1} / {images.length}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="text-white hover:bg-white/10"
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
                className="text-white hover:bg-white/10"
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
                className={cn("text-white hover:bg-white/10", showInfo && "bg-white/15")}
                title="Toggle info panel (i)"
                onClick={() => setShowInfo((v) => !v)}
              >
                <Info className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Main area: image + optional info panel */}
          {/* Desktop: row (image left, info right) / Mobile: column (image top, info bottom) */}
          <div className="flex flex-col md:flex-row w-full h-full pt-14 overflow-hidden">
            {/* Image area */}
            <div className="relative flex-1 flex items-center justify-center min-w-0 min-h-0 overflow-hidden">
              <img
                src={`/api/images/${image.content_hash}/file`}
                alt={filename}
                className="w-full h-full object-contain p-4"
              />

              {/* Prev / Next arrows */}
              {hasPrev && (
                <button
                  className="absolute left-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/40 hover:bg-black/60 flex items-center justify-center text-white transition-colors"
                  onClick={() => onNavigate(images[currentIndex - 1].content_hash)}
                >
                  <ChevronLeft className="h-5 w-5" />
                </button>
              )}
              {hasNext && (
                <button
                  className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/40 hover:bg-black/60 flex items-center justify-center text-white transition-colors"
                  onClick={() => onNavigate(images[currentIndex + 1].content_hash)}
                >
                  <ChevronRight className="h-5 w-5" />
                </button>
              )}
            </div>

            {/* Info panel: desktop = side panel (right), mobile = bottom panel */}
            <div
              className={cn(
                "bg-background overflow-y-auto transition-all duration-200",
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
