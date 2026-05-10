import type {
  ActionPackage,
  AgentRun,
  ApiKey,
  ApiKeyMint,
  CompanyProfile,
  ExtractedRequirement,
  FitScore,
  Opportunity,
  RiskFlag,
} from './types'

/**
 * Payload accepted by POST /company-profiles.
 *
 * Omits server-generated fields. If a caller passes id/created_at/
 * updated_at, the API rejects with 422 — having a separate type
 * surfaces that mistake at compile-time instead.
 */
export type CreateCompanyProfilePayload = Omit<
  CompanyProfile,
  'id' | 'created_at' | 'updated_at'
>

export function getApiBase() {
  return (process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000').replace(
    /\/$/,
    '',
  )
}

export class ApiError extends Error {
  status: number
  body: unknown
  constructor(status: number, message: string, body?: unknown) {
    super(message)
    this.status = status
    this.body = body
  }
}

async function request<T>(
  path: string,
  token: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${getApiBase()}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...init.headers,
    },
    cache: 'no-store',
  })
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    const message =
      typeof body === 'object' &&
      body &&
      'detail' in body &&
      typeof (body as { detail: unknown }).detail === 'string'
        ? (body as { detail: string }).detail
        : `Request failed (${response.status})`
    throw new ApiError(response.status, message, body)
  }
  if (response.status === 204) {
    return null as T
  }
  return (await response.json()) as T
}

export const api = {
  listCompanyProfiles: (token: string) =>
    request<CompanyProfile[]>('/company-profiles', token),
  getCompanyProfile: (token: string, id: string) =>
    request<CompanyProfile>(`/company-profiles/${id}`, token),
  createCompanyProfile: (token: string, payload: CreateCompanyProfilePayload) =>
    request<CompanyProfile>('/company-profiles', token, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  createAgentRun: (
    token: string,
    payload: { goal: string; profile_id?: string; profile?: CreateCompanyProfilePayload },
  ) =>
    request<AgentRun>('/agent-runs', token, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getAgentRun: (token: string, id: string) =>
    request<AgentRun>(`/agent-runs/${id}`, token),
  listAgentRunOpportunities: (token: string, id: string) =>
    request<Opportunity[]>(`/agent-runs/${id}/opportunities`, token),

  getOpportunity: (token: string, id: string) =>
    request<Opportunity>(`/opportunities/${id}`, token),
  getOpportunityRequirements: (token: string, id: string) =>
    request<ExtractedRequirement[]>(`/opportunities/${id}/requirements`, token),
  getOpportunityFitScore: (token: string, id: string) =>
    request<FitScore>(`/opportunities/${id}/fit-score`, token),
  getOpportunityRisks: (token: string, id: string) =>
    request<RiskFlag[]>(`/opportunities/${id}/risks`, token),

  getActionPackage: (token: string, id: string) =>
    request<ActionPackage>(`/action-packages/${id}`, token),
  approveActionPackage: (token: string, id: string) =>
    request<ActionPackage>(`/action-packages/${id}/approve`, token, {
      method: 'POST',
    }),

  listApiKeys: (token: string) => request<ApiKey[]>('/api/keys', token),

  mintApiKey: (token: string, name: string) =>
    request<ApiKeyMint>('/api/keys', token, {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),

  revokeApiKey: (token: string, id: string) =>
    request<null>(`/api/keys/${id}`, token, { method: 'DELETE' }),
}
