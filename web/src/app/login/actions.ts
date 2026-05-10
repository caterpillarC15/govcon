'use server'

import { redirect } from 'next/navigation'
import { headers } from 'next/headers'
import { createClient } from '@/lib/supabase/server'

function safeNext(value: FormDataEntryValue | null) {
  const next = typeof value === 'string' && value.startsWith('/') ? value : '/app'
  return next.startsWith('//') ? '/app' : next
}

export async function signIn(formData: FormData) {
  const email = String(formData.get('email') ?? '')
    .trim()
    .toLowerCase()
  const next = safeNext(formData.get('next'))

  if (!email) {
    redirect(`/login?error=${encodeURIComponent('Enter a work email.')}`)
  }

  const origin = (await headers()).get('origin') ?? 'http://localhost:3001'
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

export async function signOut() {
  const supabase = await createClient()
  await supabase.auth.signOut()
  redirect('/login')
}
