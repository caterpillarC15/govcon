'use server'

import { redirect } from 'next/navigation'
import { headers } from 'next/headers'
import { z } from 'zod'
import { createClient as createServiceClient } from '@supabase/supabase-js'
import { createClient } from '@/lib/supabase/server'

function safeNext(value: FormDataEntryValue | null) {
  const next = typeof value === 'string' && value.startsWith('/') ? value : '/app'
  return next.startsWith('//') ? '/app' : next
}

const emailSchema = z.string().email().max(254)

const OTP_WINDOW_MS = 60_000
const OTP_MAX_PER_WINDOW = 3
const otpHits = new Map<string, number[]>()

function rateLimited(key: string) {
  const now = Date.now()
  const recent = (otpHits.get(key) ?? []).filter((t) => now - t < OTP_WINDOW_MS)
  if (recent.length >= OTP_MAX_PER_WINDOW) {
    otpHits.set(key, recent)
    return true
  }
  recent.push(now)
  otpHits.set(key, recent)
  return false
}

async function originUrl() {
  // The magic-link callback route lives in /web (this app), not in
  // /landing. NEXT_PUBLIC_APP_URL points at /web; NEXT_PUBLIC_SITE_URL
  // points at /landing. Reading SITE_URL here was the bug — the link
  // would hit landing's :3000, which doesn't have /auth/callback.
  const configured = process.env.NEXT_PUBLIC_APP_URL?.replace(/\/$/, '')
  if (configured) return configured
  return (await headers()).get('origin') || 'http://localhost:3001'
}

export async function signIn(formData: FormData) {
  const rawEmail = String(formData.get('email') ?? '').trim().toLowerCase()
  const next = safeNext(formData.get('next'))

  const parsed = emailSchema.safeParse(rawEmail)
  if (!parsed.success) {
    redirect(`/login?error=${encodeURIComponent('Enter a valid work email.')}`)
  }
  const email = parsed.data

  const hdrs = await headers()
  const ip =
    hdrs.get('x-forwarded-for')?.split(',')[0]?.trim() ||
    hdrs.get('x-real-ip') ||
    'unknown'
  if (rateLimited(`${ip}:${email}`)) {
    redirect(
      `/login?error=${encodeURIComponent(
        'Too many magic-link requests. Wait a minute and try again.',
      )}`,
    )
  }

  const origin = await originUrl()
  const supabase = await createClient()
  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: {
      emailRedirectTo: `${origin}/auth/callback?next=${encodeURIComponent(next)}`,
    },
  })

  if (error) {
    redirect(`/login?error=${encodeURIComponent(error.message)}`)
  }

  redirect(`/login?sent=1&next=${encodeURIComponent(next)}`)
}

export async function signInWithGoogle(formData: FormData) {
  const next = safeNext(formData.get('next'))
  const origin = await originUrl()
  const supabase = await createClient()

  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: `${origin}/auth/callback?next=${encodeURIComponent(next)}`,
      // Force account chooser so users on shared devices can switch.
      queryParams: { access_type: 'offline', prompt: 'select_account' },
    },
  })

  if (error || !data?.url) {
    redirect(
      `/login?error=${encodeURIComponent(
        error?.message ||
          'Google sign-in is not configured. Use email magic link.',
      )}`,
    )
  }

  redirect(data.url)
}

// Dev-only: skip the magic-link round-trip entirely. Idempotently
// ensures a dev user exists with a known password, then signInWithPassword
// to drop a session cookie. Two server-side gates (env var ALLOW_DEV_LOGIN
// must be 'true', and SUPABASE_SERVICE_ROLE_KEY must be present) plus the
// page-level conditional render mean this can't be triggered in prod
// even if the form data leaks.
export async function signInAsDev() {
  if (process.env.ALLOW_DEV_LOGIN !== 'true') {
    redirect('/login?error=Dev+login+is+disabled')
  }
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!url || !serviceKey) {
    redirect('/login?error=SUPABASE_SERVICE_ROLE_KEY+missing+for+dev+login')
  }

  const email = process.env.DEV_USER_EMAIL || 'dev@local.test'
  const password = process.env.DEV_USER_PASSWORD || 'devonly-not-for-prod'

  // Service-role admin client — server-only, no session cookies.
  const admin = createServiceClient(url, serviceKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  })

  // Idempotent user creation. Ignore "already exists" / "already registered"
  // — anything else surfaces as a redirect with the error.
  const { error: createErr } = await admin.auth.admin.createUser({
    email,
    password,
    email_confirm: true,
    user_metadata: { dev_account: true },
  })
  if (
    createErr &&
    !/already (registered|exists|been registered)/i.test(createErr.message)
  ) {
    redirect(
      `/login?error=${encodeURIComponent(`Dev user create failed: ${createErr.message}`)}`,
    )
  }

  // Now sign in with password using the user-facing (anon-key) client so
  // session cookies land on the response.
  const supabase = await createClient()
  const { error } = await supabase.auth.signInWithPassword({ email, password })
  if (error) {
    redirect(
      `/login?error=${encodeURIComponent(`Dev sign-in failed: ${error.message}`)}`,
    )
  }

  redirect('/app')
}

export async function signOut() {
  const supabase = await createClient()
  await supabase.auth.signOut()
  redirect('/login')
}
