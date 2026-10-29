import { useEffect } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { docsApi } from '../api/client'
import { useProjectByPrefix } from '../hooks/useProjectByPrefix'
import RequirementDetail from './RequirementDetail'
import TestCaseDetail from './TestCaseDetail'
import DocumentDetail from './DocumentDetail'
import ArtefactDetail from './ArtefactDetail'
import CampaignDetail from './CampaignDetail'
import SuiteDetail from './SuiteDetail'
import AccessDenied from '../components/AccessDenied'
import { docResourceType, isAccessDenied } from '../lib/accessDenied'
import { docUrl, type DocType } from '../types/doc'

/** One document of any kind by its address; an address that names it by its database id is replaced by the one with its document ID. */
export default function UnifiedDocDetail() {
  const { prefix, kind, docId } = useParams<{ prefix: string; kind: string; docId: string }>()
  const navigate = useNavigate()
  const { data: project, error: projectError } = useProjectByPrefix(prefix)

  const { data: doc, isLoading, error: docError } = useQuery({
    queryKey: ['doc-facade', prefix, kind, docId],
    queryFn: () => docsApi.get(prefix!, kind!, docId!),
    enabled: !!prefix && !!kind && !!docId,
  })

  useEffect(() => {
    if (doc && prefix && doc.doc_id && doc.doc_id !== docId) {
      void navigate(docUrl(prefix, doc.doc_type as DocType, doc.doc_id), { replace: true })
    }
  }, [doc, docId, prefix, navigate])

  if (isAccessDenied(docError) || isAccessDenied(projectError)) {
    return <AccessDenied resourceType={docResourceType(kind)} resourceRef={docId ?? ''} projectPrefix={prefix} error={projectError ?? docError} />
  }

  if (isLoading || !project) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  }

  if (!doc) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <h3 className="text-lg font-semibold text-foreground mb-2">Document not found</h3>
          <p className="text-sm text-muted-foreground">Could not find document &quot;{docId}&quot; in project {prefix}</p>
          <Link to={kind ? `/projects/${prefix}/docs?type=${kind}` : `/projects/${prefix}/docs`} className="mt-4 inline-block text-primary hover:text-primary/80">
            &larr; Back to Documents
          </Link>
        </div>
      </div>
    )
  }

  switch (doc.doc_type) {
    case 'REQ':
      return <RequirementDetail resolvedId={doc.id} allowedActions={doc.allowed_actions} />
    case 'TC':
      return <TestCaseDetail resolvedId={doc.id} allowedActions={doc.allowed_actions} />
    case 'SPEC':
    case 'PRT':
    case 'RPT':
    case 'STD':
    case 'VIS':
      return <DocumentDetail resolvedId={doc.id} allowedActions={doc.allowed_actions} />
    case 'DES':
      return <ArtefactDetail kind="design" resolvedId={doc.id} allowedActions={doc.allowed_actions} />
    case 'RSK':
      return <ArtefactDetail kind="risk" resolvedId={doc.id} allowedActions={doc.allowed_actions} />
    case 'CHG':
      return <ArtefactDetail kind="change" resolvedId={doc.id} allowedActions={doc.allowed_actions} />
    case 'CPT':
      return <ArtefactDetail kind="test-concept" resolvedId={doc.id} allowedActions={doc.allowed_actions} />
    case 'DEF':
      return <ArtefactDetail kind="defect" resolvedId={doc.id} allowedActions={doc.allowed_actions} />
    case 'CMP':
      return <CampaignDetail resolvedId={doc.id} allowedActions={doc.allowed_actions} />
    case 'TS':
      return <SuiteDetail resolvedId={doc.id} allowedActions={doc.allowed_actions} />
    default:
      return <div className="text-center py-16 text-muted-foreground">Unknown document type: {doc.doc_type}</div>
  }
}
