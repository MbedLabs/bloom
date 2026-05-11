import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { docsApi } from '../api/client'
import { useProjectByPrefix } from '../hooks/useProjectByPrefix'
import RequirementDetail from './RequirementDetail'
import TestCaseDetail from './TestCaseDetail'
import DocumentDetail from './DocumentDetail'
import ArtefactDetail from './ArtefactDetail'
import CampaignDetail from './CampaignDetail'
import SuiteDetail from './SuiteDetail'

export default function UnifiedDocDetail() {
  const { prefix, kind, docId } = useParams<{ prefix: string; kind: string; docId: string }>()
  const { data: project } = useProjectByPrefix(prefix)

  const { data: doc, isLoading } = useQuery({
    queryKey: ['doc-facade', prefix, kind, docId],
    queryFn: () => docsApi.get(prefix!, kind!, docId!),
    enabled: !!prefix && !!kind && !!docId,
  })

  if (isLoading || !project) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  }

  if (!doc) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <h3 className="text-lg font-semibold text-foreground mb-2">Document not found</h3>
          <p className="text-sm text-muted-foreground">Could not find document &quot;{docId}&quot; in project {prefix}</p>
          <Link to={`/projects/${prefix}/docs${kind ? `?type=${kind}` : ''}`} className="mt-4 inline-block text-primary hover:text-primary/80">
            &larr; Back to Documents
          </Link>
        </div>
      </div>
    )
  }

  switch (doc.doc_type) {
    case 'REQ':
      return <RequirementDetail resolvedId={doc.id} />
    case 'TC':
      return <TestCaseDetail resolvedId={doc.id} />
    case 'SPEC':
    case 'PROT':
    case 'RPT':
    case 'STD':
      return <DocumentDetail resolvedId={doc.id} />
    case 'DES':
      return <ArtefactDetail kind="design" resolvedId={doc.id} />
    case 'RSK':
      return <ArtefactDetail kind="risk" resolvedId={doc.id} />
    case 'CHG':
      return <ArtefactDetail kind="change" resolvedId={doc.id} />
    case 'TCO':
      return <ArtefactDetail kind="test-concept" resolvedId={doc.id} />
    case 'DEF':
      return <ArtefactDetail kind="defect" resolvedId={doc.id} />
    case 'CMP':
      return <CampaignDetail resolvedId={doc.id} />
    case 'TS':
      return <SuiteDetail resolvedId={doc.id} />
    default:
      return <div className="text-center py-16 text-muted-foreground">Unknown document type: {doc.doc_type}</div>
  }
}
