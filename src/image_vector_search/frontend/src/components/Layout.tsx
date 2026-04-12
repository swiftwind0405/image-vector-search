import { useState, useEffect } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { LayoutDashboard, Tag, FolderTree, Folder, ImagePlus, Search, LogOut, Sparkles, Database, ArrowUpRight, Settings, LayoutGrid, Menu, X } from "lucide-react";
import { useLogout } from "@/api/auth";
import { cn } from "@/lib/utils";
import logoMark from "../../logo.svg";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/search", icon: Search, label: "Search" },
  { to: "/tags", icon: Tag, label: "Tags" },
  { to: "/categories", icon: FolderTree, label: "Categories" },
  { to: "/albums", icon: LayoutGrid, label: "Albums" },
  { to: "/folders", icon: Folder, label: "Folders" },
  { to: "/images", icon: ImagePlus, label: "Images" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

const pageMeta = [
  {
    match: (pathname: string) => pathname === "/",
    title: "Collection Overview",
    subtitle: "Monitor index coverage, recent jobs, and embedding configuration at a glance.",
    eyebrow: "Curator Console",
  },
  {
    match: (pathname: string) => pathname.startsWith("/search"),
    title: "Search Workspace",
    subtitle: "Run semantic lookups, compare similar frames, and review image matches without leaving the gallery flow.",
    eyebrow: "Visual Retrieval",
  },
  {
    match: (pathname: string) => pathname === "/images",
    title: "Image Library",
    subtitle: "Browse indexed assets, apply structured filters, and act on selections in bulk.",
    eyebrow: "Archive",
  },
  {
    match: (pathname: string) => pathname.startsWith("/tags"),
    title: "Tag Index",
    subtitle: "Maintain descriptive labels and jump directly into the images behind each term.",
    eyebrow: "Taxonomy",
  },
  {
    match: (pathname: string) => pathname.startsWith("/categories"),
    title: "Category Structure",
    subtitle: "Shape the hierarchy that organizes the archive and inspect each branch visually.",
    eyebrow: "Taxonomy",
  },
  {
    match: (pathname: string) => pathname.startsWith("/albums"),
    title: "Album Collections",
    subtitle: "Assemble manual sets, define smart rules, and review each collection as a living image sequence.",
    eyebrow: "Collections",
  },
  {
    match: (pathname: string) => pathname.startsWith("/folders"),
    title: "Folder Browser",
    subtitle: "Drill through the indexed archive one directory at a time and inspect direct children without recursive spillover.",
    eyebrow: "Archive",
  },
  {
    match: (pathname: string) => pathname.startsWith("/settings"),
    title: "System Settings",
    subtitle: "Manage embedding provider credentials and switch the active retrieval backend without restarting the app.",
    eyebrow: "Configuration",
  },
];

function SidebarContent({ onNavigate, onLogout }: { onNavigate?: () => void; onLogout: () => void }) {
  return (
    <>
      <div className="space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] uppercase tracking-[0.24em] text-primary/90">
          <Sparkles className="h-3.5 w-3.5" />
          Curated Admin
        </div>
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] p-2 shadow-inset">
              <img src={logoMark} alt="Image Search logo" className="h-full w-full object-contain" />
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-white">Image Search</h1>
          </div>
          <p className="max-w-xs text-sm leading-6 text-muted-foreground">
            A quiet workspace for indexing, searching, and organizing a living image archive.
          </p>
        </div>
      </div>

      <div className="mt-10 space-y-2">
        <div className="px-3 text-[11px] uppercase tracking-[0.24em] text-muted-foreground/80">
          Navigation
        </div>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "group relative flex items-center gap-3 overflow-hidden rounded-2xl px-3 py-3 text-sm transition-all duration-200",
                isActive
                  ? "bg-white/[0.08] text-white shadow-inset"
                  : "text-muted-foreground hover:bg-white/[0.045] hover:text-white",
              )
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={cn(
                    "absolute inset-y-3 left-0 w-1 rounded-full bg-primary transition-opacity",
                    isActive ? "opacity-100" : "opacity-0",
                  )}
                />
                <item.icon className={cn("h-4 w-4", isActive ? "text-primary" : "text-muted-foreground")} />
                <span className="font-medium">{item.label}</span>
                <ArrowUpRight
                  className={cn(
                    "ml-auto h-3.5 w-3.5 transition-all",
                    isActive ? "translate-x-0 opacity-100 text-primary" : "translate-x-1 opacity-0 group-hover:translate-x-0 group-hover:opacity-100",
                  )}
                />
              </>
            )}
          </NavLink>
        ))}
      </div>

      <div className="mt-10 rounded-[28px] border border-white/10 bg-white/[0.035] p-4">
        <div className="flex items-center gap-3">
          <div className="rounded-2xl bg-primary/15 p-2 text-primary">
            <Database className="h-4 w-4" />
          </div>
          <div>
            <p className="text-sm font-medium text-white">Index workspace</p>
            <p className="text-xs text-muted-foreground">Default dark curation theme enabled</p>
          </div>
        </div>
      </div>

      <div className="mt-auto">
        <button
          onClick={onLogout}
          className="flex w-full items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.03] px-3 py-3 text-sm text-muted-foreground transition-colors hover:bg-white/[0.06] hover:text-white"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </>
  );
}

