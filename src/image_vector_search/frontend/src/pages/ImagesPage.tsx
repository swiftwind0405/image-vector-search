import { useMemo, useState } from "react";
import type { ImageRecordWithLabels } from "@/api/types";
import { useFilesystemImages } from "@/api/images";
import GalleryGrid from "@/components/GalleryGrid";
import ImageModal from "@/components/ImageModal";

export default function ImagesPage() {
  const { data, isLoading, error } = useFilesystemImages();
  const [modalHash, setModalHash] = useState<string | null>(null);

  const images = useMemo<ImageRecordWithLabels[]>(
    () =>
      (data?.items ?? []).map((image) => ({
        ...image,
        tags: image.tags ?? [],
      })),
    [data?.items],
  );

  const activeImage = images.find((image) => image.content_hash === modalHash) ?? null;

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <div
            key={index}
            className="h-48 animate-pulse rounded-lg border border-border bg-[#f7f7f8]"
          />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-[#fbd5d5] bg-[#fef2f2] px-5 py-4 text-sm text-[#9b2c2c]">
        Failed to load filesystem images.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium uppercase tracking-[0.08em] text-muted-foreground">
          All Photos
        </h3>
        <p className="text-xs text-muted-foreground">{images.length} visible</p>
      </div>
      <GalleryGrid
        images={images}
        onOpen={setModalHash}
        renderStatusBadge={(image) => (image.indexed ?? true ? "Indexed" : "Unindexed")}
      />
      <ImageModal
        image={activeImage}
        images={images}
        open={activeImage !== null}
        onClose={() => setModalHash(null)}
        onNavigate={setModalHash}
      />
    </div>
  );
}
