export function projectDeleteConfirmationPhrase(prefix: string): string {
  const normalized = prefix.trim().toUpperCase()
  return `Delete ${normalized}`
}

export function projectDeleteConfirmationMatches(input: string, expected: string): boolean {
  return input.trim() === expected.trim()
}
