import { ChevronRight } from 'lucide-react'
import DashboardPreview from '@/components/DashboardPreview'
import Navbar from '@/components/Navbar'

const VIDEO_URL =
  'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260424_064411_9e9d7f84-9277-41f4-ab10-59172d89e6be.mp4'
const POSTER_URL =
  'https://images.unsplash.com/photo-1557683316-973673baf926?w=1600&q=60'

export default function Landing() {
  return (
    <main
      className="min-h-screen w-full p-3 sm:p-4"
      style={{
        backgroundColor: '#ededed',
        fontFamily:
          "'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      }}
    >
      <section
        className="relative w-full h-[calc(100vh-24px)] sm:h-[calc(100vh-32px)] overflow-hidden rounded-2xl sm:rounded-3xl"
        style={{ backgroundColor: '#d9d9d9' }}
      >
        <video
          className="absolute inset-0 w-full h-full object-cover pointer-events-none"
          src={VIDEO_URL}
          poster={POSTER_URL}
          autoPlay
          loop
          muted
          playsInline
          preload="auto"
          // @ts-expect-error non-standard mobile video attributes
          disableRemotePlayback="true"
          webkit-playsinline="true"
          x5-playsinline="true"
        />

        <div className="absolute inset-0 bg-white/10" />

        <div className="relative z-10 flex flex-col">
          <Navbar />

          <div className="flex flex-col items-center px-4 pt-10 sm:pt-16 pb-8 sm:pb-12 text-center">
            <span
              className="inline-flex items-center gap-2 bg-white rounded-full px-4 py-1.5 shadow-sm"
              style={{ fontSize: 13 }}
            >
              <span
                className="inline-block rounded-full"
                style={{
                  width: 8,
                  height: 8,
                  backgroundColor: '#ef4d23',
                }}
              />
              <span className="text-neutral-800">Convix Software</span>
            </span>

            <h1
              className="mt-5 sm:mt-6 max-w-4xl text-neutral-900"
              style={{
                fontSize: 'clamp(36px, 8vw, 72px)',
                lineHeight: 1.05,
                fontWeight: 500,
                letterSpacing: '-0.02em',
              }}
            >
              {'Shaping '}
              <span
                style={{
                  fontFamily: "'Instrument Serif', serif",
                  fontStyle: 'italic',
                  fontWeight: 400,
                }}
              >
                Agencies
              </span>
              <br />
              of tomorrow
            </h1>

            <p
              className="mt-4 sm:mt-6 text-neutral-700 px-2"
              style={{ fontSize: 'clamp(13px, 3.5vw, 16px)' }}
            >
              The All-In-One Software Powering the Future of PR Agencies
            </p>

            <button
              type="button"
              className="mt-6 sm:mt-8 inline-flex items-center gap-3 text-white rounded-full pl-6 sm:pl-7 pr-2 py-2 sm:py-2.5"
              style={{ backgroundColor: '#0b0f1a', fontSize: 14 }}
            >
              <span>Get Started</span>
              <span className="inline-flex items-center justify-center w-6 h-6 sm:w-7 sm:h-7 rounded-full bg-white/15">
                <ChevronRight size={16} strokeWidth={2} className="w-4 h-4" />
              </span>
            </button>
          </div>

          <DashboardPreview />
        </div>
      </section>
    </main>
  )
}