export default function Layout() {
  const logout = useLogout();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const meta = pageMeta.find((item) => item.match(location.pathname)) ?? {
    title: "Image Search",
    subtitle: "A curated workspace for image retrieval and archive management.",
    eyebrow: "Workspace",
  };

  // Close mobile menu on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  async function handleLogout() {
    setMobileOpen(false);
    await logout.mutateAsync();
    navigate("/login", { replace: true });
  }

  return (
    <div className="flex min-h-screen bg-transparent text-foreground">
      {/* Desktop sidebar */}
      <aside className="hidden w-72 shrink-0 border-r border-white/8 bg-sidebar/85 p-6 shadow-curator backdrop-blur xl:flex xl:flex-col">
        <SidebarContent onLogout={handleLogout} />
      </aside>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm xl:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile drawer */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-white/8 bg-sidebar p-6 shadow-curator transition-transform duration-300 xl:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <button
          onClick={() => setMobileOpen(false)}
          className="absolute right-4 top-4 rounded-xl p-2 text-muted-foreground transition-colors hover:bg-white/[0.06] hover:text-white"
        >
          <X className="h-5 w-5" />
        </button>
        <SidebarContent onNavigate={() => setMobileOpen(false)} onLogout={handleLogout} />
      </aside>

      <main className="flex-1 overflow-auto">
        <div className="mx-auto flex min-h-screen w-full max-w-[1600px] flex-col px-4 py-4 sm:px-6 lg:px-8">
          <header className="mb-6 overflow-hidden rounded-[30px] border border-white/10 bg-card/80 px-5 py-5 shadow-curator backdrop-blur sm:px-7">
            <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  {/* Mobile menu button */}
                  <button
                    onClick={() => setMobileOpen(true)}
                    className="rounded-xl border border-white/10 bg-white/[0.04] p-2 text-muted-foreground transition-colors hover:bg-white/[0.08] hover:text-white xl:hidden"
                  >
                    <Menu className="h-5 w-5" />
                  </button>
                  <p className="text-[11px] uppercase tracking-[0.26em] text-primary/90">{meta.eyebrow}</p>
                </div>
                <div className="space-y-2">
                  <h2 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                    {meta.title}
                  </h2>
                  <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
                    {meta.subtitle}
                  </p>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 lg:w-[360px]">
                <div className="rounded-3xl border border-white/10 bg-white/[0.04] px-4 py-4">
                  <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Mode</p>
                  <p className="mt-2 text-sm font-medium text-white">Search Workspace</p>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">Operate the archive as a visual editing surface, not a generic dashboard.</p>
                </div>
                <div className="rounded-3xl border border-primary/20 bg-primary/10 px-4 py-4">
                  <p className="text-[11px] uppercase tracking-[0.2em] text-primary/80">Theme</p>
                  <p className="mt-2 text-sm font-medium text-white">Dark Curation</p>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">Quiet chrome, brighter imagery, and one accent channel for decisions.</p>
                </div>
              </div>
            </div>
          </header>

          <div className="flex-1">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  );
}
