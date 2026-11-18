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
`std`/`standard`, `vis`/`vision`, `des`/`design`, `rsk`/`risk`, `chg`/`change`,
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

## Section body and formatting

Everything under a section heading, up to the next section heading, is the body of
that artefact. The body is written in Markdown and is imported as the artefact's rich
content, so the artefact page shows it formatted and the editor opens it for editing.
The following is kept:

| Markdown | Shown as |
|---|---|
| `### Heading` (levels 1 to 6) | heading |
| a blank line between lines of text | new paragraph |
| `**bold**`, `*italic*`, `~~struck~~` | bold, italic, struck text |
| `` `code` `` | inline code |
| a fenced block between ```` ``` ```` lines, with an optional language | code block |
| `[text](https://example.com)` | link |
| `- item` or `* item` | bullet list, nested by indenting |
| `1. item` | numbered list, nested by indenting |
| a table with a `\| --- \|` header line, with `:--`, `:-:` or `--:` alignment | table with a header row |
| `> text` | quote |
| `---` on its own line | horizontal rule |
| `{{NAME}}` | the parameter, shown with its value |

A line break inside a paragraph joins the lines; end a line with two spaces to keep
the break. An image `![text](https://example.com/image.png)` is imported as a link to
the image. Raw HTML is imported as text.

Inside a section opened by a type tag, a heading without a tag that is deeper than
the section heading belongs to the body: under `## [SPEC] Sign-in`, a `### Refusals`
heading is a heading of that specification. A heading at the same level or above
starts the next section. Lines inside a fenced code block are never read as headings
or test case rows.

The body is also stored as the artefact's description text. A defect has no rich
content and shows its body as that text.

```markdown
## [SPEC] Sign-in
Users sign in with an **email** and a password.

### Refusals
- A wrong password is refused.
- A locked account is refused.

| Event | Effect |
| --- | --- |
| No request for {{IDLE_MINUTES}} minutes | The session ends |
```

## Parameters and variables

Write a parameter inside the sentence where it is used, wrapped as
`{{parameter: NAME, value: VALUE}}`. On import Bloom creates a parameter and replaces
the wrapped form with `{{NAME}}`. Write `{{variable: NAME, value: VALUE}}` the same
way to create a variable instead. Both forms read `{{NAME}}` once imported, and the
rules below on names apply to both.

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

A `{{NAME}}` without `parameter:` or `variable:` and `value:` is a reference to an
existing parameter or variable and is kept as it is. Every `{{NAME}}` of the body is
shown as the parameter, with its value, the same as one written in the editor. Inside
inline code or a code block it stays plain text.

Each parameter and variable has a **name** and a **value**. On import the backend
checks each name. A name that already exists in the project, as a parameter or a variable, is
never overwritten: the import stops before creating anything and lists each such name
with the project's value and the file's value. For each one, choose to keep the
project's value (the imported text then refers to it) or to import the file's value
under a new name (the new parameter or variable is created with the kind the file
declares, and every `{{NAME}}` of the imported text refers to the new name). The
import runs once every name has a choice.

## Test cases

In a `[TC]` section, each `- Pre-Condition:`, `- Step:` or `- Loop:` line becomes a
row of the test case's steps table. Text after `=>` is the row's expected result.
Indent a row by two spaces to nest it under the loop above it. Every other line of
the section is the test case description, imported with its formatting as described
in Section body and formatting. Keep each step to one action with one expected
result.

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

## Writing a document with an AI assistant

An AI assistant can turn existing notes, a specification or a test plan into this
format. Give it this file and ask it to follow it exactly:

- one `##` section per artefact, with the type tag in the heading (`## [REQ]`,
  `## [TC]`, ...);
- every value that can change written as `{{parameter: NAME, value: VALUE}}` (or
  `{{variable: NAME, value: VALUE}}` for a variable) inside the sentence where it is
  used, with the same NAME wherever it is the same value;
- in a `[TC]` section, one action per `- Step:` line and its expected result after
  `=>`, preconditions as `- Pre-Condition:`, repetitions as `- Loop:` with the looped
  steps indented by two spaces;
- nothing invented: a value or an expected result that is not in the source is left
  out or marked for review, not guessed.

Read the result before importing it. The import shows every parameter whose name
already exists in the project and asks what to do with it, and each imported artefact
starts unlinked, so the links are checked by a person.

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
| `vis` / `vision` | Vision (VIS) | title + body; filed in the document registry |
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
