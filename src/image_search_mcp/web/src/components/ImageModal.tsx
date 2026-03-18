import { toast } from "sonner";
import { ChevronLeft, ChevronRight, FileSearch, FolderOpen } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import ImageTagEditor from "@/components/ImageTagEditor";
import { useOpenFile, useRevealFile } from "@/api/bulk";
import type { ImageRecordWithLabels } from "@/api/types";

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

  if (!image) return null;

  const currentIndex = images.findIndex((img) => img.content_hash === image.content_hash);
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < images.length - 1;

  const filename = image.canonical_path.split("/").pop() ?? image.canonical_path;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) onClose(); }}>
      <DialogContent
        className="max-w-5xl w-full p-0 overflow-hidden"
        showCloseButton
      >
        <div className="flex h-[80vh]">
          {/* Left: image */}
          <div className="flex-1 bg-black flex items-center justify-center min-w-0">
            <img
              src={`/api/images/${image.content_hash}/thumbnail?size=500`}
              alt={filename}
              className="max-w-full max-h-full object-contain"
            />
          </div>

          {/* Right: metadata + editor */}
          <div className="w-80 flex flex-col border-l overflow-y-auto">
            <DialogHeader className="p-4 border-b">
              <DialogTitle className="text-sm font-medium truncate" title={filename}>
                {filename}
              </DialogTitle>
              <p className="text-xs text-muted-foreground font-mono truncate">
                {image.content_hash.slice(0, 16)}…
              </p>
            </DialogHeader>

            <div className="p-2 border-b">
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1 text-xs"
                  onClick={() =>
                    openFile.mutate(
                      { path: image.canonical_path },
                      { onError: () => toast.error("Failed to open file") },
                    )
                  }
                >
                  <FileSearch className="h-3 w-3 mr-1" />
                  Open File
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1 text-xs"
                  onClick={() =>
                    revealFile.mutate(
                      { path: image.canonical_path },
                      { onError: () => toast.error("Failed to reveal file") },
                    )
                  }
                >
                  <FolderOpen className="h-3 w-3 mr-1" />
                  Reveal
                </Button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto">
              <ImageTagEditor contentHash={image.content_hash} />
            </div>

            {/* Navigation */}
            <div className="p-2 border-t flex items-center justify-between">
              <Button
                variant="ghost"
                size="sm"
                disabled={!hasPrev}
                onClick={() => hasPrev && onNavigate(images[currentIndex - 1].content_hash)}
              >
                <ChevronLeft className="h-4 w-4" />
                Prev
              </Button>
              <span className="text-xs text-muted-foreground">
                {currentIndex + 1} / {images.length}
              </span>
              <Button
                variant="ghost"
                size="sm"
                disabled={!hasNext}
                onClick={() => hasNext && onNavigate(images[currentIndex + 1].content_hash)}
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
