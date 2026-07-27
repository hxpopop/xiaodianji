import type { ConfirmationRead, RecordDraft, ReminderSummary } from './types'

const baseUrl = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')

function requestId() {
  return globalThis.crypto?.randomUUID?.() || `xdj-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: { Accept: 'application/json', ...init.headers },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : ''
    throw new Error(detail || '服务暂时不可用，请稍后重试或改用手动输入。')
  }
  return response.json() as Promise<T>
}

function shopHeaders(shopId: string, idempotencyKey = requestId()) {
  return { 'X-Shop-Id': shopId, 'Idempotency-Key': idempotencyKey }
}

export const apiClient = {
  createTextDraft(shopId: string, text: string, idempotencyKey = requestId()) {
    return request<ConfirmationRead>('/records/text', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...shopHeaders(shopId, idempotencyKey) },
      body: JSON.stringify({ text }),
    })
  },
  createManualDraft(shopId: string, draft: RecordDraft, idempotencyKey = requestId()) {
    return request<ConfirmationRead>('/records/manual', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...shopHeaders(shopId, idempotencyKey) },
      body: JSON.stringify(draft),
    })
  },
  getConfirmation(id: string) { return request<ConfirmationRead>(`/confirmations/${id}`) },
  updateConfirmation(id: string, draft: RecordDraft) {
    return request<ConfirmationRead>(`/confirmations/${id}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(draft),
    })
  },
  confirmConfirmation(id: string, idempotencyKey = requestId()) {
    return request<ConfirmationRead>(`/confirmations/${id}/confirm`, { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey } })
  },
  cancelConfirmation(id: string, idempotencyKey = requestId()) {
    return request<ConfirmationRead>(`/confirmations/${id}/cancel`, { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey } })
  },
  getReminders(shopId: string) { return request<ReminderSummary>('/reminders', { headers: { 'X-Shop-Id': shopId } }) },
}
