import { Button } from "@/components/ui/button"
import { Routes, Route, Link } from "react-router-dom";
import { Login } from "./pages/Login";
import { Signup } from "./pages/Signup";
import { Search } from "./pages/Search";

function App() {
  return (
    <div className="min-h-svh">
      {/* Router output */}
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/search" element={<Search />} />
      </Routes>

    </div>
  )
}

export default App