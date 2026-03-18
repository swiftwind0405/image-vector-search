import { NavLink, Outlet } from "react-router-dom";
import { LayoutDashboard, Tag, FolderTree, ImagePlus, Search } from "lucide-react";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/search", icon: Search, label: "Search" },
  { to: "/tags", icon: Tag, label: "Tags" },
  { to: "/categories", icon: FolderTree, label: "Categories" },
  { to: "/images", icon: ImagePlus, label: "Images" },
];

export default function Layout() {
  return (
    <div className="flex h-screen bg-gray-50">
      <aside className="w-56 border-r bg-white p-4 flex flex-col gap-1">
        <h1 className="text-lg font-semibold mb-4 px-2">Image Search</h1>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-2 rounded-md px-2 py-1.5 text-sm ${
                isActive
                  ? "bg-gray-100 font-medium text-gray-900"
                  : "text-gray-600 hover:bg-gray-50"
              }`
            }
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        ))}
      </aside>
      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
