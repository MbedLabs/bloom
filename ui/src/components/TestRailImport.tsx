import { useState } from 'react'
import { useNavigate } from 'react-router'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Download, FileUp } from 'lucide-react'
import { importApi, type TestRailField, type TestRailImportResult } from '../api/client'
import { useToast } from './useToast'

const MAPPED_FIELDS: { key: TestRailField; label: string }[] = [
  { key: 'title', label: 'Title' },
  { key: 'id', label: 'ID' },
  { key: 'section_hierarchy', label: 'Section hierarchy' },
  { key: 'section', label: 'Section' },
  { key: 'preconditions', label: 'Preconditions' },
  { key: 'steps', label: 'Steps (text template)' },
  { key: 'expected', label: 'Expected result (text template)' },
  { key: 'step', label: 'Steps (Step)' },
  { key: 'step_expected', label: 'Steps (Expected Result)' },
  { key: 'references', label: 'References' },
  { key: 'type', label: 'Type' },
  { key: 'priority', label: 'Priority' },
  { key: 'estimate', label: 'Estimate' },
]

/** Import a TestRail XML or CSV export, with a column-mapping step for CSV. */
export default function TestRailImport({ projectId, prefix }: { projectId: number; prefix?: string }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()
  const [format, setFormat] = useState<'xml' | 'csv'>('xml')
  const [file, setFile] = useState<File | null>(null)
  const [columns, setColumns] = useState<string[]>([])
  const [mapping, setMapping] = useState<Partial<Record<TestRailField, string>>>({})
  const [result, setResult] = useState<TestRailImportResult | null>(null)

  const detect = useMutation({
    mutationFn: (upload: File) => importApi.testRailColumns(projectId, upload),
    onSuccess: (data) => {
      setColumns(data.columns)
      setMapping(data.detected)
      toast.notify(`Found ${data.columns.length} columns`, 'success')
    },
    onError: (err) => toast.failed('Reading the columns', err),
  })

  const run = useMutation({
    mutationFn: () =>
      importApi.importTestRail(projectId, file as File, format, format === 'csv' ? mapping : undefined),
    onSuccess: (data) => {
      setResult(data)
      toast.notify(`TestRail import: ${data.created} created, ${data.updated} updated`, 'success')
      queryClient.invalidateQueries({ queryKey: ['testCases', projectId] })
      queryClient.invalidateQueries({ queryKey: ['all-docs', prefix] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
    },
    onError: (err) => {
      setResult(null)
      toast.failed('Importing from TestRail', err)
    },
  })

  const choose = (upload: File | null) => {
    setFile(upload)
    setResult(null)
    setColumns([])
    setMapping({})
    if (upload && format === 'csv') detect.mutate(upload)
  }

  const needsTitle = format === 'csv' && columns.length > 0 && !mapping.title

  return (
    <div className="bg-card rounded-lg border border-border shadow-elegant p-6 space-y-4">
      <h3 className="text-lg font-semibold text-foreground">Import test cases from TestRail</h3>
      <p className="text-sm text-muted-foreground">
        Upload a suite exported from TestRail as XML, or a CSV export. Each top-level section becomes a
        test suite, references that match a requirement become verifies links, and importing the same
        export again updates the cases it created.
      </p>

      <div className="flex gap-2">
        {(['xml', 'csv'] as const).map((f) => (
          <button
            key={f}
            onClick={() => {
              setFormat(f)
              setFile(null)
              setColumns([])
              setMapping({})
              setResult(null)
            }}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              format === f ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground hover:text-foreground'
            }`}
          >
            {f.toUpperCase()}
          </button>
        ))}
      </div>

      <label className="flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-border p-8 cursor-pointer hover:border-primary/40 hover:bg-accent/30 transition-colors">
        <FileUp className="h-6 w-6 text-muted-foreground" />
        <span className="text-sm text-foreground font-medium">
          {file ? file.name : `Choose a TestRail ${format.toUpperCase()} export`}
        </span>
        <input
          type="file"
          aria-label="TestRail export file"
          accept={format === 'xml' ? '.xml,application/xml' : '.csv,text/csv'}
          className="hidden"
          onChange={(e) => choose(e.target.files?.[0] ?? null)}
        />
      </label>

      {format === 'csv' && columns.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm text-foreground font-medium">Columns</p>
          <p className="text-xs text-muted-foreground">
            Bloom matched these from the header. Point any field at a different column before importing.
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            {MAPPED_FIELDS.map((f) => (
              <label key={f.key} className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
                {f.label}
                <select
                  aria-label={f.label}
                  value={mapping[f.key] ?? ''}
                  onChange={(e) => setMapping((m) => ({ ...m, [f.key]: e.target.value }))}
                  className="w-1/2 px-2 py-1 bg-background border border-input rounded text-xs text-foreground"
                >
                  <option value="">(none)</option>
                  {columns.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </label>
            ))}
          </div>
          {needsTitle && <p className="text-xs text-destructive">Choose the column that holds the title.</p>}
        </div>
      )}

      <div className="flex justify-end">
        <button
          onClick={() => run.mutate()}
          disabled={!file || run.isPending || needsTitle || (format === 'csv' && detect.isPending)}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 disabled:opacity-50 inline-flex items-center gap-2"
        >
          <Download className="h-4 w-4" />
          {run.isPending ? 'Importing...' : 'Import from TestRail'}
        </button>
      </div>

      {result && (
        <div className="space-y-3">
          <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 p-4 space-y-2">
            <div className="text-emerald-700 dark:text-emerald-400 font-medium">
              {result.created} created &middot; {result.updated} updated
              {result.skipped > 0 && ` · ${result.skipped} skipped`}
            </div>
            <div className="text-sm text-muted-foreground">
              {result.suites_created.length} suite(s) created &middot; {result.links_created} requirement link(s)
            </div>
            {result.new_ids.length > 0 && (
              <div className="text-sm text-muted-foreground">New IDs: {result.new_ids.join(', ')}</div>
            )}
          </div>
          {result.errors.length > 0 && (
            <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-4 space-y-1">
              <div className="flex items-center gap-2 text-red-700 dark:text-red-400 font-medium">
                <AlertCircle className="h-4 w-4" />
                Warnings
              </div>
              {result.errors.map((err, i) => (
                <div key={i} className="text-sm text-red-600 dark:text-red-400">{err}</div>
              ))}
            </div>
          )}
          <button
            onClick={() => navigate(`/projects/${prefix}/docs`)}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90"
          >
            View test cases
          </button>
        </div>
      )}
    </div>
  )
}
