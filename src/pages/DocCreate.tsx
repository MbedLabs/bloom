import { useState, useCallback, useEffect } from 'react'
import { useParams, useSearchParams, useNavigate, Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, PanelRightOpen, PanelRightClose } from 'lucide-react'
import { DocEditor } from '../components/editor'
import {
  projectsApi, requirementsApi, testCasesApi, designsApi,
  risksApi, changesApi, testConceptsApi, documentsApi, usersApi,
} from '../api/client'
import type { DocType } from '../types/doc'
import { DOC_CONFIGS, DOC_TYPE_LABELS, DOC_TYPE_COLORS } from '../types/doc'

interface DocCreateProps {
  editMode?: boolean
}

export default function DocCreate({ editMode = false }: DocCreateProps) {
  const { id: projectIdStr, docId: docIdStr } = useParams<{ id: string; docId: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const projectId = Number(projectIdStr)
  const docType = (searchParams.get('type') || 'REQ') as DocType
  const config = DOC_CONFIGS[docType]
  const docId = docIdStr ? Number(docIdStr) : undefined

  const [title, setTitle] = useState('')
  const [contentJson, setContentJson] = useState<Record<string, unknown> | null>(null)
  const [contentHtml, setContentHtml] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [metadata, setMetadata] = useState<Record<string, string>>({})

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId),
    enabled: !!projectId,
  })

  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.list,
  })

  const apiForType = useCallback((type: DocType) => {
    const map = {
      REQ: requirementsApi, TC: testCasesApi, DES: designsApi,
      RSK: risksApi, CHG: changesApi, TCO: testConceptsApi, DOC: documentsApi,
    }
    return map[type]
  }, [])

  useEffect(() => {
    if (!editMode || !docId) return
    const api = apiForType(docType) as unknown as { get: (id: number) => Promise<Record<string, unknown>> }
    api.get(docId).then((data) => {
      setTitle((data[config.titleField] as string) || '')
      if (data.content_json) setContentJson(data.content_json as Record<string, unknown>)
      if (data.content_html) setContentHtml(data.content_html as string)
      const meta: Record<string, string> = {}
      for (const field of config.fields) {
        if (field.key !== config.titleField && data[field.key] != null) {
          meta[field.key] = String(data[field.key])
        }
      }
      if (data.status) meta.status = data.status as string
      setMetadata(meta)
    })
  }, [editMode, docId, docType, config, apiForType])

  const createMutation = useMutation({
    mutationFn: async () => {
      const api = apiForType(docType)
      const payload: Record<string, unknown> = {
        project_id: projectId,
        [config.titleField]: title,
        content_json: contentJson,
        content_html: contentHtml,
        ...metadata,
      }
      if (docType === 'DOC') {
        return (api as typeof documentsApi).create({
          project_id: projectId,
          title,
          doc_type: metadata.doc_type || 'Specification',
          description: metadata.description,
        })
      }
      return (api as unknown as { create: (data: Record<string, unknown>) => Promise<Record<string, unknown>> }).create(payload)
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['requirements', projectId] })
      queryClient.invalidateQueries({ queryKey: ['test-cases', projectId] })
      queryClient.invalidateQueries({ queryKey: ['designs', projectId] })
      queryClient.invalidateQueries({ queryKey: ['risks', projectId] })
      queryClient.invalidateQueries({ queryKey: ['changes', projectId] })
      queryClient.invalidateQueries({ queryKey: ['test-concepts', projectId] })
      queryClient.invalidateQueries({ queryKey: ['documents', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })

      const routeMap: Record<string, string> = {
        REQ: 'requirements', TC: 'test-cases', DES: 'designs',
        RSK: 'risks', CHG: 'changes', TCO: 'test-concepts', DOC: 'documents',
      }
      const record = data as Record<string, unknown>
      navigate(`/projects/${projectId}/${routeMap[docType]}/${record.id}`)
    },
  })

  const updateMutation = useMutation({
    mutationFn: async () => {
      if (!docId) return
      const api = apiForType(docType) as unknown as { update: (id: number, data: Record<string, unknown>) => Promise<Record<string, unknown>> }
      const payload: Record<string, unknown> = {
        [config.titleField]: title,
        content_json: contentJson,
        content_html: contentHtml,
        ...metadata,
      }
      return api.update(docId, payload)
    },
    onSuccess: () => {
      const routeMap: Record<string, string> = {
        REQ: 'requirements', TC: 'test-cases', DES: 'designs',
        RSK: 'risks', CHG: 'changes', TCO: 'test-concepts', DOC: 'documents',
      }
      navigate(`/projects/${projectId}/${routeMap[docType]}/${docId}`)
    },
  })

  const handleEditorChange = useCallback((json: Record<string, unknown>, html: string) => {
    setContentJson(json)
    setContentHtml(html)
  }, [])

  const handleSave = () => {
    if (editMode) {
      updateMutation.mutate()
    } else {
      createMutation.mutate()
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending

  return (
    <div className="animate-fade-in -m-6 flex flex-col min-h-[calc(100vh-4rem)]">
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-border bg-card shrink-0">
        <div className="flex items-center gap-3">
          <Link
            to={`/projects/${projectId}`}
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to project
          </Link>
          <span className={`px-2 py-0.5 rounded-md text-[11px] font-semibold ${DOC_TYPE_COLORS[docType]}`}>
            {DOC_TYPE_LABELS[docType]}
          </span>
          {project && (
            <span className="text-xs text-muted-foreground">
              {project.prefix}-{config.typeCode}-...
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            title={sidebarOpen ? 'Hide metadata' : 'Show metadata'}
          >
            {sidebarOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
          </button>
          <button
            onClick={() => navigate(`/projects/${projectId}`)}
            className="px-3 py-1.5 text-sm text-muted-foreground border border-border rounded-md hover:bg-accent transition-colors"
          >
            Discard
          </button>
          <button
            onClick={handleSave}
            disabled={!title.trim() || isPending}
            className="px-4 py-1.5 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {isPending ? 'Saving...' : editMode ? 'Save' : 'Create'}
          </button>
        </div>
      </div>

      {/* Main area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Editor area */}
        <div className="flex-1 flex flex-col overflow-y-auto">
          <div className="max-w-4xl mx-auto w-full px-8 py-8">
            {/* Title */}
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Untitled"
              autoFocus
              className="w-full text-3xl font-bold text-foreground placeholder:text-muted-foreground/40 bg-transparent border-none outline-none mb-6"
            />

            {/* Editor */}
            <DocEditor
              content={contentJson}
              onChange={handleEditorChange}
              placeholder={`Start writing your ${config.label.toLowerCase()}... Use the toolbar above for formatting.`}
              editable={true}
              minHeight="min-h-[60vh]"
            />
          </div>
        </div>

        {/* Metadata sidebar */}
        {sidebarOpen && (
          <div className="w-72 border-l border-border bg-card/50 overflow-y-auto shrink-0">
            <div className="p-4 space-y-4">
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Properties</h3>

              {/* Status */}
              <MetaField label="Status">
                <select
                  value={metadata.status || config.statusOptions[0]}
                  onChange={(e) => setMetadata({ ...metadata, status: e.target.value })}
                  className="w-full px-2 py-1.5 bg-background border border-input rounded-md text-sm"
                >
                  {config.statusOptions.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </MetaField>

              {/* Priority (if applicable) */}
              {config.priorityOptions && (
                <MetaField label="Priority">
                  <select
                    value={metadata.priority || config.priorityOptions[0]}
                    onChange={(e) => setMetadata({ ...metadata, priority: e.target.value })}
                    className="w-full px-2 py-1.5 bg-background border border-input rounded-md text-sm"
                  >
                    {config.priorityOptions.map((opt) => (
                      <option key={opt} value={opt}>{opt}</option>
                    ))}
                  </select>
                </MetaField>
              )}

              {/* Assigned to */}
              <MetaField label="Assigned to">
                <select
                  value={metadata.reviewer_id || ''}
                  onChange={(e) => setMetadata({ ...metadata, reviewer_id: e.target.value })}
                  className="w-full px-2 py-1.5 bg-background border border-input rounded-md text-sm"
                >
                  <option value="">Unassigned</option>
                  {users?.map((u) => (
                    <option key={u.id} value={u.id}>{u.full_name}</option>
                  ))}
                </select>
              </MetaField>

              {/* Type-specific fields */}
              <div className="h-px bg-border" />
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                {config.label} Fields
              </h3>

              {config.fields.filter((f) => f.key !== config.titleField && f.key !== 'description' && f.type !== 'textarea').map((field) => (
                <MetaField key={field.key} label={field.label}>
                  {field.type === 'select' && field.options ? (
                    <select
                      value={metadata[field.key] || field.options[0]}
                      onChange={(e) => setMetadata({ ...metadata, [field.key]: e.target.value })}
                      className="w-full px-2 py-1.5 bg-background border border-input rounded-md text-sm"
                    >
                      {field.options.map((opt) => (
                        <option key={opt} value={opt}>{opt}</option>
                      ))}
                    </select>
                  ) : field.type === 'number' ? (
                    <input
                      type="number"
                      value={metadata[field.key] || ''}
                      onChange={(e) => setMetadata({ ...metadata, [field.key]: e.target.value })}
                      className="w-full px-2 py-1.5 bg-background border border-input rounded-md text-sm"
                    />
                  ) : (
                    <input
                      type="text"
                      value={metadata[field.key] || ''}
                      onChange={(e) => setMetadata({ ...metadata, [field.key]: e.target.value })}
                      className="w-full px-2 py-1.5 bg-background border border-input rounded-md text-sm"
                    />
                  )}
                </MetaField>
              ))}

              {/* Textarea fields in sidebar */}
              {config.fields.filter((f) => f.type === 'textarea' && f.key !== config.titleField && f.key !== 'description').map((field) => (
                <MetaField key={field.key} label={field.label}>
                  <textarea
                    value={metadata[field.key] || ''}
                    onChange={(e) => setMetadata({ ...metadata, [field.key]: e.target.value })}
                    rows={3}
                    className="w-full px-2 py-1.5 bg-background border border-input rounded-md text-sm resize-none"
                  />
                </MetaField>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function MetaField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-1">
        {label}
      </label>
      {children}
    </div>
  )
}
