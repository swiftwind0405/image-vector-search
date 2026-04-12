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
        categories: image.categories ?? [],
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
            className="h-48 animate-pulse rounded-[24px] border border-white/10 bg-white/[0.04]"
          />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-[28px] border border-rose-400/20 bg-rose-500/10 px-5 py-4 text-sm text-rose-100">
        Failed to load filesystem images.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium uppercase tracking-[0.22em] text-muted-foreground">
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
