import { Navigate, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import DashboardPage from "./pages/DashboardPage";
import TagsPage from "./pages/TagsPage";
import CategoriesPage from "./pages/CategoriesPage";
import ImagesPage from "./pages/ImagesPage";
import FoldersPage from "./pages/FoldersPage";
import AlbumsPage from "./pages/AlbumsPage";
import AlbumImagesPage from "./pages/AlbumImagesPage";
import TagImagesPage from "./pages/TagImagesPage";
import CategoryImagesPage from "./pages/CategoryImagesPage";
import SearchPage from "./pages/SearchPage";
import LoginPage from "./pages/LoginPage";
import SettingsPage from "./pages/SettingsPage";
import { useAuthMe } from "./api/auth";

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { data, isLoading } = useAuthMe();
  if (isLoading) return null;
  if (!data?.authenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <AuthGuard>
            <Layout />
          </AuthGuard>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="tags" element={<TagsPage />} />
        <Route path="tags/:tagId/images" element={<TagImagesPage />} />
        <Route path="categories" element={<CategoriesPage />} />
        <Route path="categories/:categoryId/images" element={<CategoryImagesPage />} />
        <Route path="folders" element={<FoldersPage />} />
        <Route path="albums" element={<AlbumsPage />} />
        <Route path="albums/:albumId/images" element={<AlbumImagesPage />} />
        <Route path="images" element={<ImagesPage />} />
        <Route path="search" element={<SearchPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
