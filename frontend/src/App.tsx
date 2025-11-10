import { Link } from 'react-router-dom';
import { Button } from "@/components/ui/button"

function App() {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center">
      <h1 className="text-5xl mb-10">Welcome to cityagent</h1>

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