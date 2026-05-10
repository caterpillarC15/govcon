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
  title: {
    default: 'GovCon Bid Desk · AI bid-desk operator',
    template: '%s · GovCon Bid Desk',
  },
  description:
    'Hire an AI operator that finds contracts worth bidding, qualifies opportunities, and drafts the bid plan.',
  icons: [{ rel: 'icon', url: '/favicon.svg' }],
  openGraph: {
    title: 'GovCon Bid Desk',
    description: 'AI bid-desk operator for government contracting teams.',
    siteName: 'GovCon Bid Desk',
    type: 'website',
  },
}

export const viewport: Viewport = {
  // Match the warm-canvas body color (--color-canvas-warm) so the mobile
  // browser chrome blends with the page; was '#0f172a' which produced a
  // dark slate bar against the light design.
  themeColor: '#fafaf7',
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
