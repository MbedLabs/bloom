import type { SearchResultItem } from '../api/client'
import { DOC_TYPE_SLUGS, type DocType } from '../types/doc'

/**
 * Build the in-app route for a global search result.
 *
 * Every doc-registry type, defects, suites and campaigns included, goes to the
 * unified doc detail route by its document ID; anything unknown goes to the
 * project page.
 */
export function searchResultUrl(item: SearchResultItem): string {
  const prefix = item.project_prefix
  const slug = DOC_TYPE_SLUGS[item.type as DocType]
  if (slug && item.doc_id) {
    return `/projects/${prefix}/docs/${slug}/${item.doc_id}`
  }
  return `/projects/${prefix}`
}
