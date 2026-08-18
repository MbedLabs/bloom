"""Does the UI suite actually catch a regression, or only pass?

Coverage says a line ran, not that anything checked what it did. This breaks
the source in ways a real change might - loosening a guard, reading the wrong
field, dropping a reset - and reports which breakages the suite notices. A
SURVIVED entry is a test that is watching nothing.

Run from ui/:  python3 scripts/mutation-check.py
Each mutation is applied on its own, the whole suite is run, and the file is
put back afterwards whether or not the run succeeded.
"""

import pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent

# (label, file, old, new) - each is a plausible regression, not a typo.
MUTANTS = [
 ("Users: let an admin's role be edited",
  "src/pages/Users.tsx",
  "const canEditRole = !isSelf && u.role !== 'admin'",
  "const canEditRole = !isSelf"),

 ("Users: delete without confirming",
  "src/pages/Users.tsx",
  "if (pendingDeleteUserId !== u.id && confirm('Delete this user?')) {",
  "if (pendingDeleteUserId !== u.id) {"),

 ("Projects: loosen the prefix rule to 2-4 letters",
  "src/pages/Projects.tsx",
  "const PROJECT_PREFIX_PATTERN = /^[A-Z]{3}$/",
  "const PROJECT_PREFIX_PATTERN = /^[A-Z]{2,4}$/"),

 ("Projects: send a blank description instead of omitting it",
  "src/pages/Projects.tsx",
  "createMutation.mutate({ name, prefix: normalizedPrefix, description: description || undefined })",
  "createMutation.mutate({ name, prefix: normalizedPrefix, description })"),

 ("Registry: suspect-link filter reads the wrong counter",
  "src/pages/Documents.tsx",
  "result = result.filter((doc) => doc.suspect_links > 0)",
  "result = result.filter((doc) => doc.incoming_links > 0)"),

 ("Registry: created-from range reads updated_at",
  "src/pages/Documents.tsx",
  "result = result.filter((doc) => new Date(doc.created_at).getTime() >= from)",
  "result = result.filter((doc) => new Date(doc.updated_at).getTime() >= from)"),

 ("Registry: page not reset when a filter changes",
  "src/pages/Documents.tsx",
  "useEffect(() => { setPage(0) }, [typeFilters, statusFilters, search, priorityFilter, reviewerFilter, linkFilter, createdFrom, createdTo, updatedFrom, updatedTo, pageSize])",
  "useEffect(() => { setPage(0) }, [pageSize])"),

 ("Defects: send an empty status instead of dropping the key",
  "src/pages/Defects.tsx",
  "...(filterStatus ? { status: filterStatus } : {}),",
  "...{ status: filterStatus },"),

 ("Defects: issue number sent as a string",
  "src/pages/Defects.tsx",
  "external_issue_number: form.external_issue_number ? Number(form.external_issue_number) : null,",
  "external_issue_number: form.external_issue_number || null,"),

 ("Tracker: always send the token, wiping it when blank",
  "src/components/IntegrationSettingsPanel.tsx",
  "if (token) payload.token = token",
  "payload.token = token"),

 ("Tracker: skip the confirmation before removing a tracker",
  "src/components/IntegrationSettingsPanel.tsx",
  "if (hasData && !window.confirm('Remove all external tracker configuration for this project?')) {",
  "if (false) {"),

 ("ProjectEdit: compare the delete phrase case-insensitively",
  "src/lib/projectDelete.ts",
  "return input.trim() === expected.trim()",
  "return input.trim().toLowerCase() === expected.trim().toLowerCase()"),

 ("ProjectEdit: keep doc types when promoting to maintainer",
  "src/pages/ProjectEdit.tsx",
  "        doc_types: role === 'external' ? docTypes : [],",
  "        doc_types: docTypes,"),

 ("Campaigns: allow a campaign scoped from no suite",
  "src/pages/TestCampaigns.tsx",
  "    if (selectedSuiteIds.length === 0) {\n      setCreateError('Select at least one suite before creating a campaign.')\n      return\n    }",
  "    if (false) {\n      setCreateError('Select at least one suite before creating a campaign.')\n      return\n    }"),

 ("Import: keep the selection when the doc type changes",
  "src/pages/ImportWizard.tsx",
  "onClick={() => { setDocType(type); setSelectedIds([]); setStep(3) }}",
  "onClick={() => { setDocType(type); setStep(3) }}"),

 ("Import: offer the target project as its own source",
  "src/pages/ImportWizard.tsx",
  "const availableProjects = projects?.filter((p) => p.id !== projectId) || []",
  "const availableProjects = projects || []"),

 ("MentionList: ArrowUp stops instead of wrapping",
  "src/components/editor/MentionList.tsx",
  "setSelectedIndex((i) => (i + items.length - 1) % items.length)",
  "setSelectedIndex((i) => Math.max(0, i - 1))"),

 ("MentionList: highlight not reset when the list re-filters",
  "src/components/editor/MentionList.tsx",
  "useEffect(() => setSelectedIndex(0), [items])",
  "useEffect(() => {}, [items])"),

 ("Editor: toolbar stops re-rendering on transactions",
  "src/components/editor/DocEditor.tsx",
  "    shouldRerenderOnTransaction: true,",
  "    shouldRerenderOnTransaction: false,"),

 ("Editor: {{ offers parameters only, not variables",
  "src/pages/DocCreate.tsx",
  "                  mentionItems={(projectVariables ?? []).map((variable) => ({\n                    id: variable.id,\n                    label: variable.key,\n                  }))}",
  "                  mentionItems={(projectVariables ?? []).filter((v) => v.kind === 'parameter').map((variable) => ({\n                    id: variable.id,\n                    label: variable.key,\n                  }))}"),

 ("Editor: @ trigger fed the parameter list",
  "src/components/editor/DocEditor.tsx",
  "            items: ({ query }) => userMentionItemsRef.current.filter((item) => {",
  "            items: ({ query }) => mentionItemsRef.current.filter((item) => {"),

 ("One-time token: accept a token from the query string too",
  "src/hooks/useOneTimeToken.ts",
  "return new URLSearchParams((loc.hash || '').replace(/^#/, '')).get('token') || ''",
  "return new URLSearchParams((loc.hash || '').replace(/^#/, '')).get('token') || new URLSearchParams(loc.search || '').get('token') || ''"),

 ("One-time token: leave the token in the URL after reading it",
  "src/hooks/useOneTimeToken.ts",
  "    if (loc && loc.hash) {",
  "    if (false) {"),

 ("Settings: keep the password in the form after a request",
  "src/pages/Settings.tsx",
  "      setNewEmail('')\n      setCurrentPassword('')",
  "      setNewEmail('')"),
]

