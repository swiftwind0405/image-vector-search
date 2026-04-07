import { useEffect, useState } from "react";
import { toast } from "sonner";

import { useEmbeddingSettings, useUpdateEmbeddingSettings } from "@/api/settings";
import type { UpdateEmbeddingSettingsRequest } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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

  const [provider, setProvider] = useState("");
  const [jinaKey, setJinaKey] = useState("");
  const [googleKey, setGoogleKey] = useState("");
  const [jinaKeyDirty, setJinaKeyDirty] = useState(false);
  const [googleKeyDirty, setGoogleKeyDirty] = useState(false);
  const [providerDirty, setProviderDirty] = useState(false);
  const [reloadFailed, setReloadFailed] = useState(false);
  const [lastPayload, setLastPayload] = useState<UpdateEmbeddingSettingsRequest | null>(null);

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

  if (isLoading || !data) {
    return <div className="rounded-[28px] border border-white/10 bg-card/75 p-6 text-sm text-muted-foreground">Loading settings…</div>;
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[32px] border border-white/10 bg-card/80 p-6 shadow-curator backdrop-blur">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-2">
            <p className="text-[11px] uppercase tracking-[0.24em] text-primary/90">Settings</p>
            <h3 className="text-2xl font-semibold tracking-tight text-white">Embedding Configuration</h3>
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
          <div className="mt-6 rounded-3xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
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
              className="flex h-11 w-full rounded-2xl border border-white/10 bg-white/[0.03] px-3 text-sm text-white outline-none"
            >
              <option value="">Select provider</option>
              <option value="jina">jina</option>
              <option value="gemini">gemini</option>
            </select>
          </div>

          <div className="rounded-[28px] border border-white/10 bg-white/[0.03] px-4 py-4">
            <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Configured Keys</p>
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
              className={jinaEmpty ? "border-red-400" : ""}
            />
            {jinaEmpty ? <p className="text-sm text-red-300">API key cannot be empty</p> : null}
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
              className={googleEmpty ? "border-red-400" : ""}
            />
            {googleEmpty ? <p className="text-sm text-red-300">API key cannot be empty</p> : null}
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
    </div>
  );
}
