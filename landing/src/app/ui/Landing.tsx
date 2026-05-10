import Background from '@/components/Background'
import Navbar from '@/components/Navbar'
import Hero from '@/components/sections/Hero'
import StoryCards from '@/components/sections/StoryCards'
import TrustStrip from '@/components/sections/TrustStrip'
import Waitlist from '@/components/sections/Waitlist'
import Footer from '@/components/sections/Footer'

export default function Landing() {
  return (
    <div className="relative min-h-screen w-full text-[var(--color-ink)]">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-[var(--color-ink)] focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-white focus:outline-2 focus:outline-offset-2 focus:outline-[var(--color-accent)]"
      >
        Skip to main content
      </a>
      <Background />
      <div className="relative z-10">
        <Navbar />
        <main id="main" tabIndex={-1}>
          <Hero />
          <StoryCards />
          <TrustStrip />
          <Waitlist />
        </main>
        <Footer />
      </div>
    </div>
  )
}
