import type {
  ConfirmationRead,
  CustomerSummary,
  EvaluationRunRead,
  EvidenceRead,
  QueryResponse,
  RecordDraft,
  ReminderSummary,
  VoiceAudioInput,
} from './types'

const baseUrl = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')

export class ApiRequestError extends Error {
  fallback?: string

  constructor(message: string, fallback?: string) {
    super(message)
    this.name = 'ApiRequestError'
    this.fallback = fallback
  }
}

const mapError = (detail: string) => (
  detail.includes('AI service')
    ? '智能识别暂时不可用，请改用手动输入。'
    : detail.includes('not found')
      ? '记录不存在或已失效，请返回重新输入。'
      : detail.includes('conflict')
        ? '这笔记录已处理，请刷新后查看。'
        : '服务暂时不可用，请稍后重试或改用手动输入。'
)

const requestId = () => (
  globalThis.crypto?.randomUUID?.()
  || `xdj-${Date.now()}-${Math.random().toString(16).slice(2)}`
)

const num = (value: unknown) => (
  typeof value === 'string' ? Number(value) : typeof value === 'number' ? value : 0
)

export function normalizeConfirmation(raw: any): ConfirmationRead {
  const draft = raw.effective_json
  const items = Array.isArray(draft.items)
    ? draft.items.map((item: any) => ({
        ...item,
        quantity: num(item.quantity),
        unit_price: num(item.unit_price),
        subtotal: num(item.subtotal),
      }))
    : undefined
  return {
    ...raw,
    effective_json: items
      ? { ...draft, items, total_amount: num(draft.total_amount) }
      : draft.target_type === 'payment'
        ? { ...draft, amount: num(draft.amount) }
        : draft,
  }
}

function errorFromBody(body: any) {
  const detail = typeof body?.detail === 'string' ? body.detail : ''
  return new ApiRequestError(mapError(detail), typeof body?.fallback === 'string' ? body.fallback : undefined)
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: { Accept: 'application/json', ...init.headers },
  })
  const body = await response.json().catch(() => null)
  if (!response.ok) throw errorFromBody(body)
  return body as T
}

function shopHeaders(shopId: string, idempotencyKey?: string) {
  if (!shopId) {
    throw new Error('尚未配置商户，请联系管理员设置商户信息后再记账。')
  }
  return {
    'X-Shop-Id': shopId,
    ...(idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}),
  }
}

function uploadVoicePath(
  shopId: string,
  audio: Extract<VoiceAudioInput, { path: string }>,
  idempotencyKey: string,
): Promise<ConfirmationRead> {
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: `${baseUrl}/records/voice`,
      filePath: audio.path,
      name: 'file',
      header: {
        Accept: 'application/json',
        ...shopHeaders(shopId, idempotencyKey),
      },
      formData: {},
      success(result) {
        let body: any = null
        try {
          body = JSON.parse(result.data)
        } catch {
          reject(new ApiRequestError('服务返回了无法读取的数据，请改用手动输入。', 'manual_form'))
          return
        }
        if (result.statusCode < 200 || result.statusCode >= 300) {
          reject(errorFromBody(body))
          return
        }
        resolve(normalizeConfirmation(body))
      },
      fail() {
        reject(new ApiRequestError('语音上传失败，请检查网络后重试或改用手动输入。', 'manual_form'))
      },
    })
  })
}

async function createVoiceDraft(
  shopId: string,
  audio: VoiceAudioInput,
  idempotencyKey = requestId(),
) {
  if (!(audio instanceof Blob)) {
    return uploadVoicePath(shopId, audio, idempotencyKey)
  }
  const form = new FormData()
  form.append('file', audio, 'recording.mp3')
  return request<any>('/records/voice', {
    method: 'POST',
    headers: shopHeaders(shopId, idempotencyKey),
    body: form,
  }).then(normalizeConfirmation)
}

export const apiClient = {
  createTextDraft: (shopId: string, text: string, idempotencyKey = requestId()) => (
    request<any>('/records/text', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...shopHeaders(shopId, idempotencyKey) },
      body: JSON.stringify({ text }),
    }).then(normalizeConfirmation)
  ),
  createManualDraft: (shopId: string, draft: RecordDraft, idempotencyKey = requestId()) => (
    request<any>('/records/manual', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...shopHeaders(shopId, idempotencyKey) },
      body: JSON.stringify(draft),
    }).then(normalizeConfirmation)
  ),
  createVoiceDraft,
  getConfirmation: (recordId: string) => (
    request<any>(`/confirmations/${recordId}`).then(normalizeConfirmation)
  ),
  updateConfirmation: (recordId: string, draft: RecordDraft) => (
    request<any>(`/confirmations/${recordId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(draft),
    }).then(normalizeConfirmation)
  ),
  confirmConfirmation: (recordId: string, idempotencyKey = requestId()) => (
    request<any>(`/confirmations/${recordId}/confirm`, {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
    }).then(normalizeConfirmation)
  ),
  cancelConfirmation: (recordId: string, idempotencyKey = requestId()) => (
    request<any>(`/confirmations/${recordId}/cancel`, {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
    }).then(normalizeConfirmation)
  ),
  getEvidence: (shopId: string, evidenceId: string) => (
    request<EvidenceRead>(`/evidences/${evidenceId}`, {
      headers: shopHeaders(shopId),
    })
  ),
  query: (shopId: string, question: string) => (
    request<QueryResponse>('/queries', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...shopHeaders(shopId) },
      body: JSON.stringify({ question }),
    })
  ),
  getCustomers: (shopId: string) => (
    request<CustomerSummary[]>('/customers', { headers: shopHeaders(shopId) })
  ),
  getReminders: (shopId: string) => (
    request<ReminderSummary>('/reminders', { headers: shopHeaders(shopId) })
  ),
  runEvaluation: (shopId: string) => (
    request<EvaluationRunRead>('/evaluations/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...shopHeaders(shopId) },
      body: JSON.stringify({ model_name: 'configured' }),
    })
  ),
}
