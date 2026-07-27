import { reactive } from 'vue'
import { apiClient } from '../api/client'
import type { ConfirmationRead, RecordDraft, VoiceAudioInput } from '../api/types'

const defaultShopId = import.meta.env.VITE_SHOP_ID || ''

export class RecordStore {
  state

  constructor(private readonly client: any = apiClient, shopId = defaultShopId) {
    this.state = reactive({
      shopId,
      draft: null as ConfirmationRead | null,
      error: '',
      saving: false,
    })
  }

  setShopId(shopId: string) {
    this.state.shopId = shopId
  }

  private requireShop() {
    if (!this.state.shopId) {
      throw new Error('尚未配置商户，请联系管理员设置商户信息后再记账。')
    }
  }

  private adopt(draft: ConfirmationRead) {
    this.state.draft = draft
    this.state.error = ''
    return draft
  }

  async createTextDraft(text: string) {
    this.requireShop()
    return this.run(() => this.client.createTextDraft(this.state.shopId, text))
  }

  async createManualDraft(draft: RecordDraft) {
    this.requireShop()
    return this.run(() => this.client.createManualDraft(this.state.shopId, draft))
  }

  async createVoiceDraft(audio: VoiceAudioInput) {
    this.requireShop()
    return this.run(() => this.client.createVoiceDraft(this.state.shopId, audio))
  }

  async updateDraft(draft: RecordDraft) {
    const current = this.state.draft
    if (!current) throw new Error('没有可修改的待确认记录。')
    return this.run(() => this.client.updateConfirmation(current.id, draft))
  }

  async confirmDraft() {
    const current = this.state.draft
    if (!current) throw new Error('没有可确认的待确认记录。')
    return this.run(() => this.client.confirmConfirmation(current.id))
  }

  async resolveDraft(draft: RecordDraft, edited: boolean) {
    if (edited) await this.updateDraft(draft)
    return this.confirmDraft()
  }

  async cancelDraft() {
    const current = this.state.draft
    if (!current) throw new Error('没有可取消的待确认记录。')
    return this.run(() => this.client.cancelConfirmation(current.id))
  }

  private async run(action: () => Promise<ConfirmationRead>) {
    this.state.saving = true
    try {
      return this.adopt(await action())
    } catch (error) {
      this.state.error = error instanceof Error
        ? error.message
        : '操作未完成，请稍后重试或改用手动输入。'
      throw error
    } finally {
      this.state.saving = false
    }
  }
}

export const recordStore = new RecordStore()
