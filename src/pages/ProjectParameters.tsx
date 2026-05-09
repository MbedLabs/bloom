import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Edit2, GitBranch, Plus, SlidersHorizontal, Trash2, X } from 'lucide-react'

import {
  extractApiErrorMessage,
  integrationsApi,
  IntegrationSetting,
  projectVariablesApi,
  ProjectVariable,
} from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { useProjectByPrefix } from '../hooks/useProjectByPrefix'

type TrackerKind = 'github' | 'gitlab'

const TRACKER_LABELS: Record<TrackerKind, string> = { github: 'GitHub', gitlab: 'GitLab' }

const WEBHOOK_PATHS: Record<TrackerKind, string> = {
  github: '/api/integrations/github/webhook',
  gitlab: '/api/integrations/gitlab/webhook',
}

export default function ProjectParameters() {
  const { prefix } = useParams<{ prefix: string }>()
  const { data: project, isLoading: projectLoading } = useProjectByPrefix(prefix)
  const projectId = project?.id || 0
  const queryClient = useQueryClient()

  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState({ kind: 'variable' as ProjectVariable['kind'], key: '', value: '', description: '' })
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editForm, setEditForm] = useState({ kind: 'variable' as ProjectVariable['kind'], key: '', value: '', description: '' })

  const { data: variables, isLoading: variablesLoading } = useQuery({
    queryKey: ['projectVariables', projectId],
    queryFn: () => projectVariablesApi.list(projectId),
    enabled: !!projectId,
  })

  const createMutation = useMutation({
    mutationFn: projectVariablesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectVariables', projectId] })
      setShowCreate(false)
      setCreateForm({ kind: 'variable', key: '', value: '', description: '' })
    },
  })

  useEffect(() => {
    if (!editingId || !variables) return
    const currentItem = variables.find((item) => item.id === editingId)
    if (!currentItem) return
    setEditForm({
      kind: currentItem.kind,
      key: currentItem.key,
      value: currentItem.value,
      description: currentItem.description || '',
    })
  }, [editingId, variables])

  const deleteMutation = useMutation({
    mutationFn: projectVariablesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectVariables', projectId] })
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof projectVariablesApi.update>[1] }) =>
      projectVariablesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectVariables', projectId] })
      setEditingId(null)
    },
  })

  const onCreate = (e: React.FormEvent) => {
    e.preventDefault()
    const key = createForm.key.trim()
    const value = createForm.value.trim()
    if (!key || !value) return

    createMutation.mutate({
      project_id: projectId,
      kind: createForm.kind,
      key,
      value,
      description: createForm.description || null,
    })
  }

  const onEdit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingId) return

    const key = editForm.key.trim()
    const value = editForm.value.trim()
    if (!key || !value) return

    updateMutation.mutate({
      id: editingId,
      data: {
        kind: editForm.kind,
        key,
        value,
        description: editForm.description || null,
      },
    })
  }

  if (projectLoading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>
  }

  if (!project) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6 text-center">
        <h3 className="text-lg font-medium text-destructive">Project Not Found</h3>
        <Link to="/projects" className="mt-4 inline-block text-primary hover:text-primary/80">
          &larr; Back to Projects
        </Link>
      </div>
    )
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link to={`/projects/${prefix}`} className="p-2 hover:bg-accent/50 rounded-md">
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </Link>
          <div>
            <h2 className="text-2xl font-bold text-foreground">Project Parameters</h2>
            <p className="text-muted-foreground">{project.name}</p>
          </div>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 transition-colors text-sm"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add Item
        </button>
      </div>

      {showCreate && (
        <div className="bg-card rounded-lg border border-border shadow-elegant p-5">
          <h3 className="font-semibold text-foreground mb-4">New Parameter / Variable</h3>
          <form onSubmit={onCreate} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Kind</label>
              <select
                value={createForm.kind}
                onChange={(e) => setCreateForm({ ...createForm, kind: e.target.value as ProjectVariable['kind'] })}
                title="Select item kind"
                className="w-full px-3 py-2 bg-background border border-input rounded-md"
              >
                <option value="variable">Variable</option>
                <option value="parameter">Parameter</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Key</label>
              <input
                required
                value={createForm.key}
                onChange={(e) => setCreateForm({ ...createForm, key: e.target.value })}
                title="Variable or parameter key"
                placeholder="Enter a key"
                className="w-full px-3 py-2 bg-background border border-input rounded-md"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Value</label>
              <textarea
                required
                rows={3}
                value={createForm.value}
                onChange={(e) => setCreateForm({ ...createForm, value: e.target.value })}
                title="Variable or parameter value"
                placeholder="Enter a value"
                className="w-full px-3 py-2 bg-background border border-input rounded-md"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Description</label>
              <textarea
                rows={2}
                value={createForm.description}
                onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                title="Optional description"
                placeholder="Optional description"
                className="w-full px-3 py-2 bg-background border border-input rounded-md"
              />
            </div>
            <div className="pt-2 flex justify-end gap-3">
              <button type="button" onClick={() => setShowCreate(false)} className="px-4 py-2 border border-input rounded-md text-foreground hover:bg-accent/50">Cancel</button>
              <button type="submit" disabled={createMutation.isPending} className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50">{createMutation.isPending ? 'Saving...' : 'Save'}</button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-card rounded-lg border border-border shadow-elegant p-5">
        <div className="flex items-center gap-2 mb-3">
          <SlidersHorizontal className="h-4 w-4 text-primary" />
          <h3 className="font-semibold text-foreground">Parameters & Variables</h3>
        </div>
        {variablesLoading ? (
          <div className="text-sm text-muted-foreground">Loading...</div>
        ) : !variables || variables.length === 0 ? (
          <div className="text-sm text-muted-foreground">No items yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-muted/50">
                <tr>
                  <Th>Kind</Th>
                  <Th>Key</Th>
                  <Th>Value</Th>
                  <Th>Description</Th>
                  <Th>Actions</Th>
                </tr>
              </thead>
              <tbody className="bg-card divide-y divide-border">
                {variables.map((item: ProjectVariable) => (
                  editingId === item.id ? (
                    <tr key={item.id} className="bg-accent/30">
                      <Td>
                        <select
                          value={editForm.kind}
                          onChange={(e) => setEditForm({ ...editForm, kind: e.target.value as ProjectVariable['kind'] })}
                          title="Select item kind"
                          className="w-full min-w-28 px-2 py-1.5 bg-background border border-input rounded-md text-sm text-foreground"
                        >
                          <option value="variable">Variable</option>
                          <option value="parameter">Parameter</option>
                        </select>
                      </Td>
                      <Td>
                        <input
                          value={editForm.key}
                          onChange={(e) => setEditForm({ ...editForm, key: e.target.value })}
                          title="Variable or parameter key"
                          placeholder="Enter a key"
                          className="w-full min-w-40 px-2 py-1.5 bg-background border border-input rounded-md text-sm text-foreground font-mono"
                        />
                      </Td>
                      <Td>
                        <textarea
                          rows={2}
                          value={editForm.value}
                          onChange={(e) => setEditForm({ ...editForm, value: e.target.value })}
                          title="Variable or parameter value"
                          placeholder="Enter a value"
                          className="w-full min-w-64 px-2 py-1.5 bg-background border border-input rounded-md text-sm text-foreground font-mono"
                        />
                      </Td>
                      <Td>
                        <textarea
                          rows={2}
                          value={editForm.description}
                          onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                          title="Optional description"
                          placeholder="Optional description"
                          className="w-full min-w-48 px-2 py-1.5 bg-background border border-input rounded-md text-sm text-foreground"
                        />
                      </Td>
                      <Td>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={onEdit}
                            disabled={updateMutation.isPending}
                            className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-primary text-white hover:bg-primary/90 disabled:opacity-50"
                          >
                            Save
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingId(null)}
                            className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded border border-input text-foreground hover:bg-accent/50"
                          >
                            <X className="h-3.5 w-3.5" />
                            Cancel
                          </button>
                        </div>
                      </Td>
                    </tr>
                  ) : (
                    <tr key={item.id} className="hover:bg-accent/50">
                      <Td><span className="font-mono text-sm text-foreground">{item.kind}</span></Td>
                      <Td><span className="font-mono text-sm text-foreground">{item.key}</span></Td>
                      <Td><span className="font-mono text-xs text-muted-foreground">{item.value}</span></Td>
                      <Td>{item.description || '-'}</Td>
                      <Td>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => setEditingId(item.id)}
                            className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded border border-input text-foreground hover:bg-accent/50"
                          >
                            <Edit2 className="h-3.5 w-3.5" />
                            Edit
                          </button>
                          <button
                            onClick={() => deleteMutation.mutate(item.id)}
                            className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded border border-red-500/50 text-red-600 hover:bg-red-500/10"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            Delete
                          </button>
                        </div>
                      </Td>
                    </tr>
                  )
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <IntegrationSettingsPanel projectId={projectId} />
    </div>
  )
}

function IntegrationSettingsPanel({ projectId }: { projectId: number }) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const isAdmin = user?.role === 'admin'

  const { data: settings, isLoading } = useQuery({
    queryKey: ['integrationSettings', projectId],
    queryFn: () => integrationsApi.listSettings(projectId),
    enabled: !!projectId,
  })

  const byTracker = useMemo(() => {
    const map = new Map<TrackerKind, IntegrationSetting>()
    settings?.forEach((s) => {
      if (s.tracker === 'github' || s.tracker === 'gitlab') {
        map.set(s.tracker, s)
      }
    })
    return map
  }, [settings])

  return (
    <div className="bg-card rounded-lg border border-border shadow-elegant p-5">
      <div className="flex items-center gap-2 mb-1">
        <GitBranch className="h-4 w-4 text-primary" />
        <h3 className="font-semibold text-foreground">External Tracker Integrations</h3>
      </div>
      <p className="text-xs text-muted-foreground mb-4">
        Connect this project to GitHub or GitLab so defects sync bidirectionally with linked issues.
        Tokens are stored server-side and never returned to the browser.
        {!isAdmin && ' Only project admins can change these settings.'}
      </p>

      {isLoading ? (
        <div className="text-sm text-muted-foreground">Loading...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {(['github', 'gitlab'] as TrackerKind[]).map((tracker) => (
            <IntegrationTrackerCard
              key={tracker}
              projectId={projectId}
              tracker={tracker}
              setting={byTracker.get(tracker) ?? null}
              isAdmin={isAdmin}
              onChanged={() =>
                queryClient.invalidateQueries({ queryKey: ['integrationSettings', projectId] })
              }
            />
          ))}
        </div>
      )}
    </div>
  )
}

function IntegrationTrackerCard({
  projectId,
  tracker,
  setting,
  isAdmin,
  onChanged,
}: {
  projectId: number
  tracker: TrackerKind
  setting: IntegrationSetting | null
  isAdmin: boolean
  onChanged: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [baseUrl, setBaseUrl] = useState('')
  const [token, setToken] = useState('')
  const [webhookSecret, setWebhookSecret] = useState('')
  const [enabled, setEnabled] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!editing) {
      setBaseUrl(setting?.base_url ?? '')
      setToken('')
      setWebhookSecret(setting?.webhook_secret ?? '')
      setEnabled(setting?.enabled ?? true)
      setError(null)
    }
  }, [editing, setting])

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (setting) {
        const payload: Parameters<typeof integrationsApi.updateSetting>[1] = {
          base_url: baseUrl || undefined,
          webhook_secret: webhookSecret || undefined,
          enabled,
        }
        if (token) payload.token = token
        return integrationsApi.updateSetting(setting.id, payload)
      }
      return integrationsApi.createSetting({
        project_id: projectId,
        tracker,
        base_url: baseUrl || undefined,
        token: token || undefined,
        webhook_secret: webhookSecret || undefined,
        enabled,
      })
    },
    onSuccess: () => {
      onChanged()
      setEditing(false)
    },
    onError: (err) => setError(extractApiErrorMessage(err, 'Failed to save integration')),
  })

  const deleteMutation = useMutation({
    mutationFn: () => {
      if (!setting) return Promise.resolve()
      return integrationsApi.deleteSetting(setting.id)
    },
    onSuccess: () => {
      onChanged()
      setEditing(false)
    },
    onError: (err) => setError(extractApiErrorMessage(err, 'Failed to delete integration')),
  })

  const label = TRACKER_LABELS[tracker]
  const webhookPath = WEBHOOK_PATHS[tracker]

  return (
    <div className="rounded-md border border-border bg-background/40 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-foreground">{label}</div>
          <div className="mt-0.5 text-xs text-muted-foreground">
            {setting
              ? setting.enabled
                ? 'Enabled'
                : 'Disabled'
              : 'Not configured'}
            {setting?.has_token && ' · token stored'}
          </div>
        </div>
        {isAdmin && !editing && (
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="text-xs px-2 py-1 rounded border border-input hover:bg-accent/50 inline-flex items-center gap-1"
          >
            <Edit2 className="h-3 w-3" />
            {setting ? 'Edit' : 'Configure'}
          </button>
        )}
      </div>

      {editing ? (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            setError(null)
            saveMutation.mutate()
          }}
          className="mt-3 space-y-3"
        >
          {tracker === 'gitlab' && (
            <div>
              <label className="block text-xs uppercase tracking-wide text-muted-foreground mb-1">
                Base URL
              </label>
              <input
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://gitlab.example.com"
                className="w-full px-3 py-1.5 text-sm bg-background border border-input rounded-md"
              />
            </div>
          )}
          <div>
            <label className="block text-xs uppercase tracking-wide text-muted-foreground mb-1">
              {setting?.has_token ? 'Replace token (leave empty to keep current)' : 'Token'}
            </label>
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder={tracker === 'github' ? 'ghp_… or fine-grained PAT' : 'glpat-…'}
              className="w-full px-3 py-1.5 text-sm bg-background border border-input rounded-md font-mono"
              autoComplete="new-password"
            />
          </div>
          <div>
            <label className="block text-xs uppercase tracking-wide text-muted-foreground mb-1">
              Webhook secret
            </label>
            <input
              value={webhookSecret}
              onChange={(e) => setWebhookSecret(e.target.value)}
              placeholder="Shared secret for inbound webhooks"
              className="w-full px-3 py-1.5 text-sm bg-background border border-input rounded-md font-mono"
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="rounded"
            />
            Enabled
          </label>
          {error && <div className="text-xs text-destructive">{error}</div>}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={saveMutation.isPending}
                className="text-xs px-3 py-1.5 rounded bg-primary text-white hover:bg-primary/90 disabled:opacity-50"
              >
                {saveMutation.isPending ? 'Saving...' : 'Save'}
              </button>
              <button
                type="button"
                onClick={() => setEditing(false)}
                className="text-xs px-3 py-1.5 rounded border border-input hover:bg-accent/50"
              >
                Cancel
              </button>
            </div>
            {setting && (
              <button
                type="button"
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
                className="text-xs px-3 py-1.5 rounded border border-red-500/50 text-red-600 hover:bg-red-500/10 disabled:opacity-50 inline-flex items-center gap-1"
              >
                <Trash2 className="h-3 w-3" />
                Remove
              </button>
            )}
          </div>
        </form>
      ) : (
        <div className="mt-3 space-y-1 text-xs text-muted-foreground">
          {setting?.base_url && (
            <div>
              Base URL: <code className="font-mono text-foreground">{setting.base_url}</code>
            </div>
          )}
          <div>
            Inbound webhook: <code className="font-mono text-foreground">{webhookPath}</code>
          </div>
          {setting?.webhook_secret && <div>Webhook secret stored.</div>}
        </div>
      )}
    </div>
  )
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">{children}</th>
}

function Td({ children }: { children: React.ReactNode }) {
  return <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">{children}</td>
}
