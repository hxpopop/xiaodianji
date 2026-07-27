interface UniRecorderManager {
  start(options: { duration?: number; format?: string; sampleRate?: number; numberOfChannels?: number }): void
  pause(): void
  resume(): void
  stop(): void
  onStop(callback: (result: { tempFilePath: string; duration?: number; fileSize?: number }) => void): void
  onError(callback: (error: { errMsg?: string }) => void): void
}

declare function getCurrentPages(): Array<{
  $page?: { options?: Record<string, string> }
  options?: Record<string, string>
}>

declare const uni: {
  navigateTo(options: { url: string }): void
  reLaunch(options: { url: string }): void
  previewImage(options: { current: string; urls: string[] }): void
  getRecorderManager?(): UniRecorderManager
  getSystemInfoSync?(): { uniPlatform?: string }
  uploadFile(options: {
    url: string
    filePath: string
    name: string
    header?: Record<string, string>
    formData?: Record<string, string>
    success(result: { statusCode: number; data: string }): void
    fail(error: { errMsg?: string }): void
  }): void
  downloadFile(options: {
    url: string
    success(result: { statusCode: number; tempFilePath: string }): void
    fail(error: { errMsg?: string }): void
  }): void
  openDocument(options: {
    filePath: string
    showMenu?: boolean
    fail?(error: { errMsg?: string }): void
  }): void
  showToast?(options: { title: string; icon?: 'none' | 'success' }): void
}
