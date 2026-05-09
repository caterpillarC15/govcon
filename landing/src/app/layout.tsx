import type { Metadata, Viewport } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'GovCapture Agent — First-pass capture analyst for federal contracts',
  description:
    'GovCapture Agent reads federal solicitations, extracts requirements with evidence, scores fit against your company profile, and produces a reviewable action package. Human approval required before any external action.',
  icons: [{ rel: 'icon', url: '/favicon.svg' }],
  openGraph: {
    title: 'GovCapture Agent',
    description:
      'An autonomous capture analyst for small businesses pursuing federal contracts. Source-cited requirements, conservative eligibility, human-in-the-loop.',
    type: 'website',
  },
}

export const viewport: Viewport = {
  themeColor: '#0f172a',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
