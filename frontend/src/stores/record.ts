import { reactive } from 'vue'
import { apiClient } from '../api/client'
import type { ConfirmationRead, RecordDraft } from '../api/types'
const defaultShopId = import.meta.env.VITE_SHOP_ID || '00000000-0000-0000-0000-000000000001'
export class RecordStore {
  state
  constructor(private readonly client: any = apiClient, shopId = defaultShopId) { this.state = reactive({ shopId, draft: null as ConfirmationRead | null, error: '', saving: false }) }
  setShopId(shopId: string) { this.state.shopId = shopId }
  private adopt(draft: ConfirmationRead) { this.state.draft = draft; this.state.error = ''; return draft }
  async createTextDraft(text: string) { return this.run(() => this.client.createTextDraft(this.state.shopId, text)) }
  async createManualDraft(draft: RecordDraft) { return this.run(() => this.client.createManualDraft(this.state.shopId, draft)) }
  async updateDraft(draft: RecordDraft) { const current = this.state.draft; if (!current) throw new Error('没有可修改的待确认记录。'); return this.run(() => this.client.updateConfirmation(current.id, draft)) }
  async confirmDraft() { const current = this.state.draft; if (!current) throw new Error('没有可确认的待确认记录。'); return this.run(() => this.client.confirmConfirmation(current.id)) }
  async resolveDraft(draft: RecordDraft, edited: boolean) { if (edited) await this.updateDraft(draft); return this.confirmDraft() }
  async cancelDraft() { const current = this.state.draft; if (!current) throw new Error('没有可取消的待确认记录。'); return this.run(() => this.client.cancelConfirmation(current.id)) }
  private async run(action: () => Promise<ConfirmationRead>) { this.state.saving = true; try { return this.adopt(await action()) } catch (error) { this.state.error = '操作未完成，请稍后重试或改用手动输入。'; throw error } finally { this.state.saving = false } }
}
export const recordStore = new RecordStore()
