import { Button } from "@/components/ui/button"
import { Routes, Route, Link } from "react-router-dom";
import { Login } from "./pages/Login";
import { Signup } from "./pages/Signup";

function App() {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center">
      <h1 className="text-5xl mb-10">Welcome to CityAgent</h1>
       {/* Router output */}
      <div className="mb-16">
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
        </Routes>
      </div>
      <h2 className="text-2xl mt-10 mb-5">Helpful links</h2>
      <div className='flex gap-2'>
        <Button asChild>
          <Link to="https://ui.shadcn.com/docs/components" target='_blank'>shadcn components</Link>
        </Button>

        <Button asChild>
          <Link to="https://tailwindcss.com/" target='_blank'>Tailwind CSS</Link>
        </Button>
      </div>

    </div>
  )
}

export default App