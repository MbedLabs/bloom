import type { ReactNode } from 'react'
import { APP_VERSION } from '../api/client'
import { BLOOM_LOGO_DARK, BLOOM_LOGO_LIGHT } from '../brandAssets'

/** The card with the Bloom logo and the version footer that frames the account pages. */
export default function AuthPageShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-linear-to-br/srgb from-[#1a1028] via-[#3b1d6e] to-[#6b7280] p-4">
      <div className="w-full max-w-md bg-card rounded-2xl shadow-2xl p-8 border border-border">
        <div className="flex flex-col items-center mb-6">
          <img
            src={BLOOM_LOGO_DARK}
            alt="Bloom by EmbedLabs"
            className="h-16 w-auto max-w-full object-contain mb-3 hidden dark:block"
          />
          <img
            src={BLOOM_LOGO_LIGHT}
            alt="Bloom by EmbedLabs"
            className="h-16 w-auto max-w-full object-contain mb-3 dark:hidden"
          />
        </div>
        {children}
        <div className="text-center mt-6">
          <p className="text-sm text-violet-100/70">Bloom PLM</p>
          <p className="text-xs text-violet-200/50 mt-1">v{APP_VERSION}</p>
          <a
            href="https://www.embedlabs.net"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-gray-300/50 mt-1 inline-block hover:text-gray-200 transition-colors"
          >
            Powered by EmbedLabs
          </a>
        </div>
      </div>
    </div>
  )
}
