import type { Policy, PolicyRule, PolicyScope, PolicyVisibility, Tag } from '../api/client'
import { DOC_TYPE_LABELS, type DocType } from '../types/doc'
import { docRegistryListLabel } from './docRegistryParams'

export const DOC_TYPES = Object.keys(DOC_TYPE_LABELS) as DocType[]

export const PROJECT_RESOURCES = ['baseline', 'parameter', 'link', 'project']
export const APP_RESOURCES = ['users', 'access', 'application']
export const RESOURCES = [...DOC_TYPES, ...PROJECT_RESOURCES, ...APP_RESOURCES]
const APPROVABLE_RESOURCES = new Set(['REQ', 'TC', 'SPEC', 'PRT', 'RPT', 'DES', 'CHG', 'CPT', 'DEF', 'TS'])
export const approveIncludesReview = (resource: string) => APPROVABLE_RESOURCES.has(resource) && resource !== 'RPT'
export const SCOPE_LABELS: Record<PolicyScope, string> = { document: 'Document', project: 'Project', app: 'App' }
export const BUILTIN_ORIGINS: { key: PolicyVisibility; label: string }[] = [
  { key: 'internal', label: 'Internal' },
  { key: 'customer', label: 'Customer' },
]

export type Permission = 'read' | 'write' | 'review' | 'approve' | 'delete'
export const PERMISSIONS: Permission[] = ['read', 'write', 'review', 'approve', 'delete']
export const emptyRule = (): PolicyRule => ({
  read: false,
  write: false,
  review: false,
  approve: false,
  delete: false,
  all_origins: true,
  visibility: [],
  tags: [],
})
export const isDocType = (resource: string) => (DOC_TYPES as string[]).includes(resource)
export const resourcesFor = (scope: PolicyScope) => {
  if (scope === 'document') return DOC_TYPES
  return scope === 'project' ? [...DOC_TYPES, ...PROJECT_RESOURCES] : RESOURCES
}
export const activeRule = (rule: PolicyRule) => PERMISSIONS.some((permission) => rule[permission])
export const supportedPermission = (resource: string, permission: Permission) => {
  if (permission === 'review') return isDocType(resource)
  if (permission === 'approve') return APPROVABLE_RESOURCES.has(resource)
  return permission !== 'delete' || resource !== 'project'
}
const RESOURCE_LABELS: Record<string, string> = {
  project: 'Project Management',
  users: 'User Management',
  access: 'Access Management',
  application: 'Application Administration',
}
export const resourceLabel = (resource: string) =>
  isDocType(resource)
    ? `${resource} · ${docRegistryListLabel(resource as DocType)}`
    : RESOURCE_LABELS[resource] ?? resource.charAt(0).toUpperCase() + resource.slice(1)

export function policyRules(policy: Policy) {
  return resourcesFor(policy.scope)
    .filter((resource) => policy.rules[resource] && activeRule(policy.rules[resource]))
    .map((resource) => [resource, policy.rules[resource]] as const)
}

function ruleSummaries(
  entries: readonly (readonly [string, PolicyRule])[],
  summarize: (resource: string, rule: PolicyRule) => { key: string; label: string },
) {
  const groups = new Map<string, { resources: string[]; label: string }>()
  for (const [resource, rule] of entries) {
    const { key, label } = summarize(resource, rule)
    const group = groups.get(key) ?? { resources: [], label }
    group.resources.push(isDocType(resource) ? resource : resource.charAt(0).toUpperCase() + resource.slice(1))
    groups.set(key, group)
  }
  return [...groups.values()].map(({ resources, label }) => groups.size === 1 ? label : `${resources.join(', ')}: ${label}`)
}

export function policyScopeLabel(policy: Policy) {
  return policy.scope === 'document'
    ? policyRules(policy).map(([resource]) => resource).join(', ') || 'None'
    : SCOPE_LABELS[policy.scope]
}

/** Whether a policy summary lists the permission of a rule. */
function summaryLists(rule: PolicyRule, resource: string, permission: Permission) {
  if (permission === 'read') return rule.read && !rule.write
  if (permission === 'review') return rule.review && !(rule.approve && approveIncludesReview(resource))
  return rule[permission]
}

export function policyPermissions(policy: Policy) {
  if (isCompleteAppPolicy(policy)) return ['All']
  return ruleSummaries(policyRules(policy), (resource, rule) => {
    const permissions = PERMISSIONS.filter((permission) => summaryLists(rule, resource, permission) && supportedPermission(resource, permission))
    const label = permissions.map((permission) => permission.charAt(0).toUpperCase() + permission.slice(1)).join(', ') || 'None'
    return { key: permissions.join(','), label }
  })
}

export function policyOrigins(policy: Policy, tags: Tag[]) {
  const entries = policyRules(policy).filter(([resource]) => isDocType(resource))
  if (entries.length === 0) return ['NA']
  return ruleSummaries(entries, (_resource, rule) => {
    if (rule.all_origins) return { key: 'all', label: 'All' }
    const visibility = BUILTIN_ORIGINS.filter(({ key }) => (rule.visibility ?? []).includes(key))
    const tagIds = [...new Set(rule.tags ?? [])].sort((a, b) => a - b)
    const labels = [
      ...visibility.map(({ label }) => label),
      ...tagIds.map((id) => tags.find((tag) => tag.id === id)?.name ?? `Origin ${id}`),
    ]
    return { key: JSON.stringify([visibility.map(({ key }) => key), tagIds]), label: labels.join(', ') || 'None' }
  })
}

export function isCompleteAppPolicy(policy: Policy) {
  return policy.scope === 'app' && RESOURCES.every((resource) => {
    const rule = policy.rules[resource]
    return rule && PERMISSIONS.every((permission) => !supportedPermission(resource, permission)
      || (permission === 'read' ? rule.read || rule.write : rule[permission]))
  })
}

export function policyResourceSummary(policy: Policy) {
  const entries = policyRules(policy)
  if (policy.scope !== 'document' && entries.length === resourcesFor(policy.scope).length) return SCOPE_LABELS[policy.scope]
  return entries.map(([resource]) => isDocType(resource)
    ? resource : resource.charAt(0).toUpperCase() + resource.slice(1)).join(', ') || 'None'
}
