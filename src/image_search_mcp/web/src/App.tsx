import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";

function DashboardPage() {
  return <div>Dashboard — coming soon</div>;
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
      </Route>
    </Routes>
  );
}
