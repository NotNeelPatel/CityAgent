import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_OR_ANON_KEY
)

export const BACKEND_URL = import.meta.env.BACKEND_URL || 'http://127.0.0.1:8000';