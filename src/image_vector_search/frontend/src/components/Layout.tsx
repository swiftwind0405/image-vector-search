import { useState, useEffect } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Tag,
  Folder,
  ImagePlus,
  Search,
  LogOut,
  Settings,
  LayoutGrid,
  Menu,
  X,
} from "lucide-react";
import { useLogout } from "@/api/auth";
import { cn } from "@/lib/utils";
import logoMark from "../../logo.svg";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/search", icon: Search, label: "Search" },
  { to: "/tags", icon: Tag, label: "Tags" },
  { to: "/albums", icon: LayoutGrid, label: "Albums" },
  { to: "/folders", icon: Folder, label: "Folders" },
  { to: "/images", icon: ImagePlus, label: "Images" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

const pageMeta = [
  { match: (p: string) => p === "/", title: "Collection Overview" },
  { match: (p: string) => p.startsWith("/search"), title: "Search Workspace" },
  { match: (p: string) => p === "/images", title: "Image Library" },
  { match: (p: string) => p.startsWith("/tags"), title: "Tag Index" },
  { match: (p: string) => p.startsWith("/albums"), title: "Album Collections" },
  { match: (p: string) => p.startsWith("/folders"), title: "Folder Browser" },
  { match: (p: string) => p.startsWith("/settings"), title: "System Settings" },
];

function SidebarContent({
  onNavigate,
  onLogout,
}: {
  onNavigate?: () => void;
  onLogout: () => void;
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 px-5 pt-5 pb-6">
        <div className="flex h-7 w-7 items-center justify-center rounded-md border border-border bg-white">
          <img src={logoMark} alt="Image Search logo" className="h-4 w-4 object-contain" />
        </div>
        <span className="text-[13px] font-semibold tracking-tight text-foreground">
          Image Search
        </span>
      </div>

      <nav className="flex-1 space-y-0.5 px-3">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-[13px] transition-colors",
                isActive
                  ? "bg-[#f1f1f3] text-foreground font-medium"
                  : "text-muted-foreground hover:bg-[#f4f4f5] hover:text-foreground",
              )
            }
          >
            {({ isActive }) => (
              <>
                <item.icon
                  className={cn(
                    "h-4 w-4",
                    isActive ? "text-foreground" : "text-muted-foreground",
                  )}
                  strokeWidth={isActive ? 2 : 1.75}
                />
                <span>{item.label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-border px-3 py-3">
        <button
          onClick={onLogout}
          className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-[13px] text-muted-foreground transition-colors hover:bg-[#f4f4f5] hover:text-foreground"
        >
          <LogOut className="h-4 w-4" strokeWidth={1.75} />
          Sign out
        </button>
      </div>
    </div>
  );
}

export default function Layout() {
  const logout = useLogout();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const meta =
    pageMeta.find((item) => item.match(location.pathname)) ?? { title: "Image Search" };

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  async function handleLogout() {
    setMobileOpen(false);
    await logout.mutateAsync();
    navigate("/login", { replace: true });
  }

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 self-start border-r border-border bg-sidebar xl:flex xl:flex-col">
        <SidebarContent onLogout={handleLogout} />
      </aside>

      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/20 xl:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-60 flex-col border-r border-border bg-sidebar transition-transform duration-200 xl:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <button
          onClick={() => setMobileOpen(false)}
          className="absolute right-3 top-3 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-[#f4f4f5] hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
        <SidebarContent onNavigate={() => setMobileOpen(false)} onLogout={handleLogout} />
      </aside>

      <main className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border bg-background/80 px-4 sm:px-6">
          <button
            onClick={() => setMobileOpen(true)}
            className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-[#f4f4f5] hover:text-foreground xl:hidden"
          >
            <Menu className="h-4 w-4" />
          </button>
          <h2 className="text-[13px] font-medium tracking-tight text-foreground">
            {meta.title}
          </h2>
        </header>

        <div className="mx-auto w-full max-w-[1400px] px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
