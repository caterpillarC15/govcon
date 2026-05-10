import { redirect } from 'next/navigation'
import Link from 'next/link'
import { signOut } from '../login/actions'
import { createClient } from '@/lib/supabase/server'
import { Mark } from '@/components/Mark'

export const dynamic = 'force-dynamic'

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  return (
    <main className="relative min-h-screen w-full">
      <header className="sticky top-0 z-30 w-full">
        <div className="flex justify-center px-3 pt-4 sm:px-4 sm:pt-6">
          <div className="glass-nav relative w-full max-w-[960px] rounded-full py-2 pl-2 pr-2">
            <div className="flex items-center gap-3">
              <Link
                href="/app"
                className="flex shrink-0 items-center gap-2 rounded-full pl-1 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
                aria-label="SamRail — dashboard"
              >
                <Mark />
                <span className="hidden text-[14px] font-medium tracking-tight text-[var(--color-ink)] sm:inline">
                  SamRail
                </span>
              </Link>

              <nav
                className="ml-2 hidden items-center gap-5 md:flex"
                aria-label="Primary"
              >
                <Link
                  href="/app/profile"
                  className="rounded-full text-[13px] text-[var(--color-ink-muted)] transition-colors hover:text-[var(--color-ink)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
                >
                  Profiles
                </Link>
                <Link
                  href="/app/keys"
                  className="rounded-full text-[13px] text-[var(--color-ink-muted)] transition-colors hover:text-[var(--color-ink)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
                >
                  API keys
                </Link>
              </nav>

              <div className="ml-auto flex items-center gap-2">
                <span
                  className="hidden max-w-[200px] truncate text-[12.5px] text-[var(--color-ink-muted)] md:inline"
                  title={user.email ?? undefined}
                >
                  {user.email}
                </span>
                <form action={signOut}>
                  <button
                    type="submit"
                    className="inline-flex h-9 items-center rounded-full px-3 text-[13px] font-medium text-[var(--color-ink-muted)] transition-colors hover:bg-white/50 hover:text-[var(--color-ink)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
                  >
                    Sign out
                  </button>
                </form>
              </div>
            </div>
          </div>
        </div>

        {/* Mobile section pills (md-): keep section nav reachable. */}
        <nav
          aria-label="Sections"
          className="mx-auto mt-3 flex w-full max-w-[960px] items-center gap-2 px-5 md:hidden"
        >
          <Link
            href="/app/profile"
            className="glass-subtle rounded-full px-3 py-1.5 text-[12.5px] font-medium text-[var(--color-ink)]"
          >
            Profiles
          </Link>
          <Link
            href="/app/keys"
            className="glass-subtle rounded-full px-3 py-1.5 text-[12.5px] font-medium text-[var(--color-ink)]"
          >
            API keys
          </Link>
        </nav>
      </header>

      <div className="mx-auto w-full max-w-[960px] px-5 py-8 sm:px-8">
        {children}
      </div>
    </main>
  )
}
