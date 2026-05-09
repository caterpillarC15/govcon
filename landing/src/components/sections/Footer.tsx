import { FOOTER, NAV, PRODUCT } from '../../data/copy'

export default function Footer() {
  return (
    <footer className="relative w-full">
      <div className="mx-auto max-w-[1200px] px-5 sm:px-8 pb-8">
        <div className="glass-rule" aria-hidden />
        <div className="pt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <span className="text-[12px] text-[var(--color-ink-muted)]">
            <span className="text-[var(--color-ink)] font-medium">{PRODUCT.fullName}</span>
            <span className="mx-2 text-[var(--color-ink-subtle)]">·</span>
            {FOOTER.blurb}
            <span className="mx-2 text-[var(--color-ink-subtle)]">·</span>© {new Date().getFullYear()}
          </span>
          <nav className="flex flex-wrap gap-x-5 gap-y-2" aria-label="Footer">
            {NAV.map((n) => (
              <a
                key={n.href}
                href={n.href}
                className="text-[12px] text-[var(--color-ink-muted)] hover:text-[var(--color-ink)] transition-colors"
              >
                {n.label}
              </a>
            ))}
            <a
              href="#waitlist"
              className="text-[12px] text-[var(--color-ink)] font-medium hover:text-[var(--color-accent)] transition-colors"
            >
              Request access
            </a>
          </nav>
        </div>
        <p className="mt-3 text-[11px] text-[var(--color-ink-subtle)] leading-snug">
          {FOOTER.legal}
        </p>
      </div>
    </footer>
  )
}
