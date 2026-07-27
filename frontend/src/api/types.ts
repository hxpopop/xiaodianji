export type DecimalWire = string | number
export type TargetType = 'quote' | 'transaction' | 'payment'
export type PaymentStatus = 'paid' | 'unpaid'
export type ConfirmationStatus = 'pending' | 'confirmed' | 'confirmed_after_edit' | 'cancelled'
export interface LineItemDraft { product: string; spec?: string | null; quantity: number; unit: string; unit_price: number; subtotal: number }
export interface TransactionDraft { target_type:'transaction'; customer_name:string; customer_id?:string|null; occurred_at:string; payment_status:PaymentStatus; items:LineItemDraft[]; total_amount:number; source_evidence_id?:string|null }
export interface QuoteDraft { target_type:'quote'; customer_name:string; customer_id?:string|null; quoted_at:string; items:LineItemDraft[]; total_amount:number; source_evidence_id?:string|null }
export interface PaymentDraft { target_type:'payment'; customer_name:string; customer_id?:string|null; paid_at:string; amount:number; source_evidence_id?:string|null }
export type RecordDraft=TransactionDraft|QuoteDraft|PaymentDraft
export interface ConfirmationRead { id:string;shop_id:string;target_type:TargetType;status:ConfirmationStatus;effective_json:RecordDraft;field_confidences:Record<string,string>;formal_record_type:string|null;formal_record_id:string|null }
export interface EvidenceRead { id:string; type:string; status:string; original_filename:string|null; mime_type:string; size_bytes:number; asr_text:string|null; access_url:string|null }
export interface ReminderItem {customer_id:string;customer_name:string;due_at:string;balance:number;overdue_transaction_count:number;overdue_days:number}
export interface ReminderSummary {overdue_count:number;items:ReminderItem[]}
