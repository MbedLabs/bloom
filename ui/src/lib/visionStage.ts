import type { DocumentWorkflow } from '../api/client'

/** Binding once the viewer's workflow shows an approval: the Approved phase, a revision number
 * above 1, or an approved revision in the viewer's list; Idea otherwise. */
export function visionStage(
  workflow: Pick<DocumentWorkflow, 'phase' | 'revision_number' | 'revisions'> | undefined,
): 'Idea' | 'Binding' {
  if (!workflow) return 'Idea'
  const approved =
    workflow.phase === 'Approved' ||
    (workflow.revision_number ?? 1) > 1 ||
    workflow.revisions.length > 0
  return approved ? 'Binding' : 'Idea'
}
