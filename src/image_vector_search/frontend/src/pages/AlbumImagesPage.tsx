import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import {
  useAddImagesToAlbum,
  useAlbum,
  useAlbumImages,
  useAlbumRules,
  useAlbumSourcePaths,
  useDeleteAlbum,
  useRemoveImagesFromAlbum,
} from "@/api/albums";
import type { ImageRecordWithLabels } from "@/api/types";
import AlbumEditorDialog from "@/components/AlbumEditorDialog";
import GalleryGrid from "@/components/GalleryGrid";
import ImageModal from "@/components/ImageModal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

function parseListInput(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function AlbumImagesPage() {
  const { albumId } = useParams();
  const navigate = useNavigate();
  const parsedAlbumId = Number(albumId);
  const { data: album } = useAlbum(parsedAlbumId);
  const { data: rules } = useAlbumRules(parsedAlbumId);
  const { data: sourcePaths } = useAlbumSourcePaths(parsedAlbumId);
  const albumImages = useAlbumImages(parsedAlbumId, 24);
  const deleteAlbum = useDeleteAlbum();
  const addImages = useAddImagesToAlbum();
  const removeImages = useRemoveImagesFromAlbum();

  const [editOpen, setEditOpen] = useState(false);
  const [modalHash, setModalHash] = useState<string | null>(null);
  const [addHashes, setAddHashes] = useState("");

  const images = useMemo<ImageRecordWithLabels[]>(
    () => albumImages.data?.pages.flatMap((page) => page.items) ?? [],
    [albumImages.data?.pages],
  );

  const activeImage = images.find((image) => image.content_hash === modalHash) ?? null;

  if (!Number.isInteger(parsedAlbumId) || parsedAlbumId <= 0) {
    return <p className="text-sm text-muted-foreground">Invalid album id.</p>;
  }

  if (!album) {
    return <p className="text-sm text-muted-foreground">Loading album…</p>;
  }

  const currentAlbum = album;
  const displayedRules = rules ?? [];
  const displayedSourcePaths = sourcePaths ?? [];

  function handleDeleteAlbum() {
    deleteAlbum.mutate(parsedAlbumId, {
      onSuccess: () => {
        toast.success("Album deleted");
        navigate("/albums");
      },
      onError: () => toast.error("Failed to delete album"),
    });
  }

  function handleAddImages() {
    const contentHashes = parseListInput(addHashes);
    if (contentHashes.length === 0) {
      return;
    }
    addImages.mutate(
      { albumId: parsedAlbumId, contentHashes },
      {
        onSuccess: () => {
          toast.success("Images added");
          setAddHashes("");
        },
        onError: () => toast.error("Failed to add images"),
      },
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/albums">
          <Button variant="ghost" size="sm" className="-ml-2 gap-1 text-muted-foreground">
            <ArrowLeft className="h-4 w-4" />
            Albums
          </Button>
        </Link>
      </div>

      <Card className="rounded-[32px] border-white/10 bg-card/72 shadow-curator">
        <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <CardTitle className="text-xl text-white">{currentAlbum.name}</CardTitle>
              <Badge className="border-white/10 bg-white/[0.08] text-white">
                {currentAlbum.type === "manual" ? "Manual" : "Smart"}
              </Badge>
              {currentAlbum.rule_logic && (
                <Badge variant="secondary" className="border-primary/20 bg-primary/10 text-primary">
                  {currentAlbum.rule_logic.toUpperCase()}
                </Badge>
              )}
            </div>
            {currentAlbum.description && (
              <p className="text-sm text-muted-foreground">{currentAlbum.description}</p>
            )}
            {currentAlbum.type === "smart" && (
              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary" className="border-white/10 bg-white/[0.08] text-white">
                  {displayedRules.length} rules
                </Badge>
                <Badge variant="secondary" className="border-white/10 bg-white/[0.08] text-white">
                  {displayedSourcePaths.length} source paths
                </Badge>
              </div>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setEditOpen(true)}>
              <Pencil className="mr-2 h-4 w-4" />
              Edit album
            </Button>
            <Button variant="destructive" onClick={handleDeleteAlbum}>
              Delete album
            </Button>
          </div>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          {currentAlbum.type === "smart"
            ? "Rules and source paths are managed from the edit dialog."
            : "Add or remove manual selections below."}
        </CardContent>
      </Card>

      {currentAlbum.type === "manual" && (
        <Card className="rounded-[32px] border-white/10 bg-card/72 shadow-curator">
          <CardHeader>
            <CardTitle className="text-base text-white">Manage images</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 md:flex-row">
            <Input
              placeholder="Comma-separated content hashes"
              value={addHashes}
              onChange={(event) => setAddHashes(event.target.value)}
            />
            <Button onClick={handleAddImages}>Add images</Button>
          </CardContent>
        </Card>
      )}

      <Card className="rounded-[32px] border-white/10 bg-card/72 shadow-curator">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base text-white">Images</CardTitle>
          <Badge variant="secondary" className="border-white/10 bg-white/[0.08] text-white">
            {currentAlbum.image_count ?? images.length} total
          </Badge>
        </CardHeader>
        <CardContent className="space-y-4">
          <GalleryGrid
            images={images}
            onOpen={setModalHash}
            renderStatusBadge={() => (currentAlbum.type === "manual" ? "Manual" : "Smart")}
            renderAction={(image) =>
              currentAlbum.type === "manual" ? (
                <button
                  className="rounded-full border border-white/15 bg-black/60 p-2 text-white"
                  onClick={(event) => {
                    event.stopPropagation();
                    removeImages.mutate(
                      { albumId: parsedAlbumId, contentHashes: [image.content_hash] },
                      {
                        onSuccess: () => toast.success("Image removed"),
                        onError: () => toast.error("Failed to remove image"),
                      },
                    );
                  }}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              ) : undefined
            }
          />
          {albumImages.hasNextPage && (
            <Button
              variant="outline"
              onClick={() => albumImages.fetchNextPage()}
              disabled={albumImages.isFetchingNextPage}
            >
              Load more
            </Button>
          )}
        </CardContent>
      </Card>

      <ImageModal
        image={activeImage}
        images={images}
        open={activeImage !== null}
        onClose={() => setModalHash(null)}
        onNavigate={setModalHash}
      />

      <AlbumEditorDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        album={currentAlbum}
        rules={displayedRules}
        sourcePaths={displayedSourcePaths}
      />
    </div>
  );
}
