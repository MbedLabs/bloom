import { AlertCircle } from 'lucide-react'
import type { MarkdownCollision, MarkdownCollisionAction } from '../api/client'

/**
 * The parameter names of an import that already exist in the project, each with the
 * project's value, the file's value, and the choice to keep the project's value or to
 * import the file's value under a new name.
 */
export default function ParameterCollisions({
  collisions,
  choices,
  onChange,
}: {
  collisions: MarkdownCollision[]
  choices: Record<string, MarkdownCollisionAction>
  onChange: (choices: Record<string, MarkdownCollisionAction>) => void
}) {
  const set = (name: string, choice: MarkdownCollisionAction) => onChange({ ...choices, [name]: choice })

  return (
    <div className="rounded-lg bg-amber-500/10 border border-amber-500/20 p-4 space-y-3">
      <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400 font-medium">
        <AlertCircle className="h-4 w-4" />
        These parameter names already exist. Choose what to do with each; nothing is imported until you do.
      </div>
      {collisions.map((c) => {
        const choice = choices[c.name]
        return (
          <fieldset key={c.name} className="rounded-md border border-border bg-card p-3 space-y-2">
            <legend className="px-1 font-mono text-sm text-foreground">{c.name}</legend>
            <div className="text-xs text-muted-foreground">
              In the project: <span className="font-mono text-foreground">{c.existing_value}</span> &middot; In the
              file: <span className="font-mono text-foreground">{c.imported_value}</span>
            </div>
            <label className="flex items-center gap-2 text-sm text-foreground">
              <input
                type="radio"
                name={`collision-${c.name}`}
                checked={choice?.action === 'existing'}
                onChange={() => set(c.name, { action: 'existing' })}
              />
              Use the project&apos;s value
            </label>
            <label className="flex items-center gap-2 text-sm text-foreground">
              <input
                type="radio"
                name={`collision-${c.name}`}
                checked={choice?.action === 'rename'}
                onChange={() => set(c.name, { action: 'rename', to: `${c.name}_2` })}
              />
              Import the file&apos;s value as a new parameter
            </label>
            {choice?.action === 'rename' && (
              <input
                value={choice.to}
                onChange={(e) => set(c.name, { action: 'rename', to: e.target.value })}
                aria-label={`New name for ${c.name}`}
                className="ml-6 w-64 px-2 py-1 text-sm font-mono bg-background border border-input rounded-md"
              />
            )}
          </fieldset>
        )
      })}
    </div>
  )
}
