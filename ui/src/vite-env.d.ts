/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_TESTSTATION_APP_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

interface Window {
  runtimeConfig?: {
    BLOOM_APP_URL?: string
    BUD_APP_URL?: string
  }
}
