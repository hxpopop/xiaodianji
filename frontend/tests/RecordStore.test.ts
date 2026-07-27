import { describe, expect, it, vi } from 'vitest'
import { RecordStore } from '../src/stores/record'

const confirmation = { id: 'c-1', shop_id: '00000000-0000-0000-0000-000000000001', target_type: 'transaction' as const, status: 'pending' as const, effective_json: { target_type: 'transaction' as const, customer_name: '王老板', occurred_at: '2026-07-27T09:00:00+08:00', payment_status: 'unpaid' as const, items: [{ product: '水泥', quantity: 2, unit: '袋', unit_price: 20, subtotal: 40 }], total_amount: 40 }, field_confidences: {}, formal_record_type: null, formal_record_id: null }

describe('RecordStore resolution workflow', () => {
  it('awaits PATCH before confirming an edited draft', async () => {
    const events: string[] = []
    const client = { updateConfirmation: vi.fn(async () => { events.push('patch'); return confirmation }), confirmConfirmation: vi.fn(async () => { events.push('confirm'); return { ...confirmation, status: 'confirmed_after_edit' as const } }) }
    const store = new RecordStore(client, confirmation.shop_id)
    store.state.draft = confirmation
    await store.resolveDraft({ ...confirmation.effective_json, items: [{ ...confirmation.effective_json.items[0], quantity: 10, subtotal: 200 }], total_amount: 200 }, true)
    expect(events).toEqual(['patch', 'confirm'])
  })

  it('confirms an unchanged draft without PATCH', async () => {
    const client = { updateConfirmation: vi.fn(), confirmConfirmation: vi.fn(async () => ({ ...confirmation, status: 'confirmed' as const })) }
    const store = new RecordStore(client, confirmation.shop_id)
    store.state.draft = confirmation
    await store.resolveDraft(confirmation.effective_json, false)
    expect(client.updateConfirmation).not.toHaveBeenCalled()
    expect(client.confirmConfirmation).toHaveBeenCalledOnce()
  })

  it('uses the dedicated cancel endpoint', async () => {
    const client = { cancelConfirmation: vi.fn(async () => ({ ...confirmation, status: 'cancelled' as const })) }
    const store = new RecordStore(client, confirmation.shop_id)
    store.state.draft = confirmation
    await store.cancelDraft()
    expect(client.cancelConfirmation).toHaveBeenCalledWith('c-1')
  })
})
