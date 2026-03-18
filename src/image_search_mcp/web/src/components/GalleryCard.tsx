import { useState } from "react";
import { ImageOff } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { ImageRecordWithLabels } from "@/api/types";

interface Props {
  image: ImageRecordWithLabels;
  onOpen: (hash: string) => void;
}

export default function GalleryCard({ image, onOpen }: Props) {
  const [imgError, setImgError] = useState(false);
  const filename = image.canonical_path.split("/").pop() ?? image.canonical_path;

  return (
    <div
      className="cursor-pointer rounded-lg overflow-hidden border border-border hover:border-primary/50 transition-colors group"
      onClick={() => onOpen(image.content_hash)}
    >
      <div className="relative h-[90px] bg-[#1a2233] flex items-center justify-center">
        {imgError ? (
          <ImageOff className="h-6 w-6 text-muted-foreground" />
        ) : (
          <img
            src={`/api/images/${image.content_hash}/thumbnail`}
            alt={filename}
            className="w-full h-full object-cover"
            onError={() => setImgError(true)}
          />
        )}
      </div>
      <div className="p-1.5 space-y-1">
        <p className="text-xs text-muted-foreground truncate" title={filename}>
          {filename}
        </p>
        {image.tags.length > 0 && (
          <div className="flex flex-wrap gap-0.5">
            {image.tags.slice(0, 3).map((tag) => (
              <Badge key={tag.id} variant="secondary" className="text-[10px] px-1 py-0">
                {tag.name}
              </Badge>
            ))}
            {image.tags.length > 3 && (
              <span className="text-[10px] text-muted-foreground">+{image.tags.length - 3}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
