import { redirect } from 'next/navigation'
import { signOut } from '../login/actions'
import { createClient } from '@/lib/supabase/server'
import AppConsole from './AppConsole'

export const dynamic = 'force-dynamic'

export default async function AppPage() {
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
            <p className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500">
              GovCapture
            </p>
            <h1 className="mt-1 text-2xl font-semibold tracking-normal">
              Michaela bid desk
            </h1>
            <p className="mt-1 text-sm text-slate-600">{user.email}</p>
          </div>
          <form action={signOut}>
            <button
              type="submit"
              className="h-10 rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-800"
            >
              Sign out
            </button>
          </form>
        </header>

        <AppConsole />
      </div>
    </main>
  )
}
