import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { docsApi } from '../api/client'

/** The server's ceiling on one `keys` lookup. */
const MAX_TAG_KEYS = 500

/** The `TYPE:id` keys of every `#` tag in a document body, sorted and unique. */
export function tagKeys(content: unknown): string[] {
  const keys = new Set<string>()
  const walk = (node: unknown) => {
    if (!node || typeof node !== 'object') return
    const { type, attrs, content: children } = node as {
      type?: string
      attrs?: { id?: unknown; mentionSuggestionChar?: unknown }
      content?: unknown[]
    }
    if (type === 'mention' && attrs?.mentionSuggestionChar === '#' && typeof attrs.id === 'string' && attrs.id.includes(':')) {
      keys.add(attrs.id)
    }
    if (Array.isArray(children)) children.forEach(walk)
  }
  walk(content)
  return Array.from(keys).sort().slice(0, MAX_TAG_KEYS)
}

/**
 * The current public id of every artefact a document's tags point at, resolved in
 * one request. A key maps to null when the lookup did not return it (deleted, or not
 * visible to the reader). Undefined until the lookup answers.
 */
export function useArtefactLabels(prefix: string | undefined, content: unknown): Record<string, string | null> | undefined {
  const keys = useMemo(() => tagKeys(content), [content])
  const { data, isSuccess } = useQuery({
    queryKey: ['tag-labels', prefix, keys],
    queryFn: () => docsApi.list(prefix as string, { keys, includeLinkCounts: false, limit: keys.length }),
    enabled: !!prefix && keys.length > 0,
    retry: false,
    staleTime: 60_000,
  })
  return useMemo(() => {
    if (!isSuccess || !data || !Array.isArray(data.items)) return undefined
    const found = new Map(data.items.map((doc) => [`${doc.doc_type}:${doc.id}`, doc.doc_id]))
    return Object.fromEntries(keys.map((key) => [key, found.get(key) ?? null]))
  }, [data, isSuccess, keys])
}
