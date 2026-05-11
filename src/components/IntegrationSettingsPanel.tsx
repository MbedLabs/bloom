import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { GitBranch } from 'lucide-react'

import { extractApiErrorMessage, integrationsApi } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

export type TrackerChoice = 'none' | 'github' | 'gitlab'

type TrackerKind = 'github' | 'gitlab'

const TRACKER_LABELS: Record<TrackerKind, string> = { github: 'GitHub', gitlab: 'GitLab' }

const WEBHOOK_PATHS: Record<TrackerKind, string> = {
  github: '/api/integrations/github/webhook',
  gitlab: '/api/integrations/gitlab/webhook',
}

/** One external tracker per project: None | GitHub | GitLab. */
export default function IntegrationSettingsPanel({ projectId }: { projectId: number }) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const isAdmin = user?.role === 'admin'

  const { data: settings, isLoading } = useQuery({
    queryKey: ['integrationSettings', projectId],
    queryFn: () => integrationsApi.listSettings(projectId),
    enabled: !!projectId,
  })

  const githubSetting = useMemo(
    () => settings?.find((s) => s.tracker === 'github') ?? null,
    [settings]
  )
  const gitlabSetting = useMemo(
    () => settings?.find((s) => s.tracker === 'gitlab') ?? null,
    [settings]
  )

  const activeFromServer: TrackerChoice = githubSetting
    ? 'github'
    : gitlabSetting
      ? 'gitlab'
      : 'none'

  const [choice, setChoice] = useState<TrackerChoice>('none')
  const [baseUrl, setBaseUrl] = useState('')
  const [token, setToken] = useState('')
  const [webhookSecret, setWebhookSecret] = useState('')
  const [enabled, setEnabled] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    if (!settings) return
    setChoice(activeFromServer)
    const cur = activeFromServer === 'github' ? githubSetting : activeFromServer === 'gitlab' ? gitlabSetting : null
    setBaseUrl(cur?.base_url ?? '')
    setToken('')
    setWebhookSecret(cur?.webhook_secret ?? '')
    setEnabled(cur?.enabled ?? true)
    setError(null)
    setDirty(false)
  }, [settings, activeFromServer, githubSetting, gitlabSetting])

  const confirmRemove = (row: { has_token: boolean; webhook_secret: string | null; base_url: string | null }) => {
    const hasData =
      row.has_token || (row.webhook_secret && row.webhook_secret.length > 0) || (row.base_url && row.base_url.length > 0)
    if (!hasData) return true
    return window.confirm('This removes the stored integration (token and webhook settings) for this project. Continue?')
  }

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (choice === 'none') {
        const rows = [githubSetting, gitlabSetting].filter((r): r is NonNullable<typeof r> => r != null)
        if (rows.length > 0) {
          const hasData = rows.some(
            (r) =>
              r.has_token ||
              (r.webhook_secret && r.webhook_secret.length > 0) ||
              (r.base_url && r.base_url.length > 0)
          )
          if (hasData && !window.confirm('Remove all external tracker configuration for this project?')) {
            throw new Error('cancelled')
          }
          for (const r of rows) {
            await integrationsApi.deleteSetting(r.id)
          }
        }
        return
      }

      const otherRow: typeof githubSetting = choice === 'github' ? gitlabSetting : githubSetting
      const targetRow = choice === 'github' ? githubSetting : gitlabSetting

      if (otherRow) {
        if (!confirmRemove(otherRow)) throw new Error('cancelled')
        await integrationsApi.deleteSetting(otherRow.id)
      }

      if (targetRow) {
        const payload: Parameters<typeof integrationsApi.updateSetting>[1] = {
          base_url: choice === 'gitlab' ? baseUrl || undefined : undefined,
          webhook_secret: webhookSecret || undefined,
          enabled,
        }
        if (token) payload.token = token
        await integrationsApi.updateSetting(targetRow.id, payload)
        return
      }

      await integrationsApi.createSetting({
        project_id: projectId,
        tracker: choice,
        base_url: choice === 'gitlab' ? baseUrl || undefined : undefined,
        token: token || undefined,
        webhook_secret: webhookSecret || undefined,
        enabled,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['integrationSettings', projectId] })
      setToken('')
      setDirty(false)
    },
    onError: (err: unknown) => {
      if (err instanceof Error && err.message === 'cancelled') {
        setError(null)
        return
      }
      setError(extractApiErrorMessage(err, 'Failed to save integration'))
    },
  })

  const onChoiceChange = (next: TrackerChoice) => {
    setChoice(next)
    setDirty(true)
    setError(null)
    if (next === 'none') {
      setBaseUrl('')
      setToken('')
      setWebhookSecret('')
      setEnabled(true)
      return
    }
    const row = next === 'github' ? githubSetting : gitlabSetting
    setBaseUrl(row?.base_url ?? '')
    setToken('')
    setWebhookSecret(row?.webhook_secret ?? '')
    setEnabled(row?.enabled ?? true)
  }

  const webhookPath = choice === 'none' ? null : WEBHOOK_PATHS[choice]
  const currentRow = choice === 'github' ? githubSetting : choice === 'gitlab' ? gitlabSetting : null

  return (
    <div className="bg-card rounded-lg border border-border shadow-elegant p-5">
      <div className="flex items-center gap-2 mb-1">
        <GitBranch className="h-4 w-4 text-primary" />
        <h3 className="font-semibold text-foreground">External issue tracker</h3>
      </div>
      <p className="text-xs text-muted-foreground mb-4">
        Connect at most one tracker so defects can sync with linked issues. Tokens stay on the server and are never
        returned to the browser.
        {!isAdmin && ' Only project admins can change these settings.'}
      </p>

      {isLoading ? (
        <div className="text-sm text-muted-foreground">Loading...</div>
      ) : !isAdmin ? (
        <div className="rounded-md border border-border bg-background/40 p-4 text-sm text-muted-foreground">
          {activeFromServer === 'none'
            ? 'No external tracker configured.'
            : `${TRACKER_LABELS[activeFromServer]} is configured for this project.`}
        </div>
      ) : (
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault()
            setError(null)
            if (choice !== 'none' && !currentRow && !token.trim()) {
              setError('Enter an API token to create this integration.')
              return
            }
            saveMutation.mutate()
          }}
        >
          <fieldset className="space-y-2">
            <legend className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-2">Tracker</legend>
            <div className="flex flex-wrap gap-4">
              {(['none', 'github', 'gitlab'] as const).map((v) => (
                <label key={v} className="inline-flex items-center gap-2 text-sm text-foreground cursor-pointer">
                  <input
                    type="radio"
                    name="tracker-choice"
                    checked={choice === v}
                    onChange={() => onChoiceChange(v)}
                    className="rounded-full"
                  />
                  {v === 'none' ? 'None' : TRACKER_LABELS[v]}
                </label>
              ))}
            </div>
          </fieldset>

          {choice !== 'none' && (
            <div className="rounded-md border border-border bg-background/40 p-4 space-y-3">
              {choice === 'gitlab' && (
                <div>
                  <label className="block text-xs uppercase tracking-wide text-muted-foreground mb-1">Base URL</label>
                  <input
                    value={baseUrl}
                    onChange={(e) => {
                      setBaseUrl(e.target.value)
                      setDirty(true)
                    }}
                    placeholder="https://gitlab.example.com"
                    className="w-full px-3 py-1.5 text-sm bg-background border border-input rounded-md"
                  />
                </div>
              )}
              <div>
                <label className="block text-xs uppercase tracking-wide text-muted-foreground mb-1">
                  {currentRow?.has_token ? 'Replace token (leave empty to keep current)' : 'Token'}
                </label>
                <input
                  type="password"
                  value={token}
                  onChange={(e) => {
                    setToken(e.target.value)
                    setDirty(true)
                  }}
                  placeholder={choice === 'github' ? 'ghp_… or fine-grained PAT' : 'glpat-…'}
                  className="w-full px-3 py-1.5 text-sm bg-background border border-input rounded-md font-mono"
                  autoComplete="new-password"
                />
              </div>
              <div>
                <label className="block text-xs uppercase tracking-wide text-muted-foreground mb-1">Webhook secret</label>
                <input
                  value={webhookSecret}
                  onChange={(e) => {
                    setWebhookSecret(e.target.value)
                    setDirty(true)
                  }}
                  placeholder="Shared secret for inbound webhooks"
                  className="w-full px-3 py-1.5 text-sm bg-background border border-input rounded-md font-mono"
                />
              </div>
              <label className="flex items-center gap-2 text-sm text-foreground">
                <input
                  type="checkbox"
                  checked={enabled}
                  onChange={(e) => {
                    setEnabled(e.target.checked)
                    setDirty(true)
                  }}
                  className="rounded"
                />
                Enabled
              </label>
              {webhookPath && (
                <div className="text-xs text-muted-foreground">
                  Inbound webhook: <code className="font-mono text-foreground">{webhookPath}</code>
                </div>
              )}
            </div>
          )}

          {error && <div className="text-xs text-destructive">{error}</div>}
          <button
            type="submit"
            disabled={saveMutation.isPending || (!dirty && choice === activeFromServer)}
            className="text-sm px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {saveMutation.isPending ? 'Saving...' : 'Save integration'}
          </button>
        </form>
      )}
    </div>
  )
}
