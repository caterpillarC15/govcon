import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'
import { maybeSupabaseBrowserEnv } from '@/lib/supabase/env'

export async function middleware(request: NextRequest) {
  const response = NextResponse.next({ request })
  const pathname = request.nextUrl.pathname
  const env = maybeSupabaseBrowserEnv()

  if (!env) {
    if (pathname.startsWith('/app')) {
      const loginUrl = request.nextUrl.clone()
      loginUrl.pathname = '/login'
      loginUrl.searchParams.set('next', pathname)
      loginUrl.searchParams.set('error', 'Supabase env is not configured.')
      return NextResponse.redirect(loginUrl)
    }
    return response
  }

  const supabase = createServerClient(
    env.url,
    env.anonKey,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) => {
            request.cookies.set(name, value)
            response.cookies.set(name, value, options)
          })
        },
      },
    },
  )

  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (pathname.startsWith('/app') && !user) {
    const loginUrl = request.nextUrl.clone()
    loginUrl.pathname = '/login'
    loginUrl.searchParams.set('next', pathname)
    // Preserve cookie writes (incl. token-refresh) from setAll() on the
    // existing response — a fresh NextResponse.redirect() drops them.
    const redirect = NextResponse.redirect(loginUrl)
    response.cookies.getAll().forEach((c) => {
      redirect.cookies.set(c.name, c.value)
    })
    return redirect
  }

  if (pathname === '/login' && user) {
    const redirect = NextResponse.redirect(new URL('/app', request.url))
    response.cookies.getAll().forEach((c) => {
      redirect.cookies.set(c.name, c.value)
    })
    return redirect
  }

  return response
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}
