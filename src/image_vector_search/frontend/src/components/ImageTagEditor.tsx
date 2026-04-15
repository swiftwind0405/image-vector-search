import { toast } from "sonner";
import { X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import CreatableCombobox from "@/components/CreatableCombobox";
import {
  useImageTags,
  useAddTagToImage,
  useRemoveTagFromImage,
} from "@/api/images";
import { useTags, useCreateTag } from "@/api/tags";

interface Props {
  contentHash: string;
}

export default function ImageTagEditor({ contentHash }: Props) {
  const { data: imageTags } = useImageTags(contentHash);
  const { data: allTags } = useTags();

  const addTag = useAddTagToImage();
  const removeTag = useRemoveTagFromImage();
  const createTag = useCreateTag();

  const assignedTagIds = new Set((imageTags ?? []).map((t) => t.id));

  const availableTags = (allTags ?? []).filter((t) => !assignedTagIds.has(t.id));

  const handleAddTag = (value: string) => {
    const tagId = parseInt(value, 10);
    addTag.mutate(
      { contentHash, tagId },
      { onError: () => toast.error("Failed to add tag") },
    );
  };

  const handleCreateAndAddTag = (name: string) => {
    createTag.mutate(name, {
      onSuccess: (tag) => {
        addTag.mutate(
          { contentHash, tagId: tag.id },
          { onError: () => toast.error("Failed to add tag") },
        );
      },
      onError: () => toast.error("Failed to create tag"),
    });
  };

  const handleRemoveTag = (tagId: number) => {
    removeTag.mutate(
      { contentHash, tagId },
      { onError: () => toast.error("Failed to remove tag") },
    );
  };

  return (
    <div className="space-y-4 p-4">
      {/* Tags section */}
      <div className="space-y-2">
        <p className="text-sm font-medium">Tags</p>
        <div className="flex flex-wrap gap-2">
          {(imageTags ?? []).map((tag) => (
            <Badge key={tag.id} className="flex items-center gap-1">
              {tag.name}
              <Button
                variant="ghost"
                size="icon"
                className="h-4 w-4 p-0 hover:bg-transparent"
                onClick={() => handleRemoveTag(tag.id)}
              >
                <X className="h-3 w-3" />
              </Button>
            </Badge>
          ))}
          {(imageTags ?? []).length === 0 && (
            <span className="text-sm text-muted-foreground">No tags assigned</span>
          )}
        </div>
        <CreatableCombobox
          options={availableTags.map((t) => ({
            value: String(t.id),
            label: t.name,
          }))}
          placeholder="Add tag..."
          onSelect={handleAddTag}
          onCreate={handleCreateAndAddTag}
          creating={createTag.isPending}
        />
      </div>
    </div>
  );
}
