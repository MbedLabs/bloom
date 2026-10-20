/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useMemo, type ReactNode } from 'react'

interface PageMetaState {
  crumbLabel?: string
}

interface PageMetaContextType extends PageMetaState {
  setCrumbLabel: (label: string | undefined) => void
}

const PageMetaContext = createContext<PageMetaContextType>({
  setCrumbLabel: () => {},
})

export function PageMetaProvider({ children }: Readonly<{ children: ReactNode }>) {
  const [crumbLabel, setCrumbLabel] = useState<string | undefined>()
  const value = useMemo(() => ({ crumbLabel, setCrumbLabel }), [crumbLabel])

  return (
    <PageMetaContext.Provider value={value}>
      {children}
    </PageMetaContext.Provider>
  )
}

export function usePageMeta() {
  return useContext(PageMetaContext)
}
