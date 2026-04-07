import { toast } from "sonner";
import { X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import CreatableCombobox from "@/components/CreatableCombobox";
import {
  useImageTags,
  useImageCategories,
  useAddTagToImage,
  useRemoveTagFromImage,
  useAddCategoryToImage,
  useRemoveCategoryFromImage,
} from "@/api/images";
import { useTags, useCreateTag } from "@/api/tags";
import { useCategories, useCreateCategory } from "@/api/categories";
import type { CategoryNode } from "@/api/types";

function flattenCategories(
  nodes: CategoryNode[],
  depth = 0,
): { id: number; label: string }[] {
  const result: { id: number; label: string }[] = [];
  for (const node of nodes) {
    result.push({ id: node.id, label: "\u00A0\u00A0".repeat(depth) + node.name });
    result.push(...flattenCategories(node.children, depth + 1));
  }
  return result;
}

interface Props {
  contentHash: string;
}

export default function ImageTagEditor({ contentHash }: Props) {
  const { data: imageTags } = useImageTags(contentHash);
  const { data: imageCategories } = useImageCategories(contentHash);
  const { data: allTags } = useTags();
  const { data: allCategories } = useCategories();

  const addTag = useAddTagToImage();
  const removeTag = useRemoveTagFromImage();
  const addCategory = useAddCategoryToImage();
  const removeCategory = useRemoveCategoryFromImage();
  const createTag = useCreateTag();
  const createCategory = useCreateCategory();

  const assignedTagIds = new Set((imageTags ?? []).map((t) => t.id));
  const assignedCategoryIds = new Set((imageCategories ?? []).map((c) => c.id));

  const availableTags = (allTags ?? []).filter((t) => !assignedTagIds.has(t.id));
  const flatCategories = flattenCategories(allCategories ?? []);
  const availableCategories = flatCategories.filter(
    (c) => !assignedCategoryIds.has(c.id),
  );

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

  const handleAddCategory = (value: string) => {
    const categoryId = parseInt(value, 10);
    addCategory.mutate(
      { contentHash, categoryId },
      { onError: () => toast.error("Failed to add category") },
    );
  };

  const handleCreateAndAddCategory = (name: string) => {
    createCategory.mutate(
      { name },
      {
        onSuccess: (data) => {
          const createdCategory = data as { id: number };
          addCategory.mutate(
            { contentHash, categoryId: createdCategory.id },
            { onError: () => toast.error("Failed to add category") },
          );
        },
        onError: () => toast.error("Failed to create category"),
      },
    );
  };

  const handleRemoveCategory = (categoryId: number) => {
    removeCategory.mutate(
      { contentHash, categoryId },
      { onError: () => toast.error("Failed to remove category") },
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

      {/* Categories section */}
      <div className="space-y-2">
        <p className="text-sm font-medium">Categories</p>
        <div className="flex flex-wrap gap-2">
          {(imageCategories ?? []).map((cat) => (
            <Badge key={cat.id} variant="outline" className="flex items-center gap-1">
              {cat.name}
              <Button
                variant="ghost"
                size="icon"
                className="h-4 w-4 p-0 hover:bg-transparent"
                onClick={() => handleRemoveCategory(cat.id)}
              >
                <X className="h-3 w-3" />
              </Button>
            </Badge>
          ))}
          {(imageCategories ?? []).length === 0 && (
            <span className="text-sm text-muted-foreground">No categories assigned</span>
          )}
        </div>
        <CreatableCombobox
          options={availableCategories.map((c) => ({
            value: String(c.id),
            label: c.label,
          }))}
          placeholder="Add category..."
          onSelect={handleAddCategory}
          onCreate={handleCreateAndAddCategory}
          creating={createCategory.isPending}
        />
      </div>
    </div>
  );
}
