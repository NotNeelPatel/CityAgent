import { Routes, Route } from "react-router-dom";
import { Login } from "@/pages/Login";
import { Search } from "@/pages/Search";
import { Upload } from "@/pages/Upload";
import { ProtectedRoute } from "@/routes/ProtectedRoute";
import { PublicRoute } from "@/routes/PublicRoute";

function App() {
  return (
    <div className="min-h-svh">
      <Routes>
        <Route element={<PublicRoute />}>
          <Route path="/" element={<Login />} />
          <Route path="/login" element={<Login />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route path="/search" element={<Search />} />
          <Route path="/upload" element={<Upload />} />
          {/* add more protected pages here later */}
        </Route>
      </Routes>
    </div>
  );
}

export default App;