import { redirect } from 'next/navigation'
import { maybeSupabaseBrowserEnv } from '@/lib/supabase/env'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

export default async function Home() {
  // If Supabase isn't configured, route to /login — the page renders a clear
  // error state rather than throwing during RSC render.
  if (!maybeSupabaseBrowserEnv()) {
    redirect('/login?error=Supabase+is+not+configured.')
  }
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  redirect(user ? '/app' : '/login')
}
