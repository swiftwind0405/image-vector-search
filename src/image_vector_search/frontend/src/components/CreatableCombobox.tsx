import { useState, useRef, useEffect, useCallback } from "react";
import { Input } from "@/components/ui/input";
import { Plus } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ComboboxOption {
  value: string;
  label: string;
}

interface Props {
  options: ComboboxOption[];
  placeholder?: string;
  onSelect: (value: string) => void;
  onCreate: (name: string) => void;
  creating?: boolean;
}

export default function CreatableCombobox({
  options,
  placeholder = "Search or create...",
  onSelect,
  onCreate,
  creating = false,
}: Props) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const filtered = query.trim()
    ? options.filter((o) =>
        o.label.replace(/\u00A0/g, "").toLowerCase().includes(query.trim().toLowerCase()),
      )
    : options;

  const exactMatch = options.some(
    (o) => o.label.replace(/\u00A0/g, "").trim().toLowerCase() === query.trim().toLowerCase(),
  );
  const showCreate = query.trim().length > 0 && !exactMatch;
  const totalItems = filtered.length + (showCreate ? 1 : 0);

  useEffect(() => {
    setHighlightIndex(0);
  }, [query]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const scrollToIndex = useCallback(
    (index: number) => {
      if (!listRef.current) return;
      const items = listRef.current.querySelectorAll("[data-combobox-item]");
      items[index]?.scrollIntoView({ block: "nearest" });
    },
    [],
  );

  const handleSelect = (value: string) => {
    onSelect(value);
    setQuery("");
    setOpen(false);
  };

  const handleCreate = () => {
    if (creating) return;
    onCreate(query.trim());
    setQuery("");
    setOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open && e.key !== "Escape") {
      setOpen(true);
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      const next = Math.min(highlightIndex + 1, totalItems - 1);
      setHighlightIndex(next);
      scrollToIndex(next);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      const prev = Math.max(highlightIndex - 1, 0);
      setHighlightIndex(prev);
      scrollToIndex(prev);
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (totalItems === 0) return;
      if (highlightIndex < filtered.length) {
        handleSelect(filtered[highlightIndex].value);
      } else if (showCreate) {
        handleCreate();
      }
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div ref={containerRef} className="relative w-48">
      <Input
        value={query}
        onChange={(e) => setQuery((e.target as HTMLInputElement).value)}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className="h-8 text-sm"
        disabled={creating}
      />
      {open && totalItems > 0 && (
        <div
          ref={listRef}
          className="absolute z-50 mt-1 w-full max-h-48 overflow-auto rounded-md border bg-popover text-popover-foreground shadow-md"
        >
          {filtered.map((option, i) => (
            <div
              key={option.value}
              data-combobox-item
              className={cn(
                "cursor-pointer px-2 py-1.5 text-sm",
                i === highlightIndex && "bg-accent text-accent-foreground",
              )}
              onMouseEnter={() => setHighlightIndex(i)}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => handleSelect(option.value)}
            >
              {option.label}
            </div>
          ))}
          {showCreate && (
            <div
              data-combobox-item
              className={cn(
                "flex cursor-pointer items-center gap-1.5 border-t px-2 py-1.5 text-sm text-primary",
                highlightIndex === filtered.length && "bg-accent text-accent-foreground",
              )}
              onMouseEnter={() => setHighlightIndex(filtered.length)}
              onMouseDown={(e) => e.preventDefault()}
              onClick={handleCreate}
            >
              <Plus className="h-3.5 w-3.5" />
              Create &ldquo;{query.trim()}&rdquo;
            </div>
          )}
        </div>
      )}
    </div>
  );
}
