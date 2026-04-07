import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useLogin } from "@/api/auth";
import { ArrowRight, Search, FolderKanban } from "lucide-react";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const login = useLogin();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await login.mutateAsync({ username, password });
      navigate("/", { replace: true });
    } catch {
      setError("Invalid username or password");
    }
  }

  return (
    <div className="relative flex min-h-screen overflow-hidden bg-background">
      <div className="pointer-events-none absolute inset-0 bg-grain opacity-50" />
      <div className="relative grid min-h-screen w-full lg:grid-cols-[1.15fr_0.85fr]">
        <section className="hidden border-r border-white/8 px-8 py-10 lg:flex lg:flex-col lg:justify-between">
          <div className="space-y-8">
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-4 py-2 text-[11px] uppercase tracking-[0.24em] text-primary">
              <Search className="h-3.5 w-3.5" />
              Image Search Archive
            </div>

            <div className="max-w-xl space-y-6">
              <div className="space-y-4">
                <h1 className="text-6xl font-semibold leading-none tracking-tight text-white">
                  Image Search Archive
                </h1>
                <p className="max-w-lg text-lg leading-8 text-muted-foreground">
                  Curate, search, and organize your indexed image library.
                </p>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-[28px] border border-white/10 bg-card/75 p-5 shadow-curator backdrop-blur">
                  <Search className="h-5 w-5 text-primary" />
                  <p className="mt-4 text-sm font-medium text-white">Semantic retrieval</p>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    Search by description, compare similar frames, and review results in a dedicated visual workspace.
                  </p>
                </div>
                <div className="rounded-[28px] border border-white/10 bg-card/75 p-5 shadow-curator backdrop-blur">
                  <FolderKanban className="h-5 w-5 text-primary" />
                  <p className="mt-4 text-sm font-medium text-white">Taxonomy editing</p>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    Maintain categories and tags with the same archive-first view used for search and curation.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <p className="text-sm text-muted-foreground">
            Secure access to the image archive, embedding pipeline, and curator workspace.
          </p>
        </section>

        <section className="flex items-center justify-center px-5 py-8 sm:px-8">
          <div className="w-full max-w-md rounded-[32px] border border-white/10 bg-card/85 p-7 shadow-curator backdrop-blur">
            <div className="mb-8 space-y-3">
              <p className="text-[11px] uppercase tracking-[0.24em] text-primary">Sign in</p>
              <div>
                <h2 className="text-3xl font-semibold tracking-tight text-white">Image Search Archive</h2>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  Curate, search, and organize your indexed image library.
                </p>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col gap-5">
              <div className="flex flex-col gap-2">
                <Label htmlFor="username">Username</Label>
                <Input
                  id="username"
                  type="text"
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  className="h-11 rounded-2xl border-white/10 bg-white/[0.03]"
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="h-11 rounded-2xl border-white/10 bg-white/[0.03]"
                />
              </div>
              {error && <p className="text-sm text-red-300">{error}</p>}
              <Button type="submit" disabled={login.isPending} className="h-12 rounded-2xl text-sm">
                {login.isPending ? "Signing in…" : "Sign in"}
                {!login.isPending && <ArrowRight className="h-4 w-4" />}
              </Button>
            </form>
          </div>
        </section>
      </div>
    </div>
  );
}
