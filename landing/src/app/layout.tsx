import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'SAAS Software — Shaping Agencies of Tomorrow',
  description: 'The All-In-One Software Powering the Future of PR Agencies.',
  icons: [{ rel: 'icon', url: '/favicon.svg' }],
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}

