import { useState } from "react";
import { Link } from "react-router-dom";
import { Images, Plus } from "lucide-react";
import { useListAlbums } from "@/api/albums";
import type { Album } from "@/api/types";
import AlbumEditorDialog from "@/components/AlbumEditorDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";

function AlbumCard({ album }: { album: Album }) {
  const coverSrc = album.cover_image
    ? album.cover_image.file_url ?? `/api/images/${album.cover_image.content_hash}/file`
    : null;

  return (
    <Link
      to={`/albums/${album.id}/images`}
      className="group overflow-hidden rounded-lg border border-border bg-card transition-colors hover:border-primary/40 hover:bg-[#f4f4f5]"
    >
      <div className="relative aspect-[4/3] bg-[#181a1f]">
        {coverSrc ? (
          <img
            src={coverSrc}
            alt={album.name}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.04]"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            <Images className="h-10 w-10 opacity-40" />
          </div>
        )}
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 via-black/10 to-transparent px-4 py-4">
          <div className="flex items-center gap-2">
            <Badge className="border-0 bg-black/60 text-white">
              {album.type === "manual" ? "Manual" : "Smart"}
            </Badge>
            <Badge variant="secondary" className="border-0 bg-white/90 text-[#0e0e10]">
              {album.image_count ?? 0} images
            </Badge>
          </div>
          <p className="mt-3 text-lg font-medium text-white">{album.name}</p>
          {album.description && (
            <p className="mt-1 line-clamp-2 text-sm text-white/80">{album.description}</p>
          )}
        </div>
      </div>
    </Link>
  );
}

export default function AlbumsPage() {
  const { data: albums, isLoading } = useListAlbums();
  const [open, setOpen] = useState(false);

  return (
    <div className="space-y-6">
      <Card className="rounded-lg border-border bg-card">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base text-foreground">Albums</CardTitle>
            <p className="mt-2 text-sm text-muted-foreground">
              Curate hand-picked sequences or define smart collections that stay current as tags evolve.
            </p>
          </div>
          <Button onClick={() => setOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create album
          </Button>
        </CardHeader>
      </Card>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div
              key={index}
              className="aspect-[4/3] animate-pulse rounded-lg border border-border bg-[#f7f7f8]"
            />
          ))}
        </div>
      ) : !albums || albums.length === 0 ? (
        <div className="rounded-lg border border-border bg-[#f7f7f8] px-6 py-10 text-center text-sm text-muted-foreground">
          No albums yet.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {albums.map((album) => (
            <AlbumCard key={album.id} album={album} />
          ))}
        </div>
      )}

      <AlbumEditorDialog open={open} onOpenChange={setOpen} />
    </div>
  );
}
