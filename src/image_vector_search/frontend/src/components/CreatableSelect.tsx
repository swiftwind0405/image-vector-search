import { useEffect, useMemo, useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

export interface SelectOption {
  value: string;
  label: string;
}

interface CreatableSelectProps {
  options: SelectOption[];
  value: string;
  onValueChange: (value: string) => void;
  onCreate: (name: string) => string | void | Promise<string | void>;
  placeholder: string;
  createTitle: string;
  createLabel: string;
  createButtonLabel: string;
  triggerClassName?: string;
  disabled?: boolean;
  creating?: boolean;
}

export default function CreatableSelect({
  options,
  value,
  onValueChange,
  onCreate,
  placeholder,
  createTitle,
  createLabel,
  createButtonLabel,
  triggerClassName,
  disabled = false,
  creating = false,
}: CreatableSelectProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [draftName, setDraftName] = useState("");

  const selectedOption = useMemo(
    () => options.find((option) => option.value === value),
    [options, value],
  );

  useEffect(() => {
    if (!dialogOpen) {
      setDraftName("");
    }
  }, [dialogOpen]);

  const handleCreate = async () => {
    const trimmed = draftName.trim();
    if (!trimmed || creating) return;

    try {
      const createdValue = await onCreate(trimmed);
      if (createdValue) {
        onValueChange(createdValue);
      }
      setDialogOpen(false);
    } catch {
      // Parent mutation handlers own error reporting; keep the dialog open on failure.
    }
  };

  return (
    <div className="flex items-center gap-2">
      <Select value={value} onValueChange={(next) => onValueChange(next ?? "")} disabled={disabled}>
        <SelectTrigger className={cn("flex-1", triggerClassName)}>
          {selectedOption ? (
            <span className="flex-1 truncate text-left">{selectedOption.label}</span>
          ) : (
            <SelectValue placeholder={placeholder} />
          )}
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogTrigger
          render={
            <Button
              type="button"
              size="icon-sm"
              variant="outline"
              aria-label={createButtonLabel}
              disabled={disabled}
            />
          }
        >
          <Plus className="h-4 w-4" />
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{createTitle}</DialogTitle>
          </DialogHeader>
          <form
            className="space-y-4"
            onSubmit={async (event) => {
              event.preventDefault();
              await handleCreate();
            }}
          >
            <div className="space-y-2">
              <Label htmlFor="creatable-select-name">{createLabel}</Label>
              <Input
                id="creatable-select-name"
                value={draftName}
                onChange={(event) => setDraftName(event.target.value)}
                placeholder={placeholder}
                disabled={creating}
                autoFocus
              />
            </div>
            <DialogFooter>
              <Button type="submit" disabled={!draftName.trim() || creating}>
                Create
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
