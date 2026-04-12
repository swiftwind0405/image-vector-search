import { useState, type ReactNode } from "react";
import { ImageOff, Check } from "lucide-react";
import type { ImageRecordWithLabels } from "@/api/types";
import { Badge } from "@/components/ui/badge";

interface Props {
  image: ImageRecordWithLabels;
  onOpen: (hash: string) => void;
  selected?: boolean;
  onSelect?: (hash: string) => void;
  statusBadge: ReactNode;
  action?: ReactNode;
}

export default function GalleryCard({
  image,
  onOpen,
  selected,
  onSelect,
  statusBadge,
  action,
}: Props) {
  const [imgError, setImgError] = useState(false);
  const filename = image.canonical_path.split("/").pop() ?? image.canonical_path;
  const imageSrc = image.file_url ?? `/api/images/${image.content_hash}/file`;

  return (
    <div
      className="group relative cursor-pointer overflow-hidden rounded-[24px] border border-white/10 bg-card/70 shadow-curator"
      onClick={() => onOpen(image.content_hash)}
    >
      <div className="relative flex aspect-[4/3] h-full w-full items-center justify-center bg-[#181a1f]">
        {imgError ? (
          <ImageOff className="h-8 w-8 text-neutral-600" />
        ) : (
          <img
            src={imageSrc}
            alt={filename}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.04]"
            onError={() => setImgError(true)}
            loading="lazy"
          />
        )}

        <div className={`absolute inset-0 transition-opacity duration-200 ${
          selected
            ? "bg-black/20 opacity-100"
            : "bg-gradient-to-b from-black/15 via-transparent to-black/65 opacity-0 group-hover:opacity-100"
        }`} />

        {onSelect && (
          <button
            className={`absolute left-3 top-3 z-10 flex h-7 w-7 items-center justify-center rounded-full border-2 transition-all duration-200 ${
              selected
                ? "scale-100 border-primary bg-primary opacity-100"
                : "scale-90 border-white/80 bg-black/30 opacity-0 group-hover:scale-100 group-hover:opacity-100 hover:bg-black/50"
            }`}
            onClick={(e) => {
              e.stopPropagation();
              onSelect(image.content_hash);
            }}
          >
            {selected && <Check className="h-3.5 w-3.5 text-white" strokeWidth={3} />}
          </button>
        )}

        <div className="absolute right-3 top-3 z-10 flex items-center gap-2">
          {action}
          <Badge className="border-0 bg-black/60 text-white backdrop-blur">
            {statusBadge}
          </Badge>
        </div>

        <div className="absolute inset-x-0 bottom-0 px-3 py-3 opacity-0 transition-opacity duration-200 group-hover:opacity-100">
          <p className="truncate text-[11px] text-white drop-shadow-[0_1px_2px_rgba(0,0,0,0.8)]" title={filename}>
            {filename}
          </p>
        </div>
      </div>

      {selected && (
        <div className="pointer-events-none absolute inset-0 rounded-[24px] ring-2 ring-primary ring-offset-2 ring-offset-background" />
      )}
    </div>
  );
}
