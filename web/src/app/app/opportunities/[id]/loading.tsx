import { Card } from '@/components/Card'
import { Skeleton } from '@/components/Skeleton'

export default function Loading() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-4 w-20" />
      <div>
        <Skeleton className="h-3 w-32" />
        <Skeleton className="mt-2 h-7 w-3/4" />
        <Skeleton className="mt-1 h-4 w-2/3" />
      </div>
      <Card>
        <Skeleton className="h-4 w-24" />
        <Skeleton className="mt-3 h-20 w-full" />
      </Card>
      <Card>
        <Skeleton className="h-4 w-16" />
        <Skeleton className="mt-3 h-12 w-32" />
      </Card>
    </div>
  )
}
