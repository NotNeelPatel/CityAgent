import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_OR_ANON_KEY
)

export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:8000"

export async function fetchData(path: string, init: RequestInit = {}) {
  const { data, error } = await supabase.auth.getSession()
  if (error || !data.session?.access_token) {
    throw new Error("Not authenticated. Please sign in again.")
  }

  const headers = new Headers(init.headers)
  headers.set("Authorization", `Bearer ${data.session.access_token}`)

  return fetch(`${BACKEND_URL}${path}`, {
    ...init,
    headers,
  })
}
