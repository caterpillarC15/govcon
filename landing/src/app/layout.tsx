import type { Metadata, Viewport } from 'next'
import { GeistSans } from 'geist/font/sans'
import { GeistMono } from 'geist/font/mono'
import { Instrument_Serif } from 'next/font/google'
import './globals.css'

const instrumentSerif = Instrument_Serif({
  weight: '400',
  style: ['normal', 'italic'],
  subsets: ['latin'],
  variable: '--font-instrument-serif',
  display: 'swap',
})

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
    <html
      lang="en"
      className={`${GeistSans.variable} ${GeistMono.variable} ${instrumentSerif.variable}`}
    >
      <body>{children}</body>
    </html>
  )
}
