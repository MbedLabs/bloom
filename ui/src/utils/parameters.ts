import type { MarkdownCollision, MarkdownCollisionAction } from '../api/client'

/** The Parameters & Variables page focused on one key. */
export function parameterKeyHref(base: string, key: string): string {
  return `${base}?key=${encodeURIComponent(key)}`
}

/** Every collision has an action, and every new name is filled in. */
export function collisionsResolved(
  collisions: MarkdownCollision[],
  choices: Record<string, MarkdownCollisionAction>,
): boolean {
  return collisions.every((c) => {
    const choice = choices[c.name]
    return !!choice && (choice.action === 'existing' || choice.to.trim().length > 0)
  })
}
