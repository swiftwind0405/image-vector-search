import GalleryCard from "./GalleryCard";
import type { ImageRecordWithLabels } from "@/api/types";

interface Props {
  images: ImageRecordWithLabels[];
  onOpen: (hash: string) => void;
}

export default function GalleryGrid({ images, onOpen }: Props) {
  if (images.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-12">
        No images match the active filters.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-6 gap-2">
      {images.map((image) => (
        <GalleryCard key={image.content_hash} image={image} onOpen={onOpen} />
      ))}
    </div>
  );
}
