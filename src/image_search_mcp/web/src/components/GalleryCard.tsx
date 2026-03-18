import { useState } from "react";
import { ImageOff, Check } from "lucide-react";
import type { ImageRecordWithLabels } from "@/api/types";

interface Props {
  image: ImageRecordWithLabels;
  onOpen: (hash: string) => void;
  selected?: boolean;
  onSelect?: (hash: string) => void;
}

export default function GalleryCard({ image, onOpen, selected, onSelect }: Props) {
  const [imgError, setImgError] = useState(false);
  const filename = image.canonical_path.split("/").pop() ?? image.canonical_path;

  return (
    <div
      className="relative cursor-pointer rounded-sm overflow-hidden group"
      onClick={() => onOpen(image.content_hash)}
    >
      <div className="relative w-full h-full bg-[#1a1a1a] flex items-center justify-center aspect-[3/2]">
        {imgError ? (
          <ImageOff className="h-8 w-8 text-neutral-600" />
        ) : (
          <img
            src={`/api/images/${image.content_hash}/thumbnail`}
            alt={filename}
            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
            onError={() => setImgError(true)}
            loading="lazy"
          />
        )}

        {/* Hover overlay */}
        <div className={`absolute inset-0 transition-opacity duration-200 ${
          selected
            ? "bg-black/20 opacity-100"
            : "bg-gradient-to-b from-black/30 via-transparent to-black/20 opacity-0 group-hover:opacity-100"
        }`} />

        {/* Selection checkbox */}
        {onSelect && (
          <button
            className={`absolute top-1.5 left-1.5 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all duration-200 z-10 ${
              selected
                ? "bg-blue-500 border-blue-500 opacity-100 scale-100"
                : "border-white/80 bg-black/30 opacity-0 group-hover:opacity-100 scale-90 group-hover:scale-100 hover:bg-black/50"
            }`}
            onClick={(e) => {
              e.stopPropagation();
              onSelect(image.content_hash);
            }}
          >
            {selected && <Check className="h-3.5 w-3.5 text-white" strokeWidth={3} />}
          </button>
        )}

        {/* Filename tooltip on hover (bottom) */}
        <div className="absolute bottom-0 left-0 right-0 px-2 py-1.5 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
          <p className="text-[11px] text-white truncate drop-shadow-[0_1px_2px_rgba(0,0,0,0.8)]" title={filename}>
            {filename}
          </p>
        </div>
      </div>

      {/* Selected ring */}
      {selected && (
        <div className="absolute inset-0 rounded-sm ring-2 ring-blue-500 ring-offset-1 ring-offset-background pointer-events-none" />
      )}
    </div>
  );
}
