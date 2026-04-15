import { useEffect, useState } from "react";
import { toast } from "sonner";

import { FolderMinus } from "lucide-react";

import {
  useEmbeddingSettings,
  useFolderSettings,
  useUpdateEmbeddingSettings,
  useUpdateExcludedFolders,
} from "@/api/settings";
import type { UpdateEmbeddingSettingsRequest } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function readApiErrorMessage(error: unknown): string {
  if (!error || typeof error !== "object") {
    return "Failed to save settings";
  }
  const message = "message" in error ? String(error.message) : "";
  if (!message) {
    return "Failed to save settings";
  }
  try {
    const parsed = JSON.parse(message) as { detail?: string };
    return parsed.detail || message;
  } catch {
    return message;
  }
}

export default function SettingsPage() {
  const { data, isLoading } = useEmbeddingSettings();
  const updateSettings = useUpdateEmbeddingSettings();

  const { data: folderData, isLoading: folderIsLoading } = useFolderSettings();
  const updateFolders = useUpdateExcludedFolders();

  const [provider, setProvider] = useState("");
  const [jinaKey, setJinaKey] = useState("");
  const [googleKey, setGoogleKey] = useState("");
  const [jinaKeyDirty, setJinaKeyDirty] = useState(false);
  const [googleKeyDirty, setGoogleKeyDirty] = useState(false);
  const [providerDirty, setProviderDirty] = useState(false);
  const [reloadFailed, setReloadFailed] = useState(false);
  const [lastPayload, setLastPayload] = useState<UpdateEmbeddingSettingsRequest | null>(null);

  const [selectedExclusions, setSelectedExclusions] = useState<Set<string>>(new Set());
  const [exclusionsDirty, setExclusionsDirty] = useState(false);

  useEffect(() => {
    if (!data) {
      return;
    }
    setProvider(data.provider || "");
    setJinaKey("");
    setGoogleKey("");
    setJinaKeyDirty(false);
    setGoogleKeyDirty(false);
    setProviderDirty(false);
    setReloadFailed(false);
    setLastPayload(null);
  }, [data]);

  useEffect(() => {
    if (folderData?.excluded) {
      setSelectedExclusions(new Set(folderData.excluded));
      setExclusionsDirty(false);
    }
  }, [folderData]);

  const jinaEmpty = jinaKeyDirty && jinaKey.trim() === "";
  const googleEmpty = googleKeyDirty && googleKey.trim() === "";
  const isDirty = providerDirty || jinaKeyDirty || googleKeyDirty;
  const hasValidationError = jinaEmpty || googleEmpty;
  const canSave = Boolean(provider) && isDirty && !hasValidationError && !updateSettings.isPending;

  async function submit(payload: UpdateEmbeddingSettingsRequest) {
    setLastPayload(payload);
    try {
      await updateSettings.mutateAsync(payload);
      setReloadFailed(false);
      toast.success("Settings saved");
      setJinaKey("");
      setGoogleKey("");
      setJinaKeyDirty(false);
      setGoogleKeyDirty(false);
      setProviderDirty(false);
    } catch (error) {
      const message = readApiErrorMessage(error);
      if (message.startsWith("Settings saved but embedding reload failed:")) {
        setReloadFailed(true);
        toast.error("Settings saved but reload failed - try again");
        return;
      }
      toast.error(message);
    }
  }

  async function handleSave() {
    if (!canSave) {
      return;
    }
    await submit({
      provider,
      jina_api_key: jinaKeyDirty ? jinaKey : null,
      google_api_key: googleKeyDirty ? googleKey : null,
    });
  }

  async function handleRetry() {
    if (lastPayload) {
      await submit(lastPayload);
    }
  }

  if (isLoading || !data || folderIsLoading || !folderData) {
    return <div className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">Loading settings…</div>;
  }

  const handleToggleExclusion = (folder: string, checked: boolean) => {
    setSelectedExclusions((current) => {
      const next = new Set(current);
      if (checked) {
        next.add(folder);
      } else {
        next.delete(folder);
      }
      return next;
    });
    setExclusionsDirty(true);
  };

  const handleSaveExclusions = async () => {
    if (!exclusionsDirty || updateFolders.isPending) return;
    try {
      await updateFolders.mutateAsync({ excluded: Array.from(selectedExclusions) });
      setExclusionsDirty(false);
      toast.success("Excluded folders updated");
    } catch (error) {
      toast.error(readApiErrorMessage(error));
    }
  };

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-border bg-card p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-2">
            <p className="text-[11px] uppercase tracking-[0.08em] text-muted-foreground">Settings</p>
            <h3 className="text-lg font-semibold tracking-tight text-foreground">Embedding Configuration</h3>
            <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
              Choose the active embedding provider and manage provider API keys without restarting the service.
            </p>
          </div>
          {data.using_environment_fallback ? (
            <Badge variant="outline" className="border-primary/20 bg-primary/10 text-primary">
              Currently using environment variable
            </Badge>
          ) : null}
        </div>

        {provider === "" && !data.jina_api_key_configured && !data.google_api_key_configured ? (
          <div className="mt-6 rounded-lg border border-[#f5e6b4] bg-[#fef9ec] px-4 py-3 text-sm text-[#8a6400]">
            Embedding not configured
          </div>
        ) : null}

        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="embedding-provider">Embedding Provider</Label>
            <select
              id="embedding-provider"
              aria-label="Embedding Provider"
              value={provider}
              onChange={(event) => {
                setProvider(event.target.value);
                setProviderDirty(true);
              }}
              className="flex h-11 w-full rounded-md border border-border bg-[#f9f9fa] px-3 text-sm text-foreground outline-none"
            >
              <option value="">Select provider</option>
              <option value="jina">jina</option>
              <option value="gemini">gemini</option>
            </select>
          </div>

          <div className="rounded-lg border border-border bg-[#f9f9fa] px-4 py-4">
            <p className="text-[11px] uppercase tracking-[0.08em] text-muted-foreground">Configured Keys</p>
            <div className="mt-3 flex gap-2">
              {data.jina_api_key_configured ? <Badge>Configured</Badge> : <Badge variant="outline">Jina missing</Badge>}
              {data.google_api_key_configured ? <Badge>Configured</Badge> : <Badge variant="outline">Google missing</Badge>}
            </div>
          </div>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="jina-api-key">Jina API Key</Label>
            <Input
              id="jina-api-key"
              aria-label="Jina API Key"
              type="password"
              value={jinaKey}
              placeholder={!jinaKeyDirty && data.jina_api_key_configured ? "••••••" : ""}
              onChange={(event) => {
                setJinaKey(event.target.value);
                setJinaKeyDirty(true);
              }}
              className={jinaEmpty ? "border-[#e1534a]" : ""}
            />
            {jinaEmpty ? <p className="text-sm text-[#b42318]">API key cannot be empty</p> : null}
          </div>

          <div className="space-y-2">
            <Label htmlFor="google-api-key">Google API Key</Label>
            <Input
              id="google-api-key"
              aria-label="Google API Key"
              type="password"
              value={googleKey}
              placeholder={!googleKeyDirty && data.google_api_key_configured ? "••••••" : ""}
              onChange={(event) => {
                setGoogleKey(event.target.value);
                setGoogleKeyDirty(true);
              }}
              className={googleEmpty ? "border-[#e1534a]" : ""}
            />
            {googleEmpty ? <p className="text-sm text-[#b42318]">API key cannot be empty</p> : null}
          </div>
        </div>

        <div className="mt-8 flex items-center gap-3">
          <Button onClick={handleSave} disabled={!canSave}>
            Save Settings
          </Button>
          {reloadFailed ? (
            <Button variant="outline" onClick={handleRetry}>
              Retry
            </Button>
          ) : null}
        </div>
      </section>

      <section className="rounded-lg border border-border bg-card p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-2">
            <p className="text-[11px] uppercase tracking-[0.08em] text-muted-foreground">Indexing</p>
            <h3 className="text-lg font-semibold tracking-tight text-foreground">Excluded Folders</h3>
            <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
              Select folders to exclude from embedding, indexing, browsing, search, and albums. Existing index data is preserved, so re-including a folder is instant.
            </p>
          </div>
          <div className="rounded-md bg-primary/12 p-3 text-primary">
            <FolderMinus className="h-5 w-5" />
          </div>
        </div>

        <div className="mt-8 space-y-2">
          {!folderData.folders.length ? (
            <p className="text-sm text-muted-foreground">No folders found in the images root.</p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {folderData.folders.map((folder) => {
                const checked = selectedExclusions.has(folder);
                return (
                  <label
                    key={folder}
                    className="flex cursor-pointer items-center gap-3 overflow-hidden rounded-md border border-border bg-[#f9f9fa] px-4 py-3 pb-3 pt-3 text-sm transition-colors hover:bg-[#f1f1f3]"
                  >
                    <Checkbox
                      checked={checked}
                      onCheckedChange={(c) => handleToggleExclusion(folder, c === true)}
                    />
                    <span className="min-w-0 flex-1 truncate text-foreground">{folder}</span>
                  </label>
                );
              })}
            </div>
          )}
        </div>

        <div className="mt-8 flex items-center gap-3">
          <Button
            onClick={handleSaveExclusions}
            disabled={!exclusionsDirty || updateFolders.isPending}
          >
            Save Exclusions
          </Button>
        </div>
      </section>
    </div>
  );
}
