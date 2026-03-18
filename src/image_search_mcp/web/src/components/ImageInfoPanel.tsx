import { useState } from "react";
import { Copy, Check } from "lucide-react";
import { toast } from "sonner";
import ImageTagEditor from "@/components/ImageTagEditor";
import type { ImageRecordWithLabels } from "@/api/types";

function CopyablePath({ path }: { path: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(path);
    setCopied(true);
    toast.success("Path copied");
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <button
      onClick={handleCopy}
      className="group flex items-center gap-1.5 max-w-full text-left cursor-pointer rounded px-1.5 py-1 -mx-1.5 hover:bg-muted transition-colors"
      title={path}
    >
      <span className="text-xs text-muted-foreground font-mono truncate min-w-0">
        {path}
      </span>
      {copied ? (
        <Check className="h-3 w-3 text-green-500 shrink-0" />
      ) : (
        <Copy className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
      )}
    </button>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground/70 mb-2">
      {children}
    </p>
  );
}

interface Props {
  image: ImageRecordWithLabels;
}

export default function ImageInfoPanel({ image }: Props) {
  const filename = image.canonical_path.split("/").pop() ?? image.canonical_path;

  return (
    <div className="h-full overflow-y-auto">
      {/* Section 1: General info */}
      <div className="p-4 border-b">
        <SectionLabel>General</SectionLabel>
        <p className="text-sm font-bold truncate" title={filename}>
          {filename}
        </p>
        {image.width && image.height && (
          <p className="text-xs text-muted-foreground mt-1.5">
            {image.width} × {image.height} · {image.mime_type}
          </p>
        )}
        <div className="mt-1.5">
          <CopyablePath path={image.canonical_path} />
        </div>
      </div>

      {/* Section 2: Properties (Tags & Categories) */}
      <div>
        <div className="px-4 pt-4">
          <SectionLabel>Properties</SectionLabel>
        </div>
        <ImageTagEditor contentHash={image.content_hash} />
      </div>
    </div>
  );
}
