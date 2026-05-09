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
      <Background />
      <div className="relative z-10">
        <Navbar />
        <main>
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
