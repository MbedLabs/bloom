import { QueryClient, type QueryClientConfig } from '@tanstack/react-query'

/** Build the application query client with optional test overrides. */
export function createQueryClient(config: QueryClientConfig = {}) {
  return new QueryClient({
    ...config,
    defaultOptions: {
      ...config.defaultOptions,
      queries: {
        staleTime: 5 * 60 * 1000,
        retry: 1,
        ...config.defaultOptions?.queries,
      },
    },
  })
}
