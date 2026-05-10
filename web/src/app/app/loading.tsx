import { Card } from '@/components/Card'
import { Skeleton } from '@/components/Skeleton'

export default function Loading() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-3 w-24" />
        <Skeleton className="mt-2 h-7 w-48" />
        <Skeleton className="mt-1 h-4 w-72" />
      </div>
      <Card>
        <Skeleton className="h-4 w-32" />
        <Skeleton className="mt-2 h-6 w-20" />
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      </Card>
    </div>
  )
}
