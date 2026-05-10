import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'

/**
 * Validate the user server-side and return both the user and the
 * bearer token for FastAPI calls. Redirects to /login if no valid
 * session.
 *
 * Use this in every server component / route handler that needs to
 * make an authenticated call to the FastAPI backend.
 *
 * Why getUser() not getSession(): per Supabase SSR docs, getSession()
 * only locally decodes the JWT — an expired or forged token passes
 * silently. getUser() makes a network round-trip to /auth/v1/user
 * and is the only path that actually validates identity on the server.
 */
export async function requireUser() {
  const supabase = await createClient()
  const {
    data: { user },
    error: userErr,
  } = await supabase.auth.getUser()
  if (userErr || !user) {
    redirect('/login')
  }
  // Safe to read the session locally for the access token now that
  // getUser() validated it. The middleware will have refreshed
  // expiring tokens before this runs.
  const {
    data: { session },
  } = await supabase.auth.getSession()
  if (!session?.access_token) {
    redirect('/login')
  }
  return { user, token: session.access_token }
}
