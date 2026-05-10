'use client'

import { useEffect } from 'react'
import { Card } from '@/components/Card'
import { PageHeader } from '@/components/PageHeader'

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Error"
        title="That page didn't load"
        subtitle={
          error.digest
            ? `Error id: ${error.digest}`
            : 'Try again, or head back to the dashboard.'
        }
      />
      <Card className="border-rose-200 bg-rose-50/80 text-sm text-rose-900">
        {error.message || 'Unknown error.'}
      </Card>
      <button
        type="button"
        onClick={() => reset()}
        className="inline-flex h-10 items-center gap-2 rounded-full bg-slate-950 px-4 text-sm font-medium text-white transition hover:bg-slate-800"
      >
        Try again
      </button>
    </div>
  )
}
