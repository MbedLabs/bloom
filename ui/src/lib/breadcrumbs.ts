import { docRegistryListLabel, docRegistryListUrl } from './docRegistryParams'
import { normalizeDocTypeParam } from '../types/doc'

export type BreadcrumbProject = { id: number; name: string; prefix: string }

export type BreadcrumbCrumb = {
  label: string
  href?: string
  emphasize?: boolean
}

export function getBreadcrumbs(
  pathname: string,
  search: string,
  projects: BreadcrumbProject[],
  pageCrumbLabel?: string,
): BreadcrumbCrumb[] {
  const path = pathname
  const crumbs: BreadcrumbCrumb[] = [{ label: 'Home', href: '/' }]
  const parts = path.split('/')
  const slug = parts[2]
  const projectName = slug
    ? (projects.find((p) => p.prefix === slug || String(p.id) === slug)?.name || slug)
    : undefined

  if (path === '/') return [{ label: 'Dashboard' }]
  if (path === '/reports') return [{ label: 'Home', href: '/' }, { label: 'Reports' }]
  if (path === '/baselines') return [{ label: 'Home', href: '/' }, { label: 'Baselines' }]
  if (path === '/settings') return [{ label: 'Home', href: '/' }, { label: 'Settings' }]
  if (path === '/access') return [{ label: 'Home', href: '/' }, { label: 'Access' }]
  if (path === '/users') return [{ label: 'Home', href: '/' }, { label: 'Users' }]

  if (path.startsWith('/projects')) {
    crumbs.push({ label: 'Projects', href: '/projects' })
    if (!slug) return crumbs

    const sub = parts[3]
    const projCrumb = { label: projectName!, href: `/projects/${slug}` }

    if (!sub) {
      crumbs.push({ label: projectName! })
      return crumbs
    }

    crumbs.push(projCrumb)

    const subMap: Record<string, string> = {
      docs: 'Documents',
      campaigns: 'Test Campaigns',
      suites: 'Suites',
      traceability: 'Traceability Matrix',
      'impact-analysis': 'Impact Analysis',
      parameters: 'Parameters',
      baselines: 'Baselines',
      defects: 'Defects',
      edit: 'Edit project',
    }

    if (sub === 'docs') {
      const docTypeFromQuery = normalizeDocTypeParam(new URLSearchParams(search).get('type'))
      const docTypeFromPath = parts[4] !== 'new' ? normalizeDocTypeParam(parts[4]) : null
      const resolvedDocType = docTypeFromQuery ?? docTypeFromPath
      const docLabel = resolvedDocType ? docRegistryListLabel(resolvedDocType) : 'Documents'
      const docsHref = resolvedDocType
        ? docRegistryListUrl(slug, resolvedDocType)
        : docRegistryListUrl(slug)
      if (parts[4] === 'new' || parts[6] === 'edit') {
        crumbs.push({ label: docLabel, href: docsHref, emphasize: true })
      } else if (parts[4] && parts[5]) {
        crumbs.push({ label: docLabel })
      }
    } else if (sub === 'campaigns' && parts[4]) {
      crumbs.push(
        { label: 'Test Campaigns', href: `/projects/${slug}/campaigns` },
        { label: pageCrumbLabel || parts[4] },
      )
    } else if (sub === 'suites' && parts[4]) {
      crumbs.push(
        { label: 'Suites', href: docRegistryListUrl(slug, 'TS') },
        { label: pageCrumbLabel || parts[4] },
      )
    } else if (subMap[sub]) {
      crumbs.push({ label: subMap[sub] })
    }
  }

  return crumbs
}
