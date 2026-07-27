declare const uni: {
  navigateTo(options: { url: string }): void
  previewImage(options: { current: string; urls: string[] }): void
  reLaunch(options: { url: string }): void
}