results = []


def restore_any_leftovers() -> None:
    """Put back anything a previous run was killed in the middle of.

    The per-mutant `finally` cannot help against SIGKILL, and a mutated file
    left in the tree is worse than useless - it is a deliberately broken guard
    that looks like ordinary uncommitted work and can be committed by mistake.
    So the original is written to a sidecar *before* the source is touched, and
    the next run puts it back before doing anything else.
    """
    for backup in sorted(ROOT.glob('**/*.mutation-backup')):
        target = backup.with_suffix('')
        target.write_text(backup.read_text())
        backup.unlink()
        print(f"restored {target.relative_to(ROOT)} from an interrupted run", flush=True)


restore_any_leftovers()

for label, rel, old, new in MUTANTS:
    path = ROOT / rel
    original = path.read_text()
    if old not in original:
        results.append((label, rel, "NOT-APPLIED"))
        print(f"{'NOT-APPLIED':10} {label}", flush=True)
        continue
    backup = path.with_name(path.name + '.mutation-backup')
    backup.write_text(original)
    path.write_text(original.replace(old, new, 1))
    try:
        proc = subprocess.run(
            [str(ROOT / 'node_modules/.bin/vitest'), 'run', '--reporter=dot'],
            cwd=ROOT, capture_output=True, text=True, timeout=900)
        results.append((label, rel, "CAUGHT" if proc.returncode != 0 else "SURVIVED"))
    finally:
        path.write_text(original)
        backup.unlink(missing_ok=True)
    print(f"{results[-1][2]:10} {label}", flush=True)

print()
caught = sum(1 for r in results if r[2] == 'CAUGHT')
total = sum(1 for r in results if r[2] != 'NOT-APPLIED')
print(f"=== {caught}/{total} caught ===")
for label, rel, verdict in results:
    if verdict != 'CAUGHT':
        print(f"  {verdict}: {label}  [{rel}]")
