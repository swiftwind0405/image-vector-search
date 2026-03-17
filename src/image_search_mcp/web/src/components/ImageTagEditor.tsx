import { toast } from "sonner";
import { X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useImageTags,
  useImageCategories,
  useAddTagToImage,
  useRemoveTagFromImage,
  useAddCategoryToImage,
  useRemoveCategoryFromImage,
} from "@/api/images";
import { useTags } from "@/api/tags";
import { useCategories } from "@/api/categories";
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
      {
        onError: () => toast.error("Failed to add tag"),
      },
    );
  };

  const handleRemoveTag = (tagId: number) => {
    removeTag.mutate(
      { contentHash, tagId },
      {
        onError: () => toast.error("Failed to remove tag"),
      },
    );
  };

  const handleAddCategory = (value: string) => {
    const categoryId = parseInt(value, 10);
    addCategory.mutate(
      { contentHash, categoryId },
      {
        onError: () => toast.error("Failed to add category"),
      },
    );
  };

  const handleRemoveCategory = (categoryId: number) => {
    removeCategory.mutate(
      { contentHash, categoryId },
      {
        onError: () => toast.error("Failed to remove category"),
      },
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
        {availableTags.length > 0 && (
          <Select onValueChange={handleAddTag} value="">
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Add tag..." />
            </SelectTrigger>
            <SelectContent>
              {availableTags.map((tag) => (
                <SelectItem key={tag.id} value={String(tag.id)}>
                  {tag.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
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
        {availableCategories.length > 0 && (
          <Select onValueChange={handleAddCategory} value="">
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Add category..." />
            </SelectTrigger>
            <SelectContent>
              {availableCategories.map((cat) => (
                <SelectItem key={cat.id} value={String(cat.id)}>
                  {cat.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>
    </div>
  );
}
