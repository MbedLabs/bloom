# Markdown import format

Bloom can import a Markdown document and classify its content into artefacts
(requirements, designs, test concepts, and so on). This file defines the format
each template accepts.

## Classifying content

An artefact type is chosen, in priority order, by:

1. a **heading tag** on the section — `## [REQ] Title`, `## [DES] Title`, …
2. **frontmatter** at the top of the file — `type: requirement`
3. the **type specified at import** time (a default applied to unmarked sections)

Recognised type tokens (case-insensitive): `req`/`requirement`, `spec`,
`std`/`standard`, `des`/`design`, `rsk`/`risk`, `chg`/`change`,
`cpt`/`concept`/`test-concept`, `tc`/`test-case`, `def`/`defect`.

```markdown
---
type: requirement
---

## [REQ] The system shall boot in under 500 ms
Body text for this requirement.

## [DES] Boot sequence
Body text for this design.
```

## Parameters section

Parameters are declared as `parameter:`/`value:` pairs; the backend uses them to
fill the document.

```markdown
## Parameters
parameter: BOOT_BUDGET_MS
value: 500
parameter: MAX_TEMP_C
value: 85
```

Each parameter has a **name** and a **value**. On import the backend checks each
name: **if a parameter with that name already exists it alerts and requires an
action — it is never silently overwritten.**

## Links

When an imported document classifies as a specification, test concept, design or
requirement, the uploader is prompted to check the necessity of the relevant
links, both in the text and in the relationship tree. A document that ends up
unlinked always prompts the user to link it, via a notification.
