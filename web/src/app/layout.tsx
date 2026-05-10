import './globals.css'

export const metadata = {
  title: 'GovCapture App',
  description: 'Authenticated GovCapture bid-desk workspace.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
