import type { Tag } from "@/api/types";
import CreatableSelect from "@/components/CreatableSelect";

interface TagSelectProps {
  tags: Tag[];
  value: string;
  onValueChange: (value: string) => void;
  onCreate: (name: string) => string | void | Promise<string | void>;
  placeholder?: string;
  triggerClassName?: string;
  disabled?: boolean;
  creating?: boolean;
}

export default function TagSelect({
  tags,
  value,
  onValueChange,
  onCreate,
  placeholder = "Select tag...",
  triggerClassName,
  disabled = false,
  creating = false,
}: TagSelectProps) {
  return (
    <CreatableSelect
      options={tags.map((tag) => ({ value: String(tag.id), label: tag.name }))}
      value={value}
      onValueChange={onValueChange}
      onCreate={onCreate}
      placeholder={placeholder}
      createTitle="Create Tag"
      createLabel="Tag name"
      createButtonLabel="New tag"
      triggerClassName={triggerClassName}
      disabled={disabled}
      creating={creating}
    />
  );
}
