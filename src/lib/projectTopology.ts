import { docsApi, type DocShell, type PaginatedResponse } from '../api/client'

const TOPOLOGY_PAGE_SIZE = 500

type ListDocsFn = (
  projectRef: string,
  params?: {
    type?: string[]
    status?: string
    q?: string
    includeLinkCounts?: boolean
    skip?: number
    limit?: number
  },
) => Promise<PaginatedResponse<DocShell>>

export async function fetchAllTopologyDocs(
  projectRef: string,
  listDocs: ListDocsFn = docsApi.list,
): Promise<DocShell[]> {
  const allDocs: DocShell[] = []
  let skip = 0
  let hasMore = true

  while (hasMore) {
    const page = await listDocs(projectRef, {
      includeLinkCounts: true,
      skip,
      limit: TOPOLOGY_PAGE_SIZE,
    })

    allDocs.push(...page.items)

    if (allDocs.length >= page.total || page.items.length === 0) {
      hasMore = false
      continue
    }

    skip += page.limit
  }

  return allDocs
}
