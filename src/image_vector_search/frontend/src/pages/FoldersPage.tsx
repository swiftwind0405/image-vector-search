import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ChevronRight, Folder } from "lucide-react";
import { useFolderBrowse } from "@/api/folders";
import type { ImageRecordWithLabels } from "@/api/types";
import GalleryGrid from "@/components/GalleryGrid";
import ImageModal from "@/components/ImageModal";

function FolderCard({ path }: { path: string }) {
  const label = path.split("/").pop() ?? path;
  return (
    <Link
      to={`/folders?path=${encodeURIComponent(path)}`}
      className="group rounded-[24px] border border-white/10 bg-card/70 p-4 shadow-curator transition-colors hover:border-primary/40 hover:bg-white/[0.05]"
      title={path}
    >
      <div className="flex items-center gap-3">
        <div className="rounded-2xl border border-primary/20 bg-primary/10 p-3 text-primary">
          <Folder className="h-5 w-5" />
        </div>
        <p className="truncate text-sm font-medium text-white">{label}</p>
      </div>
    </Link>
  );
}

export default function FoldersPage() {
  const [searchParams] = useSearchParams();
  const path = searchParams.get("path") ?? "";
  const { data, isLoading, error } = useFolderBrowse(path);
  const [modalHash, setModalHash] = useState<string | null>(null);

  const images = useMemo<ImageRecordWithLabels[]>(
    () =>
      (data?.images ?? []).map((image) => ({
        ...image,
        tags: [],
        categories: [],
      })),
    [data?.images],
  );

  const activeImage = images.find((image) => image.content_hash === modalHash) ?? null;
  const segments = data?.path ? data.path.split("/") : [];

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-6 w-48 animate-pulse rounded-full bg-white/10" />
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div
              key={index}
              className="h-24 animate-pulse rounded-[24px] border border-white/10 bg-white/[0.04]"
            />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-[28px] border border-rose-400/20 bg-rose-500/10 px-5 py-4 text-sm text-rose-100">
        Failed to load folder contents.
      </div>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div className="space-y-6">
      <nav className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <Link to="/folders" className="transition-colors hover:text-white">
          Root
        </Link>
        {segments.map((segment, index) => {
          const accumulated = segments.slice(0, index + 1).join("/");
          const isLast = index === segments.length - 1;
          return (
            <span key={accumulated} className="inline-flex items-center gap-2">
              <ChevronRight className="h-4 w-4 text-muted-foreground/60" />
              {isLast ? (
                <span className="text-white">{segment}</span>
              ) : (
                <Link
                  to={`/folders?path=${encodeURIComponent(accumulated)}`}
                  className="transition-colors hover:text-white"
                >
                  {segment}
                </Link>
              )}
            </span>
          );
        })}
      </nav>

      {data.folders.length > 0 && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium uppercase tracking-[0.22em] text-muted-foreground">
              Subfolders
            </h3>
            <p className="text-xs text-muted-foreground">{data.folders.length} folders</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {data.folders.map((folder) => (
              <FolderCard key={folder} path={folder} />
            ))}
          </div>
        </section>
      )}

      {images.length > 0 && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium uppercase tracking-[0.22em] text-muted-foreground">
              Images
            </h3>
            <p className="text-xs text-muted-foreground">{images.length} visible</p>
          </div>
          <GalleryGrid
            images={images}
            onOpen={setModalHash}
            renderStatusBadge={(image) => (image.indexed ?? true ? "Indexed" : "Unindexed")}
          />
        </section>
      )}

      {data.folders.length === 0 && images.length === 0 && (
        <div className="rounded-[28px] border border-white/10 bg-white/[0.04] px-6 py-10 text-center text-sm text-muted-foreground">
          This folder is empty.
        </div>
      )}

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
