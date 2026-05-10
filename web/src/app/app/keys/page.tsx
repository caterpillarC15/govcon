import { requireUser } from '@/lib/supabase/auth'
import { api, ApiError } from '@/lib/api'
import { PageHeader } from '@/components/PageHeader'
import { Card } from '@/components/Card'
import type { ApiKey } from '@/lib/types'
import { KeysClient } from './KeysClient'

export const dynamic = 'force-dynamic'

export default async function KeysPage() {
  const { token } = await requireUser()

  let keys: ApiKey[] = []
  let loadError: string | null = null
  try {
    keys = await api.listApiKeys(token)
  } catch (err) {
    loadError = err instanceof ApiError ? err.message : 'Could not load keys.'
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Agent keys"
        title="API keys"
        subtitle="Per-agent gck_… keys. Use these to call /api/v1/tools/<name> from your agent. Mint here, copy ONCE, store securely."
      />
      {loadError ? (
        <Card className="border-red-200 bg-red-50/80 text-sm text-red-900">
          {loadError}
        </Card>
      ) : null}
      <KeysClient initial={keys} />
    </div>
  )
}
