# Markdown import format

Bloom can import a Markdown document and classify its content into artefacts
(requirements, designs, test concepts, and so on). This file defines the format
each template accepts.

## Classifying content

An artefact type is chosen, in priority order, by:

1. a **heading tag** on the section: `## [REQ] Title`, `## [DES] Title`
2. **frontmatter** at the top of the file: `type: requirement`
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

## Parameters

Write a parameter inside the sentence where it is used, wrapped as
`{{parameter: NAME, value: VALUE}}`. On import Bloom creates the parameter and
replaces the wrapped form with `{{NAME}}`.

```markdown
## [REQ] Boot time
The system shall boot within {{parameter: BOOT_BUDGET_MS, value: 500}} ms of power-on.
```

imports as a requirement whose text reads:

```markdown
The system shall boot within {{BOOT_BUDGET_MS}} ms of power-on.
```

The app shows the parameter value in the text, so write the sentence around it:
`repeat {{parameter: BOOT_CYCLES, value: 3}} times` reads "repeat 3 times".

A `{{NAME}}` without `parameter:` and `value:` is a reference to an existing
parameter and is kept as it is.

Each parameter has a **name** and a **value**. On import the backend checks each
name. A name that already exists in the project, as a parameter or a variable, is
never overwritten: the import stops before creating anything and lists each such name
with the project's value and the file's value. For each one, choose to keep the
project's value (the imported text then refers to it) or to import the file's value
under a new name (the new parameter is created and every `{{NAME}}` of the imported
text refers to the new name). The import runs once every name has a choice.

## Test cases

In a `[TC]` section, each `- Pre-Condition:`, `- Step:` or `- Loop:` line becomes a
row of the test case's steps table. Text after `=>` is the row's expected result.
Indent a row by two spaces to nest it under the loop above it. Every other line of
the section is the test case description. Keep each step to one action with one
expected result.

```markdown
## [TC] Boot within budget
Measures the cold boot time of the device under test.

- Pre-Condition: device under test powered off through the relay
- Loop: repeat {{parameter: BOOT_CYCLES, value: 3}} times
  - Step: switch the relay on => relay reports closed
  - Step: read the serial port until the boot banner => boot banner received
  - Step: measure the time from relay on to boot banner => within {{parameter: BOOT_BUDGET_MS, value: 500}} ms +- {{parameter: BOOT_TOLERANCE_MS, value: 50}} ms
```

The CSV and XML test-case exports write the steps column in this same row form, one row per line, so an exported file imports back without losing rows.

## Links

When an imported document classifies as a specification, test concept, design or
requirement, the uploader is prompted to check the necessity of the relevant
links, both in the text and in the relationship tree. A document that ends up
unlinked always prompts the user to link it, via a notification.

## Per-template acceptance

Each artefact template accepts the same document shape; the type token or default
decides which template a section is filed under.

| Type token | Template | Notes |
|---|---|---|
| `req` / `requirement` | Requirement | title + body |
| `spec` / `std` | Document (SPEC/STD) | title + body; filed in the document registry |
| `des` / `design` | Design | title + body |
| `rsk` / `risk` | Risk | title + body |
| `cpt` / `concept` / `test-concept` | Test Concept | title becomes the concept name |
| `tc` / `test-case` | Test Case | title, description and steps rows (see Test cases) |
| `chg` / `change` | Change Request | title + body |
| `def` / `defect` | Defect | title + body |

On import every created artefact starts **unlinked** and raises a notification asking
you to add relevant links. For **requirement, design, test-concept and
spec/standard** documents the notification specifically asks you to check the
necessity of links in the text and in the relationship tree.
