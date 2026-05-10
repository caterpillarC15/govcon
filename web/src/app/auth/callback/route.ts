import { NextResponse, type NextRequest } from 'next/server'
import { createClient } from '@/lib/supabase/server'

function safeNext(value: string | null) {
  if (!value || !value.startsWith('/') || value.startsWith('//')) return '/app'
  return value
}

export async function GET(request: NextRequest) {
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const oauthError = requestUrl.searchParams.get('error')
  const oauthErrorDescription = requestUrl.searchParams.get('error_description')
  const next = safeNext(requestUrl.searchParams.get('next'))

  // Provider returned an error (e.g. user denied consent, app not on the
  // OAuth consent screen's Test users list, mismatched redirect URI).
  // Surface the real reason instead of the generic magic-link message.
  if (oauthError) {
    const message = oauthErrorDescription || oauthError
    return NextResponse.redirect(
      new URL(
        `/login?error=${encodeURIComponent(`Sign-in failed: ${message}`)}&next=${encodeURIComponent(next)}`,
        requestUrl.origin,
      ),
    )
  }

  if (!code) {
    return NextResponse.redirect(
      new URL(
        `/login?error=${encodeURIComponent(
          'Sign-in callback missing auth code. Try again or use email magic link.',
        )}&next=${encodeURIComponent(next)}`,
        requestUrl.origin,
      ),
    )
  }

  const supabase = await createClient()
  const { error } = await supabase.auth.exchangeCodeForSession(code)
  if (error) {
    return NextResponse.redirect(
      new URL(
        `/login?error=${encodeURIComponent(`Sign-in failed: ${error.message}`)}&next=${encodeURIComponent(next)}`,
        requestUrl.origin,
      ),
    )
  }

  return NextResponse.redirect(new URL(next, requestUrl.origin))
}
