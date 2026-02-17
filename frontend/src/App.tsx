import { Routes, Route, useLocation } from "react-router-dom";
import { Login } from "@/pages/Login";
import { Search } from "@/pages/Search";
import { Dashboard } from "@/pages/Dashboard";
import { ProtectedRoute } from "@/routes/ProtectedRoute";
import { PublicRoute } from "@/routes/PublicRoute";

function App() {
  const location = useLocation();

  return (
    <div className="">
      <Routes>
        <Route element={<PublicRoute />}>
          <Route path="/" element={<Login />} />
          <Route path="/login" element={<Login />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route path="/search" element={<Search key={location.key} />} />
          {/* add more protected pages here later */}
        </Route>

        <Route element={<ProtectedRoute allow={["admin"]} />}>
          <Route path="/dashboard" element={<Dashboard />} />
        </Route>
      </Routes>
    </div>
  );
}

export default App;