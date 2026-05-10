import Link from 'next/link'
import { signIn } from './actions'
import { SubmitButton } from './SubmitButton'

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
  const sent = params.sent === '1'

  return (
    <main className="min-h-screen bg-[#f7f8fb] text-slate-950">
      <div className="mx-auto flex min-h-screen w-full max-w-md flex-col justify-center px-6 py-12">
        <div className="rounded-[28px] border border-white/80 bg-white/72 p-7 shadow-[0_24px_70px_-36px_rgba(15,23,42,0.42)] backdrop-blur-2xl">
          <p className="text-sm font-medium text-blue-900">GovCapture private beta</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-normal">
            Sign in to the bid desk
          </h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Enter your work email and we&apos;ll send a magic link. We don&apos;t use
            passwords.
          </p>

          {!sent && (
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
              <SubmitButton label="Send magic link" />
            </form>
          )}

          {sent && (
            <div className="mt-6 space-y-4">
              <div className="rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
                <p className="font-medium">Magic link sent.</p>
                <p className="mt-1">
                  Check your inbox and click the link to sign in. The link works
                  once and expires after 5 minutes.
                </p>
              </div>
              <Link
                href="/login"
                className="block text-center text-sm font-medium text-blue-900 underline-offset-4 hover:underline"
              >
                Use a different email
              </Link>
            </div>
          )}

          {params.error && (
            <p
              className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-900"
              role="alert"
            >
              {params.error}
            </p>
          )}
        </div>
      </div>
    </main>
  )
}
