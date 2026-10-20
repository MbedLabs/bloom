import type { Query, QueryClient, QueryKey } from '@tanstack/react-query'

interface ProjectScope {
  prefix?: string
  projectId?: number
}

/** The cached project metadata matching the supplied scope. */
function cachedProject(client: QueryClient, scope: ProjectScope): { id: number; prefix: string } | undefined {
  if (scope.prefix) return client.getQueryData<{ id: number; prefix: string }>(['project-by-prefix', scope.prefix])
  if (!scope.projectId) return undefined
  return client.getQueryData<{ id: number; prefix: string }>(['project', scope.projectId])
    ?? client.getQueryCache().findAll({ queryKey: ['project-by-prefix'] })
      .map(query => query.state.data as { id: number; prefix: string } | undefined)
      .find(item => item?.id === scope.projectId)
    ?? client.getQueryData<{ id: number; prefix: string }[]>(['projects'])
      ?.find(item => item.id === scope.projectId)
}

/** Resolve the project identity from the supplied scope and cached project metadata. */
function projectScope(client: QueryClient, scope: ProjectScope): ProjectScope {
  const project = cachedProject(client, scope)
  return { prefix: scope.prefix || project?.prefix, projectId: scope.projectId || project?.id }
}

/** Refresh affected project views and shared aggregates without waiting for requests. */
export function refreshProjectViews(client: QueryClient, scope: ProjectScope, refetchType: 'active' | 'none' = 'active') {
  const { prefix, projectId } = projectScope(client, scope)
  if (!prefix && !projectId) return
  const keys: QueryKey[] = [
    ['impact-analysis'], ['artefactRelated'], ['dashboard-stats'], ['baselines', 'global'],
  ]
  if (prefix) {
    for (const key of ['all-docs', 'project-doc-type-summary', 'project-by-prefix', 'tag-labels', 'doc-link-labels', 'doc-type-summary', 'link-candidates']) {
      keys.push([key, prefix])
    }
  }
  if (projectId) {
    for (const key of ['project', 'project-links', 'traceability', 'coverage-gaps', 'defects', 'testCases', 'projectVariables', 'campaigns', 'testSuites', 'projectTestCases', 'baselines']) {
      keys.push([key, projectId])
    }
  }
  for (const queryKey of keys) void client.invalidateQueries({ queryKey, refetchType })
}

/** Remove a deleted artefact's queries and refresh views after navigation unmounts its observers. */
export function finishArtefactDeletion(
  client: QueryClient,
  scope: ProjectScope & { detailKey: string; artefactType: string; recordId: number; kind?: string; docId?: string },
  navigate: () => void,
) {
  const resolvedScope = projectScope(client, scope)
  const predicate = (query: Query) => {
    const [key, type, id] = query.queryKey
    if (key === scope.detailKey && type === scope.recordId) return true
    if (['document-workflow', 'artefactComments', 'artefactActivity', 'document-revision', 'artefactRelated', 'artefact-tags'].includes(String(key))) {
      return type === scope.artefactType && id === scope.recordId
    }
    return key === 'doc-facade' && type === resolvedScope.prefix && id === scope.kind && query.queryKey[3] === scope.docId
  }
  const cache = client.getQueryCache()
  const queries = cache.findAll({ predicate })
  let finished = false
  const finish = () => {
    if (finished || queries.some(query => query.getObserversCount() > 0)) return
    finished = true
    unsubscribe()
    client.removeQueries({ predicate })
    refreshProjectViews(client, resolvedScope)
  }
  const unsubscribe = cache.subscribe(event => {
    if (event.type === 'observerRemoved') setTimeout(finish, 0)
  })
  navigate()
  setTimeout(finish, 0)
}
