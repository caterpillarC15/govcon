import { PageHeader } from '@/components/PageHeader'
import { Card } from '@/components/Card'
import { ProfileForm } from './ProfileForm'

export const dynamic = 'force-dynamic'

export default function NewProfilePage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Profile"
        title="Create a company profile"
        subtitle="Capabilities, NAICS, certifications, and clearance — used by Gate (eligibility) and Lenny (fit ranking)."
      />
      <Card>
        <ProfileForm />
      </Card>
    </div>
  )
}
