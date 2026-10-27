import type { QueryClient } from '@tanstack/react-query'

import { refreshProjectViews } from './refreshProjectViews'

/** The detail query key of each artefact type. */
export const ENTITY_KEYS: Record<string, string> = {
  requirement: 'requirement',
  'test-case': 'testCase',
  document: 'document',
  design: 'design',
  risk: 'risk',
  change: 'change',
  'test-concept': 'testConcept',
  defect: 'defect',
  'test-suite': 'testSuite',
  campaign: 'campaign',
}

/** Refresh an artefact's detail, workflow, discussion, activity and revision queries and its project's views. */
export function refreshArtefactViews(
  client: QueryClient,
  artefactType: string,
  artefactId: number,
  projectPrefix?: string,
  projectId?: number,
): Promise<unknown> {
  refreshProjectViews(client, { prefix: projectPrefix, projectId })
  return Promise.all([
    ['document-workflow', artefactType, artefactId], [ENTITY_KEYS[artefactType], artefactId],
    ['artefactComments', artefactType, artefactId], ['artefactActivity', artefactType, artefactId],
    ['document-revision', artefactType, artefactId], ['doc-facade', projectPrefix],
  ].map(queryKey => client.invalidateQueries({ queryKey })))
}
