/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

interface PageMetaState {
  crumbLabel?: string
}

interface PageMetaContextType extends PageMetaState {
  setCrumbLabel: (label: string | undefined) => void
}

const PageMetaContext = createContext<PageMetaContextType>({
  setCrumbLabel: () => {},
})

export function PageMetaProvider({ children }: { children: ReactNode }) {
  const [crumbLabel, setCrumbLabelRaw] = useState<string | undefined>()
  const setCrumbLabel = useCallback((label: string | undefined) => setCrumbLabelRaw(label), [])

  return (
    <PageMetaContext.Provider value={{ crumbLabel, setCrumbLabel }}>
      {children}
    </PageMetaContext.Provider>
  )
}

export function usePageMeta() {
  return useContext(PageMetaContext)
}
