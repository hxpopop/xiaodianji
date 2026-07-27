export type DecimalWire = string | number
export type TargetType = 'quote' | 'transaction' | 'payment'
export type PaymentStatus = 'paid' | 'unpaid'
export type ConfirmationStatus = 'pending' | 'confirmed' | 'confirmed_after_edit' | 'cancelled'
export type EvidenceType = 'audio' | 'image' | 'text'

export interface LineItemDraft {
  product: string
  spec?: string | null
  quantity: number
  unit: string
  unit_price: number
  subtotal: number
}

export interface TransactionDraft {
  target_type: 'transaction'
  customer_name: string
  customer_id?: string | null
  occurred_at: string
  payment_status: PaymentStatus
  items: LineItemDraft[]
  total_amount: number
  source_evidence_id?: string | null
}

export interface QuoteDraft {
  target_type: 'quote'
  customer_name: string
  customer_id?: string | null
  quoted_at: string
  items: LineItemDraft[]
  total_amount: number
  source_evidence_id?: string | null
}

export interface PaymentDraft {
  target_type: 'payment'
  customer_name: string
  customer_id?: string | null
  paid_at: string
  amount: number
  source_evidence_id?: string | null
}

export type RecordDraft = TransactionDraft | QuoteDraft | PaymentDraft

export interface ConfirmationRead {
  id: string
  shop_id: string
  target_type: TargetType
  status: ConfirmationStatus
  effective_json: RecordDraft
  field_confidences: Record<string, string>
  formal_record_type: string | null
  formal_record_id: string | null
}

export interface EvidenceRead {
  id: string
  type: EvidenceType
  status: string
  original_filename: string | null
  mime_type: string
  size_bytes: number
  asr_text: string | null
  access_url: string | null
}

export interface QueryResponse {
  answer: string
  amount: string | null
  calculation_basis: string | null
  details: Array<Record<string, unknown>>
  evidence_ids: string[]
  ambiguity: {
    candidates?: Array<{ customer_id: string; name: string; score: DecimalWire; matched_on: string }>
  } | null
}

export interface CustomerSummary {
  id: string
  name: string
  aliases: string[]
}

export interface ReminderItem {
  customer_id: string
  customer_name: string
  due_at: string
  balance: DecimalWire
  overdue_transaction_count: number
  overdue_days: number
}

export interface ReminderSummary {
  overdue_count: number
  items: ReminderItem[]
}

export interface EvaluationScore {
  correct: number
  total: number
  accuracy: DecimalWire
}

export interface EvaluationMetrics {
  customer: EvaluationScore
  products: EvaluationScore
  quantities: EvaluationScore
  amounts: EvaluationScore
  payment_status: EvaluationScore
  case_count: number
  failed_case_count: number
  average_latency_ms: DecimalWire
}

export interface EvaluationRunRead {
  id: string
  shop_id: string
  model_name: string
  started_at: string
  finished_at: string | null
  metrics: EvaluationMetrics
  case_count: number
  failed_case_count: number
  average_latency_ms: DecimalWire
}

export type VoiceAudioInput =
  | Blob
  | { path: string; filename?: string; mimeType?: string }
