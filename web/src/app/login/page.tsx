import { signIn } from './actions'

type LoginSearchParams = {
  sent?: string
  error?: string
  next?: string
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<LoginSearchParams>
}) {
  const params = await searchParams
  const next = params.next && params.next.startsWith('/') ? params.next : '/app'

  return (
    <main className="min-h-screen bg-[#f7f8fb] text-slate-950">
      <div className="mx-auto flex min-h-screen w-full max-w-md flex-col justify-center px-6 py-12">
        <div className="rounded-[28px] border border-white/80 bg-white/72 p-7 shadow-[0_24px_70px_-36px_rgba(15,23,42,0.42)] backdrop-blur-2xl">
          <p className="text-sm font-medium text-blue-900">GovCapture private beta</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-normal">
            Sign in to the bid desk
          </h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Use the email attached to your Supabase Auth account. GovCapture sends
            a magic link and keeps the app shell behind an authenticated session.
          </p>

          <form action={signIn} className="mt-6 space-y-4">
            <input type="hidden" name="next" value={next} />
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Work email</span>
              <input
                name="email"
                type="email"
                required
                autoComplete="email"
                placeholder="you@company.com"
                className="mt-2 h-11 w-full rounded-full border border-slate-200 bg-white px-4 text-sm text-slate-950 outline-none transition focus:border-blue-800 focus:ring-2 focus:ring-blue-800/20"
              />
            </label>
            <button
              type="submit"
              className="h-11 w-full rounded-full bg-slate-950 px-5 text-sm font-medium text-white transition hover:bg-slate-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-800"
            >
              Send magic link
            </button>
          </form>

          {params.sent && (
            <p className="mt-4 rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
              Magic link sent. Check your inbox, then return here after sign-in.
            </p>
          )}

          {params.error && (
            <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-900">
              {params.error}
            </p>
          )}
        </div>
      </div>
    </main>
  )
}
