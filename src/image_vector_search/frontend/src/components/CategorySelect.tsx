import type { CategoryNode } from "@/api/types";
import CreatableSelect, { type SelectOption } from "@/components/CreatableSelect";

interface CategorySelectProps {
  categories: CategoryNode[];
  value: string;
  onValueChange: (value: string) => void;
  onCreate: (name: string) => string | void | Promise<string | void>;
  placeholder?: string;
  triggerClassName?: string;
  disabled?: boolean;
  creating?: boolean;
}

function flattenCategories(
  nodes: CategoryNode[],
  depth = 0,
): SelectOption[] {
  const options: SelectOption[] = [];

  for (const node of nodes) {
    options.push({
      value: String(node.id),
      label: "\u00A0\u00A0".repeat(depth) + node.name,
    });
    options.push(...flattenCategories(node.children, depth + 1));
  }

  return options;
}

export default function CategorySelect({
  categories,
  value,
  onValueChange,
  onCreate,
  placeholder = "Select category...",
  triggerClassName,
  disabled = false,
  creating = false,
}: CategorySelectProps) {
  return (
    <CreatableSelect
      options={flattenCategories(categories)}
      value={value}
      onValueChange={onValueChange}
      onCreate={onCreate}
      placeholder={placeholder}
      createTitle="Create Category"
      createLabel="Category name"
      createButtonLabel="New category"
      triggerClassName={triggerClassName}
      disabled={disabled}
      creating={creating}
    />
  );
}
