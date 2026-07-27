import { reactive } from 'vue'
import { apiClient } from '../api/client'
import type { ConfirmationRead, RecordDraft } from '../api/types'

const defaultShopId = import.meta.env.VITE_SHOP_ID || ''

export class RecordStore {
  state = reactive({ shopId: defaultShopId, draft: null as ConfirmationRead | null, error: '', saving: false })
  setShopId(shopId: string) { this.state.shopId = shopId }
  private adopt(draft: ConfirmationRead) { this.state.draft = draft; this.state.error = ''; return draft }
  async createTextDraft(text: string) { return this.run(() => apiClient.createTextDraft(this.state.shopId, text)) }
  async createManualDraft(draft: RecordDraft) { return this.run(() => apiClient.createManualDraft(this.state.shopId, draft)) }
  async updateDraft(draft: RecordDraft) {
    if (!this.state.draft) throw new Error('没有可修改的待确认记录。')
    return this.run(() => apiClient.updateConfirmation(this.state.draft!.id, draft))
  }
  async confirmDraft() {
    if (!this.state.draft) throw new Error('没有可确认的待确认记录。')
    return this.run(() => apiClient.confirmConfirmation(this.state.draft!.id))
  }
  async cancelDraft() {
    if (!this.state.draft) throw new Error('没有可取消的待确认记录。')
    return this.run(() => apiClient.cancelConfirmation(this.state.draft!.id))
  }
  private async run(action: () => Promise<ConfirmationRead>) {
    this.state.saving = true
    try { return this.adopt(await action()) }
    catch (error) { this.state.error = error instanceof Error ? error.message : '操作未完成，请改用手动输入。'; throw error }
    finally { this.state.saving = false }
  }
}

export const recordStore = new RecordStore()
