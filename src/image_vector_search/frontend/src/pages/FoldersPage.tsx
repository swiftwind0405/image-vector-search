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
      className="group rounded-lg border border-border bg-card p-4 transition-colors hover:border-primary/40 hover:bg-[#f4f4f5]"
      title={path}
    >
      <div className="flex items-center gap-3">
        <div className="rounded-md border border-primary/20 bg-primary/10 p-3 text-primary">
          <Folder className="h-5 w-5" />
        </div>
        <p className="truncate text-sm font-medium text-foreground">{label}</p>
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
      })),
    [data?.images],
  );

  const activeImage = images.find((image) => image.content_hash === modalHash) ?? null;
  const segments = data?.path ? data.path.split("/") : [];

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-6 w-48 animate-pulse rounded-full bg-[#f1f1f3]" />
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div
              key={index}
              className="h-24 animate-pulse rounded-lg border border-border bg-[#f7f7f8]"
            />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-[#fbd5d5] bg-[#fef2f2] px-5 py-4 text-sm text-[#9b2c2c]">
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
        <Link to="/folders" className="transition-colors hover:text-foreground">
          Root
        </Link>
        {segments.map((segment, index) => {
          const accumulated = segments.slice(0, index + 1).join("/");
          const isLast = index === segments.length - 1;
          return (
            <span key={accumulated} className="inline-flex items-center gap-2">
              <ChevronRight className="h-4 w-4 text-muted-foreground/60" />
              {isLast ? (
                <span className="text-foreground">{segment}</span>
              ) : (
                <Link
                  to={`/folders?path=${encodeURIComponent(accumulated)}`}
                  className="transition-colors hover:text-foreground"
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
            <h3 className="text-sm font-medium uppercase tracking-[0.08em] text-muted-foreground">
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
            <h3 className="text-sm font-medium uppercase tracking-[0.08em] text-muted-foreground">
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
        <div className="rounded-lg border border-border bg-[#f7f7f8] px-6 py-10 text-center text-sm text-muted-foreground">
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
