import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Check, ChevronRight, Download, AlertCircle } from 'lucide-react'
import { projectsApi, requirementsApi, testCasesApi, importApi } from '../api/client'
import { useProjectByPrefix } from '../hooks/useProjectByPrefix'
import type { ImportResult } from '../api/client'

type WizardStep = 1 | 2 | 3 | 4 | 5

export default function ImportWizard() {
  const { prefix } = useParams<{ prefix: string }>()
  const { data: currentProject } = useProjectByPrefix(prefix)
  const projectId = currentProject?.id || 0
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [step, setStep] = useState<WizardStep>(1)
  const [sourceProjectId, setSourceProjectId] = useState<number | null>(null)
  const [docType, setDocType] = useState<'REQ' | 'TC'>('REQ')
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [includeLinks, setIncludeLinks] = useState(true)
  const [result, setResult] = useState<ImportResult | null>(null)

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  })

  const { data: targetProject } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId),
    enabled: !!projectId,
  })

  const { data: sourceReqs } = useQuery({
    queryKey: ['requirements', sourceProjectId],
    queryFn: () => requirementsApi.list(sourceProjectId!),
    enabled: !!sourceProjectId && docType === 'REQ' && step >= 3,
  })

  const { data: sourceTcs } = useQuery({
    queryKey: ['testCases', sourceProjectId],
    queryFn: () => testCasesApi.list(sourceProjectId!),
    enabled: !!sourceProjectId && docType === 'TC' && step >= 3,
  })

  const importMutation = useMutation({
    mutationFn: () =>
      importApi.import(projectId, {
        source_project_id: sourceProjectId!,
        doc_type: docType,
        doc_ids: selectedIds,
        include_links: includeLinks,
      }),
    onSuccess: (data) => {
      setResult(data)
      setStep(5)
      queryClient.invalidateQueries({ queryKey: ['requirements', projectId] })
      queryClient.invalidateQueries({ queryKey: ['testCases', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
    },
  })

  const sourceDocs = docType === 'REQ' ? sourceReqs : sourceTcs
  const availableProjects = projects?.filter((p) => p.id !== projectId) || []
  const sourceProject = projects?.find((p) => p.id === sourceProjectId)

  const toggleId = (id: number) => {
    setSelectedIds((prev) => prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id])
  }

  const steps = ['Source Project', 'Doc Type', 'Select Docs', 'Review', 'Results']

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl mx-auto">
      <div className="flex items-center gap-3">
        <Link to={`/projects/${prefix}`} className="p-2 hover:bg-accent/50 rounded-md">
          <ArrowLeft className="h-5 w-5 text-muted-foreground" />
        </Link>
        <div>
          <h2 className="text-xl font-bold text-foreground">Import Docs</h2>
          <p className="text-sm text-muted-foreground">
            Import docs from another project into {targetProject?.name || 'this project'}
          </p>
        </div>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2">
        {steps.map((label, i) => (
          <div key={i} className="flex items-center gap-2">
            {i > 0 && <ChevronRight className="h-4 w-4 text-muted-foreground/40" />}
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium ${
              step > i + 1 ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400' :
              step === i + 1 ? 'bg-primary/10 text-primary' :
              'bg-muted text-muted-foreground'
            }`}>
              {step > i + 1 ? <Check className="h-3 w-3" /> : <span>{i + 1}</span>}
              {label}
            </div>
          </div>
        ))}
      </div>

      <div className="bg-card rounded-lg border border-border shadow-elegant p-6">
        {step === 1 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-foreground">Select Source Project</h3>
            <p className="text-sm text-muted-foreground">Choose which project to import docs from.</p>
            {availableProjects.length === 0 ? (
              <p className="text-muted-foreground">No other projects available.</p>
            ) : (
              <div className="grid grid-cols-1 gap-2">
                {availableProjects.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => { setSourceProjectId(p.id); setStep(2) }}
                    className={`text-left p-4 rounded-lg border transition-colors ${
                      sourceProjectId === p.id ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/30 hover:bg-accent/30'
                    }`}
                  >
                    <div className="font-medium text-foreground">{p.name}</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {p.prefix} &middot; {p.requirement_count} REQs &middot; {p.test_case_count} TCs
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-foreground">Select Doc Type</h3>
            <p className="text-sm text-muted-foreground">What type of docs do you want to import from {sourceProject?.name}?</p>
            <div className="flex gap-3">
              {(['REQ', 'TC'] as const).map((type) => (
                <button
                  key={type}
                  onClick={() => { setDocType(type); setSelectedIds([]); setStep(3) }}
                  className={`flex-1 p-4 rounded-lg border text-center transition-colors ${
                    docType === type ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/30'
                  }`}
                >
                  <div className="font-medium text-foreground">{type === 'REQ' ? 'Requirements' : 'Test Cases'}</div>
                </button>
              ))}
            </div>
            <button onClick={() => setStep(1)} className="text-sm text-muted-foreground hover:text-foreground">
              &larr; Back
            </button>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-foreground">Select Docs to Import</h3>
            <p className="text-sm text-muted-foreground">
              {selectedIds.length} of {sourceDocs?.length || 0} selected
            </p>
            {sourceDocs && sourceDocs.length > 0 ? (
              <>
                <button
                  onClick={() => setSelectedIds(
                    selectedIds.length === sourceDocs.length ? [] : sourceDocs.map((d) => d.id)
                  )}
                  className="text-xs text-primary hover:text-primary/80"
                >
                  {selectedIds.length === sourceDocs.length ? 'Deselect all' : 'Select all'}
                </button>
                <div className="max-h-96 overflow-y-auto space-y-1">
                  {sourceDocs.map((doc) => {
                    const isSelected = selectedIds.includes(doc.id)
                    const docRecord = doc as unknown as Record<string, unknown>
                    return (
                      <button
                        key={doc.id}
                        onClick={() => toggleId(doc.id)}
                        className={`w-full text-left p-3 rounded-lg border transition-colors ${
                          isSelected ? 'border-primary bg-primary/5' : 'border-border hover:bg-accent/30'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`w-4 h-4 rounded border-2 flex items-center justify-center ${isSelected ? 'border-primary bg-primary' : 'border-muted-foreground/30'}`}>
                            {isSelected && <Check className="h-3 w-3 text-primary-foreground" />}
                          </div>
                          <div>
                            <span className="font-mono text-xs text-primary">{String(docRecord.req_id || docRecord.tc_id || '')}</span>
                            <span className="ml-2 text-sm text-foreground">{String(docRecord.title || docRecord.name || '')}</span>
                          </div>
                        </div>
                      </button>
                    )
                  })}
                </div>
              </>
            ) : (
              <p className="text-muted-foreground">No docs found in source project.</p>
            )}
            <div className="flex justify-between">
              <button onClick={() => setStep(2)} className="text-sm text-muted-foreground hover:text-foreground">&larr; Back</button>
              <button
                onClick={() => setStep(4)}
                disabled={selectedIds.length === 0}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
              >
                Review ({selectedIds.length})
              </button>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-foreground">Review Import</h3>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Source</span>
                <span className="text-foreground font-medium">{sourceProject?.name} ({sourceProject?.prefix})</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Target</span>
                <span className="text-foreground font-medium">{targetProject?.name} ({targetProject?.prefix})</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Doc type</span>
                <span className="text-foreground font-medium">{docType === 'REQ' ? 'Requirements' : 'Test Cases'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Count</span>
                <span className="text-foreground font-medium">{selectedIds.length} docs</span>
              </div>
              <div className="flex justify-between text-sm items-center">
                <span className="text-muted-foreground">New IDs</span>
                <span className="text-foreground font-medium">{targetProject?.prefix}-{docType}-NNN</span>
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={includeLinks}
                  onChange={(e) => setIncludeLinks(e.target.checked)}
                  className="rounded"
                />
                Include links
              </label>
            </div>
            <div className="flex justify-between pt-4">
              <button onClick={() => setStep(3)} className="text-sm text-muted-foreground hover:text-foreground">&larr; Back</button>
              <button
                onClick={() => importMutation.mutate()}
                disabled={importMutation.isPending}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 disabled:opacity-50 inline-flex items-center gap-2"
              >
                <Download className="h-4 w-4" />
                {importMutation.isPending ? 'Importing...' : `Import ${selectedIds.length} Docs`}
              </button>
            </div>
          </div>
        )}

        {step === 5 && result && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-foreground">Import Complete</h3>
            <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 p-4 space-y-2">
              <div className="text-emerald-700 dark:text-emerald-400 font-medium">
                {result.imported} doc{result.imported !== 1 ? 's' : ''} imported successfully
              </div>
              {result.skipped > 0 && (
                <div className="text-amber-700 dark:text-amber-400 text-sm">{result.skipped} skipped</div>
              )}
              {result.new_ids.length > 0 && (
                <div className="text-sm text-muted-foreground">
                  New IDs: {result.new_ids.join(', ')}
                </div>
              )}
            </div>
            {result.errors.length > 0 && (
              <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-4 space-y-1">
                <div className="flex items-center gap-2 text-red-700 dark:text-red-400 font-medium">
                  <AlertCircle className="h-4 w-4" />
                  Errors
                </div>
                {result.errors.map((err, i) => (
                  <div key={i} className="text-sm text-red-600 dark:text-red-400">{err}</div>
                ))}
              </div>
            )}
            <button
              onClick={() => navigate(`/projects/${prefix}`)}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90"
            >
              Back to Project
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
