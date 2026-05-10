import { redirect } from 'next/navigation'
import Link from 'next/link'
import { signOut } from '../login/actions'
import { createClient } from '@/lib/supabase/server'

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
    <main className="min-h-screen bg-[#f7f8fb] text-slate-950">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-5 py-6 sm:px-8">
        <header className="flex flex-col gap-4 rounded-[28px] border border-white/80 bg-white/72 p-5 shadow-[0_24px_70px_-44px_rgba(15,23,42,0.44)] backdrop-blur-2xl sm:flex-row sm:items-center sm:justify-between">
          <div>
            <Link
              href="/app"
              className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500 transition hover:text-slate-700"
            >
              GovCapture
            </Link>
            <h1 className="mt-1 text-2xl font-semibold tracking-normal">
              Michaela bid desk
            </h1>
            <p className="mt-1 text-sm text-slate-600">{user.email}</p>
          </div>
          <nav className="flex items-center gap-2">
            <Link
              href="/app/profile"
              className="grid h-10 place-items-center rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            >
              Profiles
            </Link>
            <form action={signOut}>
              <button
                type="submit"
                className="h-10 rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
              >
                Sign out
              </button>
            </form>
          </nav>
        </header>
        {children}
      </div>
    </main>
  )
}
