import { spawnSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { basename, isAbsolute } from 'node:path'
import { fileURLToPath } from 'node:url'

const reviewedAdvisoriesFile = fileURLToPath(new URL('./reviewed-advisories.json', import.meta.url))

/** Prints a message to stderr and ends the process with exit code 1. */
function fail(message) {
  console.error(message)
  process.exit(1)
}

/** Returns true for a JSON object that is neither null nor an array. */
function isPlainObject(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/** Returns the absolute path of the npm CLI script that started this process through `npm run audit`. */
function npmCliPath() {
  const cli = process.env.npm_execpath
  if (!cli || !isAbsolute(cli) || !/^npm-cli\.[cm]?js$/.test(basename(cli)) || !existsSync(cli)) {
    fail('Unable to locate the npm CLI: run this script with `npm run audit` so that npm_execpath names an absolute npm-cli.js.')
  }
  return cli
}

/**
 * Reads reviewed-advisories.json next to this script into a map of package name to advisory URLs.
 * The file maps each package name to an object of `advisory URL: reason the advisory does not apply to Bloom`;
 * an advisory that is not listed there fails the audit.
 */
function loadReviewedAdvisories() {
  let data
  try {
    data = JSON.parse(readFileSync(reviewedAdvisoriesFile, 'utf8'))
  } catch (error) {
    fail(`Unable to read ${reviewedAdvisoriesFile}: ${error.message}`)
  }
  if (!isPlainObject(data)) fail(`${reviewedAdvisoriesFile} must contain a JSON object`)
  const advisories = new Map()
  for (const [name, entries] of Object.entries(data)) {
    const valid = isPlainObject(entries) && Object.entries(entries).every(
      ([url, reason]) => url.startsWith('https://') && typeof reason === 'string' && reason.trim() !== '',
    )
    if (!valid) fail(`${reviewedAdvisoriesFile}: "${name}" must map each advisory URL to the reason it does not apply`)
    advisories.set(name, new Set(Object.keys(entries)))
  }
  return advisories
}

const reviewedAdvisories = loadReviewedAdvisories()

const result = spawnSync(process.execPath, [npmCliPath(), 'audit', '--json'], {
  encoding: 'utf8',
  maxBuffer: 20 * 1024 * 1024,
})

if (result.error) {
  fail(`Unable to run npm audit: ${result.error.message}`)
}

let report
try {
  report = JSON.parse(result.stdout)
} catch {
  console.error(result.stderr || result.stdout || 'npm audit returned invalid JSON')
  process.exit(1)
}

const vulnerabilities = report.vulnerabilities ?? {}
const memo = new Map()

function isReviewed(name, visiting = new Set()) {
  if (memo.has(name)) return memo.get(name)
  if (visiting.has(name)) return false

  const vulnerability = vulnerabilities[name]
  if (!vulnerability?.via?.length) return false

  const nextVisiting = new Set(visiting).add(name)
  const reviewed = vulnerability.via.every((via) => {
    if (typeof via === 'string') return isReviewed(via, nextVisiting)
    return reviewedAdvisories.get(name)?.has(via.url) ?? false
  })

  memo.set(name, reviewed)
  return reviewed
}

const unexpected = Object.keys(vulnerabilities).filter((name) => !isReviewed(name))
if (unexpected.length > 0) {
  const details = Object.fromEntries(unexpected.map((name) => [name, vulnerabilities[name]]))
  console.error('npm audit found unreviewed vulnerabilities:')
  console.error(JSON.stringify(details, null, 2))
  process.exit(1)
}

if (result.status !== 0 && Object.keys(vulnerabilities).length === 0) {
  console.error(result.stderr || 'npm audit failed without a vulnerability report')
  process.exit(1)
}

const reviewed = Object.keys(vulnerabilities)
console.log(
  reviewed.length === 0
    ? 'npm audit found no vulnerabilities.'
    : `npm audit found only reviewed non-applicable advisories (${reviewed.join(', ')}).`,
)
