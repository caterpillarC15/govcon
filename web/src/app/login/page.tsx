import Link from 'next/link'
import { signIn, signInWithGoogle } from './actions'
import { SubmitButton } from './SubmitButton'
import { GoogleButton } from './GoogleButton'
import { Mark } from '@/components/Mark'
import { ErrorBanner, inputClass } from '@/components/Field'

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
    <main className="relative min-h-screen w-full">
      <div className="mx-auto flex min-h-screen w-full max-w-md flex-col justify-center px-5 py-12">
        <Link
          href="/"
          aria-label="GovCon Bid Desk — home"
          className="mb-7 inline-flex items-center gap-2 self-start rounded-full focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
        >
          <Mark />
          <span className="text-[14px] font-medium tracking-tight text-[var(--color-ink)]">
            GovCon Bid Desk
          </span>
        </Link>

        <div className="glass-strong rounded-[var(--radius-card)] p-7">
          <p className="text-[12px] font-medium uppercase tracking-[0.14em] text-[var(--color-ink-muted)]">
            Sign in or create your account
          </p>
          <h1 className="mt-3 text-[30px] font-semibold leading-[1.05] tracking-[-0.01em] text-[var(--color-ink)]">
            Sign in to the bid desk
          </h1>
          <p className="mt-3 text-[14px] leading-[1.55] text-[var(--color-ink-muted)]">
            New here? We&apos;ll create your account automatically — no separate
            signup step.
          </p>

          {sent ? (
            <div className="mt-6 space-y-4">
              <div className="glass-subtle rounded-2xl px-4 py-3 text-[13.5px] leading-[1.55] text-[var(--color-ink)]">
                <p className="font-semibold">Magic link sent.</p>
                <p className="mt-1 text-[var(--color-ink-muted)]">
                  Check your inbox and click the link to sign in. The link
                  works once and expires after 5 minutes.
                </p>
              </div>
              <Link
                href="/login"
                className="block text-center text-[13px] font-medium text-[var(--color-accent)] underline-offset-4 hover:underline"
              >
                Use a different method
              </Link>
            </div>
          ) : (
            <>
              <form action={signInWithGoogle} className="mt-6">
                <input type="hidden" name="next" value={next} />
                <GoogleButton />
              </form>

              <div className="my-5 flex items-center gap-3" aria-hidden>
                <div className="h-px flex-1 bg-[var(--color-paper-line)]" />
                <span className="text-[11.5px] font-medium uppercase tracking-[0.12em] text-[var(--color-ink-subtle)]">
                  or with email
                </span>
                <div className="h-px flex-1 bg-[var(--color-paper-line)]" />
              </div>

              <form action={signIn} className="space-y-3">
                <input type="hidden" name="next" value={next} />
                <label className="block">
                  <span className="text-[12.5px] font-medium text-[var(--color-ink)]">
                    Work email
                  </span>
                  <input
                    name="email"
                    type="email"
                    required
                    autoComplete="email"
                    placeholder="you@company.com"
                    className={inputClass}
                  />
                </label>
                <SubmitButton label="Send magic link" />
                <p className="pt-1 text-center text-[11.5px] text-[var(--color-ink-subtle)]">
                  No password — we&apos;ll email you a one-time link.
                </p>
              </form>
            </>
          )}

          {params.error ? (
            <div className="mt-4">
              <ErrorBanner message={params.error} />
            </div>
          ) : null}
        </div>

        <p className="mt-6 text-center text-[12.5px] text-[var(--color-ink-subtle)]">
          By signing in you agree to our{' '}
          <Link
            href="/terms"
            className="underline underline-offset-2 hover:text-[var(--color-ink)]"
          >
            terms
          </Link>{' '}
          and{' '}
          <Link
            href="/privacy"
            className="underline underline-offset-2 hover:text-[var(--color-ink)]"
          >
            privacy policy
          </Link>
          .
        </p>
      </div>
    </main>
  )
}
