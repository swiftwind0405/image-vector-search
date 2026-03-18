import { Navigate, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import DashboardPage from "./pages/DashboardPage";
import TagsPage from "./pages/TagsPage";
import CategoriesPage from "./pages/CategoriesPage";
import ImagesPage from "./pages/ImagesPage";
import SearchPage from "./pages/SearchPage";
import LoginPage from "./pages/LoginPage";
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
        <Route path="categories" element={<CategoriesPage />} />
        <Route path="images" element={<ImagesPage />} />
        <Route path="search" element={<SearchPage />} />
      </Route>
    </Routes>
  );
}
