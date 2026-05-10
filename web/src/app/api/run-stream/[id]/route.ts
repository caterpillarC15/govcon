import { NextResponse, type NextRequest } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { getApiBase } from '@/lib/api'

export const dynamic = 'force-dynamic'

type Params = { id: string }

export async function GET(
  request: NextRequest,
  context: { params: Promise<Params> },
) {
  const { id } = await context.params
  const supabase = await createClient()
  const {
    data: { session },
  } = await supabase.auth.getSession()
  if (!session) {
    return new NextResponse('Unauthorized', { status: 401 })
  }

  const upstream = await fetch(`${getApiBase()}/agent-runs/${id}/stream`, {
    headers: {
      Authorization: `Bearer ${session.access_token}`,
      Accept: 'text/event-stream',
    },
    cache: 'no-store',
    signal: request.signal,
  })

  if (!upstream.ok || !upstream.body) {
    return new NextResponse(`Upstream error ${upstream.status}`, {
      status: upstream.status,
    })
  }

  return new NextResponse(upstream.body, {
    status: 200,
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  })
}
