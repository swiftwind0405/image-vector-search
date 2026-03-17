import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import DashboardPage from "./pages/DashboardPage";
import TagsPage from "./pages/TagsPage";
import CategoriesPage from "./pages/CategoriesPage";
import ImagesPage from "./pages/ImagesPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="tags" element={<TagsPage />} />
        <Route path="categories" element={<CategoriesPage />} />
        <Route path="images" element={<ImagesPage />} />
      </Route>
    </Routes>
  );
}
