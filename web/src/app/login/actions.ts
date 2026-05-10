'use server'

import { redirect } from 'next/navigation'
import { headers } from 'next/headers'
import { z } from 'zod'
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
  const configured = process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, '')
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

export async function signOut() {
  const supabase = await createClient()
  await supabase.auth.signOut()
  redirect('/login')
}
