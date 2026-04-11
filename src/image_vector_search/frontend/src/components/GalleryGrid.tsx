import type { ReactNode } from "react";
import { ImageOff } from "lucide-react";
import GalleryCard from "./GalleryCard";
import type { ImageRecordWithLabels } from "@/api/types";

interface Props {
  images: ImageRecordWithLabels[];
  onOpen: (hash: string) => void;
  selectedHashes?: Set<string>;
  onSelect?: (hash: string) => void;
  renderStatusBadge: (image: ImageRecordWithLabels) => ReactNode;
  renderAction?: (image: ImageRecordWithLabels) => ReactNode;
}

export default function GalleryGrid({
  images,
  onOpen,
  selectedHashes,
  onSelect,
  renderStatusBadge,
  renderAction,
}: Props) {
  if (images.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
        <ImageOff className="h-12 w-12 mb-3 opacity-40" />
        <p className="text-sm">No images match the active filters.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 min-[560px]:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5">
      {images.map((image) => (
        <GalleryCard
          key={image.content_hash}
          image={image}
          onOpen={onOpen}
          selected={selectedHashes?.has(image.content_hash)}
          onSelect={onSelect}
          statusBadge={renderStatusBadge(image)}
          action={renderAction?.(image)}
        />
      ))}
    </div>
  );
}
