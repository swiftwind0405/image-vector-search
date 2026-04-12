import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useCreateAlbum, useSetAlbumRules, useSetAlbumSourcePaths, useUpdateAlbum } from "@/api/albums";
import { ApiError } from "@/api/client";
import { useTags } from "@/api/tags";
import type { Album, AlbumRule } from "@/api/types";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface RuleDraft {
  tag_id: string;
  match_mode: "include" | "exclude";
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  album?: Album | null;
  rules?: AlbumRule[];
  sourcePaths?: string[];
  onSaved?: (album: Album) => void;
}

export default function AlbumEditorDialog({
  open,
  onOpenChange,
  album,
  rules = [],
  sourcePaths = [],
  onSaved,
}: Props) {
  const { data: tags } = useTags();
  const createAlbum = useCreateAlbum();
  const updateAlbum = useUpdateAlbum();
  const setAlbumRules = useSetAlbumRules();
  const setAlbumSourcePaths = useSetAlbumSourcePaths();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [type, setType] = useState<"manual" | "smart">("manual");
  const [ruleLogic, setRuleLogic] = useState<"and" | "or">("or");
  const [ruleDrafts, setRuleDrafts] = useState<RuleDraft[]>([]);
  const [sourcePathInput, setSourcePathInput] = useState("");
  const [sourcePathDrafts, setSourcePathDrafts] = useState<string[]>([]);

  useEffect(() => {
    if (!open) {
      return;
    }
    setName(album?.name ?? "");
    setDescription(album?.description ?? "");
    setType(album?.type ?? "manual");
    setRuleLogic(album?.rule_logic ?? "or");
    setRuleDrafts(
      rules.map((rule) => ({
        tag_id: String(rule.tag_id),
        match_mode: rule.match_mode,
      })),
    );
    setSourcePathInput("");
    setSourcePathDrafts(sourcePaths);
  }, [open, album, rules, sourcePaths]);

  const isPending =
    createAlbum.isPending ||
    updateAlbum.isPending ||
    setAlbumRules.isPending ||
    setAlbumSourcePaths.isPending;

  function addRuleDraft() {
    setRuleDrafts((current) => [...current, { tag_id: "", match_mode: "include" }]);
  }

  function updateRuleDraft(index: number, next: Partial<RuleDraft>) {
    setRuleDrafts((current) =>
      current.map((rule, currentIndex) =>
        currentIndex === index ? { ...rule, ...next } : rule,
      ),
    );
  }

  function removeRuleDraft(index: number) {
    setRuleDrafts((current) => current.filter((_, currentIndex) => currentIndex !== index));
  }

  function addSourcePathDraft() {
    const normalized = sourcePathInput.trim().replace(/^\/+|\/+$/g, "");
    if (!normalized) {
      return;
    }
    if (sourcePathDrafts.includes(normalized)) {
      toast.error("Source path already exists");
      return;
    }
    setSourcePathDrafts((current) => [...current, normalized]);
    setSourcePathInput("");
  }

  function removeSourcePathDraft(path: string) {
    setSourcePathDrafts((current) => current.filter((currentPath) => currentPath !== path));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();

    const normalizedRules = ruleDrafts
      .filter((rule) => rule.tag_id)
      .map((rule) => ({
        tag_id: Number(rule.tag_id),
        match_mode: rule.match_mode,
      }));

    if (
      (album?.type ?? type) === "smart" &&
      normalizedRules.some((rule) => !Number.isInteger(rule.tag_id) || rule.tag_id <= 0)
    ) {
      toast.error("Each smart rule needs a valid tag");
      return;
    }

    try {
      let savedAlbum: Album;
      if (album) {
        savedAlbum = await updateAlbum.mutateAsync({
          albumId: album.id,
          name,
          description,
        });
      } else {
        savedAlbum = await createAlbum.mutateAsync({
          name,
          description,
          type,
          ...(type === "smart" ? { rule_logic: ruleLogic } : {}),
        });
      }

      if ((album?.type ?? type) === "smart") {
        await setAlbumRules.mutateAsync({
          albumId: savedAlbum.id,
          rules: normalizedRules,
        });
        await setAlbumSourcePaths.mutateAsync({
          albumId: savedAlbum.id,
          paths: sourcePathDrafts,
        });
      }

      toast.success(album ? "Album updated" : "Album created");
      onOpenChange(false);
      onSaved?.(savedAlbum);
    } catch (error) {
      toast.error(
        error instanceof ApiError && error.message ? error.message : "Failed to save album",
      );
    }
  }

  const effectiveType = album?.type ?? type;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>{album ? "Edit album" : "Create album"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid gap-3 md:grid-cols-2">
            <Input
              placeholder="Album name"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
            <Input
              placeholder="Description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </div>

          {!album && (
            <div className="grid gap-3 md:grid-cols-2">
              <Select value={type} onValueChange={(value) => setType(value as "manual" | "smart")}>
                <SelectTrigger>
                  <SelectValue placeholder="Album type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="manual">Manual</SelectItem>
                  <SelectItem value="smart">Smart</SelectItem>
                </SelectContent>
              </Select>
              {type === "smart" && (
                <Select
                  value={ruleLogic}
                  onValueChange={(value) => setRuleLogic(value as "and" | "or")}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Rule logic" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="or">Match any include tag</SelectItem>
                    <SelectItem value="and">Match all include tags</SelectItem>
                  </SelectContent>
                </Select>
              )}
            </div>
          )}

        {effectiveType === "smart" && (
          <div className="space-y-5">
              <div className="space-y-3 rounded-[24px] border border-white/10 bg-white/[0.03] p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-medium text-white">Rules</h3>
                    <p className="text-xs text-muted-foreground">
                      Define include/exclude tags before saving the smart album.
                    </p>
                  </div>
                  <Button type="button" variant="outline" size="sm" onClick={addRuleDraft}>
                    <Plus className="mr-1 h-3.5 w-3.5" />
                    Add rule
                  </Button>
                </div>
                {ruleDrafts.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No rules configured yet.</p>
                ) : (
                  <div className="space-y-3">
                    {ruleDrafts.map((rule, index) => (
                      <div
                        key={`${index}-${rule.tag_id}-${rule.match_mode}`}
                        className="grid gap-2 md:grid-cols-[1.1fr_0.8fr_auto]"
                      >
                        <Select
                          value={rule.tag_id}
                          onValueChange={(value) =>
                            updateRuleDraft(index, { tag_id: value ?? "" })
                          }
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select tag" />
                          </SelectTrigger>
                          <SelectContent>
                            {(tags ?? []).map((tag) => (
                              <SelectItem key={tag.id} value={String(tag.id)}>
                                {tag.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <Select
                          value={rule.match_mode}
                          onValueChange={(value) =>
                            updateRuleDraft(index, {
                              match_mode: value as "include" | "exclude",
                            })
                          }
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Mode" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="include">Include</SelectItem>
                            <SelectItem value="exclude">Exclude</SelectItem>
                          </SelectContent>
                        </Select>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => removeRuleDraft(index)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="space-y-3 rounded-[24px] border border-white/10 bg-white/[0.03] p-4">
                <div>
                  <h3 className="text-sm font-medium text-white">Source paths</h3>
                  <p className="text-xs text-muted-foreground">
                    Limit smart matching to specific folders before saving.
                  </p>
                </div>
                <div className="flex gap-2">
                  <Input
                    placeholder="photos/travel"
                    value={sourcePathInput}
                    onChange={(event) => setSourcePathInput(event.target.value)}
                  />
                  <Button type="button" variant="outline" onClick={addSourcePathDraft}>
                    Add
                  </Button>
                </div>
                {sourcePathDrafts.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No source path limits.</p>
                ) : (
                  <div className="space-y-2">
                    {sourcePathDrafts.map((path) => (
                      <div
                        key={path}
                        className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.04] px-3 py-2"
                      >
                        <span className="text-sm text-white">{path}</span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => removeSourcePathDraft(path)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          <DialogFooter>
            <Button type="submit" disabled={isPending || !name.trim()}>
              {album ? "Save" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
