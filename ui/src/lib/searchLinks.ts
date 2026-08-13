import type { SearchResultItem } from '../api/client'
import { DOC_TYPE_SLUGS, type DocType } from '../types/doc'

/**
 * Build the in-app route for a global search result.
 *
 * Defects, suites and campaigns have dedicated pages keyed by numeric id;
 * every doc-registry type goes to the unified doc detail route; anything
 * unknown falls back to the project page so the click is never a dead end.
 */
export function searchResultUrl(item: SearchResultItem): string {
  const prefix = item.project_prefix
  switch (item.type) {
    case 'DEF':
      return `/projects/${prefix}/defects/${item.id}`
    case 'TS':
      return `/projects/${prefix}/suites/${item.id}`
    case 'CMP':
      return `/projects/${prefix}/campaigns/${item.id}`
    default: {
      const slug = DOC_TYPE_SLUGS[item.type as DocType]
      if (slug && item.doc_id) {
        return `/projects/${prefix}/docs/${slug}/${item.doc_id}`
      }
      return `/projects/${prefix}`
    }
  }
}
