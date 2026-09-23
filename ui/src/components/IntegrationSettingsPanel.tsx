import { useCallback, useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { GitBranch } from 'lucide-react'

import { extractApiErrorMessage, integrationsApi, type JiraPullResult } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from './useToast'

export type TrackerChoice = 'none' | 'github' | 'gitlab' | 'jira'

type TrackerKind = 'github' | 'gitlab' | 'jira'

const TRACKER_LABELS: Record<TrackerKind, string> = { github: 'GitHub', gitlab: 'GitLab', jira: 'Jira' }

const WEBHOOK_PATHS: Record<TrackerKind, string> = {
  github: '/api/integrations/github/webhook',
  gitlab: '/api/integrations/gitlab/webhook',
  jira: '/api/integrations/jira/webhook',
}

const JIRA_PRIORITIES = ['Highest', 'High', 'Medium', 'Low', 'Lowest'] as const
const BLOOM_LEVELS = ['Critical', 'High', 'Medium', 'Low'] as const
const DEFAULT_PRIORITY_MAP: Record<string, string> = {
  Highest: 'Critical',
  High: 'High',
  Medium: 'Medium',
  Low: 'Low',
  Lowest: 'Low',
}

const inputClass = 'w-full px-3 py-1.5 text-sm bg-background border border-input rounded-md'
const labelClass = 'block text-xs uppercase tracking-wide text-muted-foreground mb-1'

/** One external tracker per project: None | GitHub | GitLab | Jira. */
export default function IntegrationSettingsPanel({ projectId }: { projectId: number }) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const toast = useToast()
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
  const jiraSetting = useMemo(
    () => settings?.find((s) => s.tracker === 'jira') ?? null,
    [settings]
  )

  const activeFromServer: TrackerChoice = githubSetting
    ? 'github'
    : gitlabSetting
      ? 'gitlab'
      : jiraSetting
        ? 'jira'
        : 'none'
  const rowFor = (kind: TrackerChoice) =>
    kind === 'github' ? githubSetting : kind === 'gitlab' ? gitlabSetting : kind === 'jira' ? jiraSetting : null

  const [choice, setChoice] = useState<TrackerChoice>('none')
  const [baseUrl, setBaseUrl] = useState('')
  const [token, setToken] = useState('')
  const [webhookSecret, setWebhookSecret] = useState('')
  const [enabled, setEnabled] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)
  const [accountEmail, setAccountEmail] = useState('')
  const [jiraProjectKey, setJiraProjectKey] = useState('')
  const [createOnInbound, setCreateOnInbound] = useState(true)
  const [issueTypes, setIssueTypes] = useState('Bug')
  const [jiraLabel, setJiraLabel] = useState('')
  const [jiraJql, setJiraJql] = useState('')
  const [referenceField, setReferenceField] = useState('')
  const [priorityMap, setPriorityMap] = useState<Record<string, string>>(DEFAULT_PRIORITY_MAP)
  const [twoWay, setTwoWay] = useState(false)
  const [pulled, setPulled] = useState<JiraPullResult | null>(null)

  const loadJira = useCallback((row: typeof jiraSetting) => {
    setAccountEmail(row?.account_email ?? '')
    setJiraProjectKey(row?.jira_project_key ?? '')
    setCreateOnInbound(row?.create_defects_on_inbound ?? true)
    setIssueTypes((row?.jira_issue_types?.length ? row.jira_issue_types : ['Bug']).join(', '))
    setJiraLabel(row?.jira_label ?? '')
    setJiraJql(row?.jira_jql ?? '')
    setReferenceField(row?.jira_reference_field ?? '')
    setPriorityMap({ ...DEFAULT_PRIORITY_MAP, ...(row?.jira_priority_map ?? {}) })
    setTwoWay(row?.two_way ?? false)
  }, [])

  const jiraFields = () => ({
    account_email: accountEmail || undefined,
    jira_project_key: jiraProjectKey.trim() || undefined,
    create_defects_on_inbound: createOnInbound,
    jira_issue_types: issueTypes
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean),
    jira_label: jiraLabel.trim(),
    jira_jql: jiraJql.trim(),
    jira_reference_field: referenceField.trim(),
    jira_priority_map: priorityMap,
    two_way: twoWay,
  })

  const touch = <T,>(set: (value: T) => void) => (value: T) => {
    set(value)
    setDirty(true)
  }

  useEffect(() => {
    if (!settings) return
    setChoice(activeFromServer)
    const cur = activeFromServer === 'github' ? githubSetting : activeFromServer === 'gitlab' ? gitlabSetting : activeFromServer === 'jira' ? jiraSetting : null
    setBaseUrl(cur?.base_url ?? '')
    loadJira(jiraSetting)
    setToken('')
    setWebhookSecret('')
    setEnabled(cur?.enabled ?? true)
    setError(null)
    setDirty(false)
  }, [settings, activeFromServer, githubSetting, gitlabSetting, jiraSetting, loadJira])

  const confirmRemove = (row: { has_token: boolean; has_webhook_secret: boolean; base_url: string | null }) => {
    const hasData = row.has_token || row.has_webhook_secret || (row.base_url && row.base_url.length > 0)
    if (!hasData) return true
    return window.confirm('This removes the stored integration (token and webhook settings) for this project. Continue?')
  }

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (choice === 'none') {
        const rows = [githubSetting, gitlabSetting, jiraSetting].filter((r): r is NonNullable<typeof r> => r != null)
        if (rows.length > 0) {
          const hasData = rows.some(
            (r) =>
              r.has_token ||
              r.has_webhook_secret ||
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

      const targetRow = rowFor(choice)
      const otherRows = [githubSetting, gitlabSetting, jiraSetting].filter(
        (r): r is NonNullable<typeof r> => r != null && r !== targetRow,
      )

      for (const otherRow of otherRows) {
        if (!confirmRemove(otherRow)) throw new Error('cancelled')
        await integrationsApi.deleteSetting(otherRow.id)
      }
      const siteUrl = choice === 'github' ? undefined : baseUrl || undefined
      const extra = choice === 'jira' ? jiraFields() : {}

      if (targetRow) {
        const payload: Parameters<typeof integrationsApi.updateSetting>[1] = {
          base_url: siteUrl,
          webhook_secret: webhookSecret || undefined,
          enabled,
          ...extra,
        }
        if (token) payload.token = token
        await integrationsApi.updateSetting(targetRow.id, payload)
        return
      }

      await integrationsApi.createSetting({
        project_id: projectId,
        tracker: choice,
        base_url: siteUrl,
        token: token || undefined,
        webhook_secret: webhookSecret || undefined,
        enabled,
        ...extra,
      })
    },
    onSuccess: (_updated) => {
      void _updated
      queryClient.invalidateQueries({ queryKey: ['integrationSettings', projectId] })
      setToken('')
      setDirty(false)
      toast.saved('Integration')
    },
    onError: (err: unknown) => {
      if (err instanceof Error && err.message === 'cancelled') {
        setError(null)
        return
      }
      setError(extractApiErrorMessage(err, 'Failed to save integration'))
      toast.failed('Saving the integration', err)
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
    const row = rowFor(next)
    setBaseUrl(row?.base_url ?? '')
    loadJira(jiraSetting)
    setToken('')
    setWebhookSecret('')
    setEnabled(row?.enabled ?? true)
  }

  const pullMutation = useMutation({
    mutationFn: (id: number) => integrationsApi.pullJira(id),
    onSuccess: (result) => {
      setPulled(result)
      queryClient.invalidateQueries({ queryKey: ['defects'] })
      toast.notify(`Pulled from Jira: ${result.created} defect(s) created`, 'success')
    },
    onError: (err: unknown) => toast.failed('Pulling from Jira', err),
  })

  const webhookPath = choice === 'none' ? null : WEBHOOK_PATHS[choice]
  const currentRow = rowFor(choice)

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
              {(['none', 'github', 'gitlab', 'jira'] as const).map((v) => (
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
              {choice !== 'github' && (
                <div>
                  <label className="block text-xs uppercase tracking-wide text-muted-foreground mb-1">
                    {choice === 'jira' ? 'Site URL' : 'Base URL'}
                  </label>
                  <input
                    value={baseUrl}
                    onChange={(e) => {
                      setBaseUrl(e.target.value)
                      setDirty(true)
                    }}
                    placeholder={choice === 'jira' ? 'https://your-site.atlassian.net' : 'https://gitlab.example.com'}
                    className="w-full px-3 py-1.5 text-sm bg-background border border-input rounded-md"
                  />
                </div>
              )}
              {choice === 'jira' && (
                <div>
                  <label className={labelClass}>Account email</label>
                  <input
                    value={accountEmail}
                    onChange={(e) => touch(setAccountEmail)(e.target.value)}
                    placeholder="The Atlassian account the API token belongs to"
                    className={inputClass}
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
                  placeholder={choice === 'github' ? 'ghp_… or fine-grained PAT' : choice === 'jira' ? 'Atlassian API token' : 'glpat-…'}
                  className="w-full px-3 py-1.5 text-sm bg-background border border-input rounded-md font-mono"
                  autoComplete="new-password"
                />
              </div>
              <div>
                <label className="block text-xs uppercase tracking-wide text-muted-foreground mb-1">
                  {currentRow?.has_webhook_secret
                    ? 'Replace webhook secret (leave empty to keep current)'
                    : 'Webhook secret'}
                </label>
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
              {choice === 'jira' && (
                <JiraFields
                  projectKey={jiraProjectKey}
                  onProjectKey={touch(setJiraProjectKey)}
                  createOnInbound={createOnInbound}
                  onCreateOnInbound={touch(setCreateOnInbound)}
                  issueTypes={issueTypes}
                  onIssueTypes={touch(setIssueTypes)}
                  label={jiraLabel}
                  onLabel={touch(setJiraLabel)}
                  jql={jiraJql}
                  onJql={touch(setJiraJql)}
                  referenceField={referenceField}
                  onReferenceField={touch(setReferenceField)}
                  priorityMap={priorityMap}
                  onPriorityMap={touch(setPriorityMap)}
                  twoWay={twoWay}
                  onTwoWay={touch(setTwoWay)}
                />
              )}
              {webhookPath && (
                <div className="text-xs text-muted-foreground">
                  Inbound webhook: <code className="font-mono text-foreground">{webhookPath}</code>
                </div>
              )}
              {choice === 'jira' && jiraSetting && (
                <div className="flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={() => pullMutation.mutate(jiraSetting.id)}
                    disabled={pullMutation.isPending || dirty}
                    className="text-sm px-3 py-1.5 rounded-md border border-border hover:bg-accent disabled:opacity-50"
                  >
                    {pullMutation.isPending ? 'Pulling...' : 'Pull existing issues'}
                  </button>
                  <span className="text-xs text-muted-foreground">
                    {dirty
                      ? 'Save first; the pull uses the saved filter.'
                      : pulled
                        ? `Found ${pulled.searched}: ${pulled.created} created, ${pulled.already_linked} already linked, ${pulled.skipped} skipped.`
                        : 'Creates the defects for issues that match the filter. Reads from Jira only.'}
                  </span>
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

/** The Jira inbound filter, priority map and sync direction. */
function JiraFields(props: {
  projectKey: string
  onProjectKey: (value: string) => void
  createOnInbound: boolean
  onCreateOnInbound: (value: boolean) => void
  issueTypes: string
  onIssueTypes: (value: string) => void
  label: string
  onLabel: (value: string) => void
  jql: string
  onJql: (value: string) => void
  referenceField: string
  onReferenceField: (value: string) => void
  priorityMap: Record<string, string>
  onPriorityMap: (value: Record<string, string>) => void
  twoWay: boolean
  onTwoWay: (value: boolean) => void
}) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label className={labelClass}>Jira project key</label>
          <input
            value={props.projectKey}
            onChange={(e) => props.onProjectKey(e.target.value)}
            placeholder="PROJ"
            className={`${inputClass} font-mono`}
          />
        </div>
        <div>
          <label className={labelClass}>Issue types</label>
          <input
            value={props.issueTypes}
            onChange={(e) => props.onIssueTypes(e.target.value)}
            placeholder="Bug"
            title="Comma-separated Jira issue types"
            className={inputClass}
          />
        </div>
        <div>
          <label className={labelClass}>Label (optional)</label>
          <input
            value={props.label}
            onChange={(e) => props.onLabel(e.target.value)}
            placeholder="Only issues with this label"
            className={inputClass}
          />
        </div>
        <div>
          <label className={labelClass}>Test case reference field (optional)</label>
          <input
            value={props.referenceField}
            onChange={(e) => props.onReferenceField(e.target.value)}
            placeholder="customfield_10042"
            className={`${inputClass} font-mono`}
          />
        </div>
      </div>
      <div>
        <label className={labelClass}>Extra JQL for the pull (optional)</label>
        <input
          value={props.jql}
          onChange={(e) => props.onJql(e.target.value)}
          placeholder='created >= "2026-01-01"'
          className={`${inputClass} font-mono`}
        />
      </div>
      <fieldset>
        <legend className={labelClass}>Jira priority to Bloom priority</legend>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
          {JIRA_PRIORITIES.map((jira) => (
            <label key={jira} className="text-xs text-muted-foreground">
              {jira}
              <select
                aria-label={`Bloom priority for Jira ${jira}`}
                value={props.priorityMap[jira]}
                onChange={(e) => props.onPriorityMap({ ...props.priorityMap, [jira]: e.target.value })}
                className={`${inputClass} mt-1`}
              >
                {BLOOM_LEVELS.map((level) => (
                  <option key={level} value={level}>
                    {level}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>
      </fieldset>
      <label className="flex items-center gap-2 text-sm text-foreground">
        <input
          type="checkbox"
          checked={props.createOnInbound}
          onChange={(e) => props.onCreateOnInbound(e.target.checked)}
          className="rounded"
        />
        Create a defect for each new matching issue
      </label>
      <label className="flex items-center gap-2 text-sm text-foreground">
        <input
          type="checkbox"
          checked={props.twoWay}
          onChange={(e) => props.onTwoWay(e.target.checked)}
          className="rounded"
        />
        Two-way sync
      </label>
      <p className="text-xs text-muted-foreground">
        {props.twoWay
          ? 'Two-way: Jira issues create and update defects, and Bloom pushes defect title and status changes back to Jira.'
          : 'One-way: Jira issues create and update defects; Bloom never writes to Jira.'}
      </p>
    </div>
  )
}
