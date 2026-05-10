import { Card } from '@/components/Card'
import { Skeleton } from '@/components/Skeleton'

export default function Loading() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-4 w-20" />
      <div>
        <Skeleton className="h-3 w-12" />
        <Skeleton className="mt-2 h-7 w-3/4" />
        <Skeleton className="mt-1 h-4 w-48" />
      </div>
      <Card>
        <div className="flex gap-3">
          <Skeleton className="h-7 w-7 rounded-full" />
          <div className="flex-1">
            <Skeleton className="h-3 w-12" />
            <Skeleton className="mt-1 h-5 w-40" />
          </div>
        </div>
        <div className="mt-5 space-y-3">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      </Card>
    </div>
  )
}
