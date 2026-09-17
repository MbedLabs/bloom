/** The Parameters & Variables page focused on one key. */
export function parameterKeyHref(base: string, key: string): string {
  return `${base}?key=${encodeURIComponent(key)}`
}
