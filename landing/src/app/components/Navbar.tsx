import { useState } from 'react'
import { ChevronDown, ChevronRight, Menu, ShoppingCart, X } from 'lucide-react'

const NAV_ITEMS = [
  { label: 'Home', kind: 'home' as const },
  { label: 'Features', kind: 'plain' as const },
  { label: 'About', kind: 'plain' as const },
  { label: 'Pages', kind: 'pages' as const },
]

function Logo() {
  // 8-petal flower: 8 outer circles around center (16,16) at radius 10,
  // plus a center circle. All circles r=3.5. viewBox 32x32.
  const cx = 16
  const cy = 16
  const r = 10
  const petals = Array.from({ length: 8 }, (_, i) => {
    const angle = (i / 8) * Math.PI * 2
    return {
      cx: cx + r * Math.cos(angle),
      cy: cy + r * Math.sin(angle),
    }
  })
  return (
    <svg
      viewBox="0 0 32 32"
      className="w-7 h-7 sm:w-8 sm:h-8 shrink-0"
      aria-hidden="true"
    >
      {petals.map((p, i) => (
        <circle key={i} cx={p.cx} cy={p.cy} r={3.5} fill="#ef4d23" />
      ))}
      <circle cx={cx} cy={cy} r={3.5} fill="#ef4d23" />
    </svg>
  )
}

function NavLink({ item }: { item: (typeof NAV_ITEMS)[number] }) {
  if (item.kind === 'home') {
    return (
      <a
        href="#"
        className="flex items-center gap-1.5 text-neutral-900"
        style={{ fontSize: 14 }}
      >
        <span
          className="inline-block rounded-full bg-black"
          style={{ width: 6, height: 6 }}
        />
        Home
      </a>
    )
  }
  if (item.kind === 'pages') {
    return (
      <a
        href="#"
        className="flex items-center gap-1"
        style={{ color: '#ef4d23', fontSize: 14 }}
      >
        Pages
        <ChevronDown size={14} strokeWidth={2} />
      </a>
    )
  }
  return (
    <a
      href="#"
      className="text-neutral-900"
      style={{ fontSize: 14 }}
    >
      {item.label}
    </a>
  )
}

export default function Navbar() {
  const [open, setOpen] = useState(false)

  return (
    <div className="flex justify-center pt-4 sm:pt-6 px-3 sm:px-4">
      <div className="bg-white rounded-full shadow-sm border border-neutral-200 pl-2 pr-2 py-2 w-full max-w-[760px] relative">
        <div className="flex items-center gap-3">
          <a href="#" className="flex items-center shrink-0 pl-1">
            <Logo />
          </a>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-6 pl-3">
            {NAV_ITEMS.map((item) => (
              <NavLink key={item.label} item={item} />
            ))}
          </nav>

          {/* Right cluster */}
          <div className="ml-auto flex items-center gap-2">
            <button
              type="button"
              aria-label="Cart"
              className="hidden md:flex w-9 h-9 items-center justify-center rounded-full text-neutral-900 hover:bg-neutral-100"
            >
              <ShoppingCart size={18} strokeWidth={1.75} />
            </button>

            <button
              type="button"
              className="hidden sm:inline-flex items-center gap-2 rounded-full text-white pl-4 pr-1 py-1"
              style={{ backgroundColor: '#ef4d23', fontSize: 13 }}
            >
              <span className="hidden md:inline">Get early access</span>
              <span className="md:hidden">Early access</span>
              <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-white/20">
                <ChevronRight size={14} strokeWidth={2.25} />
              </span>
            </button>

            <button
              type="button"
              className="sm:hidden inline-flex items-center gap-2 rounded-full text-white pl-3 pr-1 py-1"
              style={{ backgroundColor: '#ef4d23', fontSize: 13 }}
            >
              <span>Early access</span>
              <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-white/20">
                <ChevronRight size={12} strokeWidth={2.25} />
              </span>
            </button>

            {/* Mobile menu toggle */}
            <button
              type="button"
              aria-label="Toggle menu"
              aria-expanded={open}
              onClick={() => setOpen((v) => !v)}
              className="md:hidden w-9 h-9 inline-flex items-center justify-center rounded-full text-neutral-900 hover:bg-neutral-100"
            >
              {open ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </div>

        {open && (
          <div className="absolute top-full left-2 right-2 mt-2 bg-white rounded-2xl shadow-lg border border-neutral-200 p-3 z-20 md:hidden">
            <ul className="flex flex-col">
              {NAV_ITEMS.map((item) => (
                <li
                  key={item.label}
                  className="px-2 py-2 border-b border-neutral-100 last:border-b-0"
                >
                  <NavLink item={item} />
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
