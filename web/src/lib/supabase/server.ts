import { cookies } from 'next/headers'
import { createServerClient } from '@supabase/ssr'
import { getSupabaseBrowserEnv } from './env'

export async function createClient() {
  const { url, anonKey } = getSupabaseBrowserEnv()
  const cookieStore = await cookies()

  return createServerClient(url, anonKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll()
      },
      setAll(cookiesToSet) {
        try {
          cookiesToSet.forEach(({ name, value, options }) => {
            cookieStore.set(name, value, options)
          })
        } catch {
          // Server Components cannot always mutate cookies. Middleware and
          // server actions refresh sessions where mutation is available.
        }
      },
    },
  })
}
