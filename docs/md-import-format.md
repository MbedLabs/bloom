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

Each section is one artefact and answers one question. A specification frames one
behaviour area and mentions its requirements; it does not restate them. A requirement
holds one rule: its title is the rule, and its text gives the purpose, the rule and
its boundary. A design says how the rule is built.

```markdown
---
type: requirement
---

## [REQ] The device is ready within a fixed time of power-on
An operator waits for the device before every measurement. The device shall reach its
ready state within {{parameter: BOOT_BUDGET_MS, value: 500}} ms of power-on. A start
from standby is not covered by this rule.

## [DES] Boot sequence
The boot loader skips the memory test on a warm start and starts the measurement task
before the network task.
```

## A specification and its requirements

An import document never holds a document ID: Bloom assigns every ID on import. An
artefact is mentioned by its title instead, written as `[[Title]]`.

Once every section is created, each `[[Title]]` is resolved:

1. to the section of the same document whose heading has that title (case and
   spacing do not matter);
2. when the document has no such section, to the artefact of the project, visible to
   you, whose title is exactly that title.

The reference becomes a mention of that artefact, the same as one picked in the
editor after typing `#`, and the section is linked to it with a `references` link.
A requirement and a defect are plain text: in their text the reference reads as the
document ID Bloom gave the mentioned artefact, with a `#` in front, the form the
requirement editor writes. In a requirement it still creates the link.

A specification frames its area: what it covers, why, and where it ends. Its
sub-headings group the requirements by mentioning them. Each rule is its own
`## [REQ]` section whose title is the rule.

```markdown
## [SPEC] Sign-in
Sign-in is how a person proves who they are before they see any project data. This area covers signing in with an email and a password and ending a session that is no longer used. Signing in through an identity provider is not part of it.

### Credentials
How the product treats the email and the password a person enters.

- [[A wrong password is refused without saying which part was wrong]]

### Sessions
How long a signed-in session lasts.

- [[A session ends after a period without requests]]

## [REQ] A wrong password is refused without saying which part was wrong
A refusal that names the wrong part tells an attacker which emails exist. The product shall refuse a sign-in whose password does not match the account, with the same answer whether the email or the password was wrong. A refused sign-in does not lock the account.

## [REQ] A session ends after a period without requests
A session left open on a shared machine is a way into the project. The product shall end a session that has received no request for {{parameter: IDLE_MINUTES, value: 30}} minutes. A session that is in use is never ended by this rule.
```

The specification above is imported with both requirements mentioned under their
headings and linked to it. A later document can mention one of these requirements
the same way, by its title: `[[A session ends after a period without requests]]`.

A `[[Title]]` that matches nothing, more than one section or more than one artefact
of the project stays text and is listed in the import result's errors, and so is one
whose section was not imported. A reference inside inline code or a code block stays
text.

Requirements, designs, risks, change requests, test concepts, specifications,
standards and visions hold mentions. A test case and a defect do not: in their text a
resolved `[[Title]]` reads as the document ID, and the import result says so.

## Section body and formatting

Everything under a section heading, up to the next section heading, is the body of
that artefact. What the body becomes depends on the type:

| Type | The body becomes |
|---|---|
| specification, standard, vision, design, risk, change request, test concept | rich content, shown formatted and opened in the editor |
| test case | the step rows (see Test cases), and the other text as rich content |
| requirement | the description, as plain text |
| defect | the description, as plain text |

For the types with rich content the description is the one-line brief description
under the title. The import leaves it empty; write it in Bloom when needed.

A requirement holds one rule in plain prose, so write its body without Markdown
formatting. In rich content the following is kept:

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
| `[[Title]]` | the mentioned artefact (see above) |

A line break inside a paragraph joins the lines; end a line with two spaces to keep
the break. An image `![text](https://example.com/image.png)` is imported as a link to
the image. Raw HTML is imported as text.

Inside a section opened by a type tag, a heading without a tag that is deeper than
the section heading belongs to the body: under `## [SPEC] Sign-in`, a `### Sessions`
heading is a heading of that specification. A heading at the same level or above
starts the next section. Lines inside a fenced code block are never read as headings
or test case rows.

The editor numbers headings from level 1, so the shallowest heading of a body becomes
a level 1 heading and deeper headings keep their distance to it: under
`## [SPEC] Sign-in`, `### Sessions` becomes heading 1 and a `####` below it heading
1.1.

A design is where technical detail such as tables of values and code belongs:

````markdown
## [DES] Session expiry
Each session row stores the time of its **last request**. A background task ends the
sessions that are idle for longer than {{IDLE_MINUTES}} minutes; see
[the scheduler notes](https://example.com/scheduler) for its timing.

### Session states

| State | Set when | Next state |
| --- | --- | --- |
| `active` | a request arrives | `expired` |
| `expired` | the idle limit passes | none |

### Expiry query

```sql
UPDATE sessions SET state = 'expired'
WHERE state = 'active' AND last_request_at < :cutoff;
```

1. The task computes the cutoff from the idle limit.
2. It runs the query and records how many sessions it ended.
````

## Parameters and variables

Write a parameter inside the sentence where it is used, wrapped as
`{{parameter: NAME, value: VALUE}}`. On import Bloom creates a parameter and replaces
the wrapped form with `{{NAME}}`. Write `{{variable: NAME, value: VALUE}}` the same
way to create a variable instead. Both forms read `{{NAME}}` once imported, and the
rules below on names apply to both.

```markdown
## [REQ] The device is ready within a fixed time of power-on
An operator waits for the device before every measurement. The device shall reach its
ready state within {{parameter: BOOT_BUDGET_MS, value: 500}} ms of power-on. A start
from standby is not covered by this rule.
```

imports as a requirement whose text reads:

```markdown
An operator waits for the device before every measurement. The device shall reach its
ready state within {{BOOT_BUDGET_MS}} ms of power-on. A start from standby is not
covered by this rule.
```

Rich content shows the parameter value in the text, so write the sentence around it:
`repeat {{parameter: BOOT_CYCLES, value: 3}} times` reads "repeat 3 times".

A `{{NAME}}` without `parameter:` or `variable:` and `value:` is a reference to an
existing parameter or variable and is kept as it is. In rich content every `{{NAME}}`
becomes the parameter, shown with its value, the same as one written in the editor;
inside inline code or a code block it stays plain text. In a requirement or a defect
it stays `{{NAME}}`.

Each parameter and variable has a **name** and a **value**. On import the backend
checks each name. A name that already exists in the project, as a parameter or a variable, is
never overwritten: the import stops before creating anything and lists each such name
with the project's value and the file's value. For each one, choose to keep the
project's value (the imported text then refers to it) or to import the file's value
under a new name (the new parameter or variable is created with the kind the file
declares, and every `{{NAME}}` of the imported text refers to the new name). The
import runs once every name has a choice.

## Test cases

A test case is one scenario. In a `[TC]` section, each `- Pre-Condition:`, `- Step:`
or `- Loop:` line becomes a row of the test case's steps table. Text after `=>` is the
row's expected result. Indent a row by two spaces to nest it under the loop above it.
Every other line of the section becomes the test case's rich content, with its
formatting as described in Section body and formatting. Keep each step to one action
with one expected result.

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
- a `[SPEC]` section that frames its area (what it covers, why, where it ends) and
  mentions its requirements as `[[Requirement title]]` under its sub-headings, never
  restating them;
- no document ID anywhere: every artefact, in the document or in the project, is
  mentioned by its title as `[[Title]]`;
- each rule as its own `[REQ]` section whose title is the rule, with its purpose, the
  rule and its boundary in the text;
- every value that can change written as `{{parameter: NAME, value: VALUE}}` (or
  `{{variable: NAME, value: VALUE}}` for a variable) inside the sentence where it is
  used, with the same NAME wherever it is the same value;
- in a `[TC]` section, one action per `- Step:` line and its expected result after
  `=>`, preconditions as `- Pre-Condition:`, repetitions as `- Loop:` with the looped
  steps indented by two spaces;
- nothing invented: a value or an expected result that is not in the source is left
  out or marked for review, not guessed.

Read the result before importing it. The import shows every parameter whose name
already exists in the project and asks what to do with it, and lists every section
reference it could not resolve.

## Links

Each mention the import writes links the mentioning artefact to the mentioned one
with a `references` link, as the editor does on save. An imported artefact that ends
the import without any link raises a notification asking you to add relevant links.
For a specification, test concept, design or requirement the notification asks you to
check the necessity of links in the text and in the relationship tree.

## Per-template acceptance

Each artefact template accepts the same document shape; the type token or default
decides which template a section is filed under.

| Type token | Template | Notes |
|---|---|---|
| `req` / `requirement` | Requirement | title + body; plain text |
| `spec` / `std` | Document (SPEC/STD) | title + body; filed in the document registry |
| `vis` / `vision` | Vision (VIS) | title + body; filed in the document registry |
| `des` / `design` | Design | title + body |
| `rsk` / `risk` | Risk | title + body |
| `cpt` / `concept` / `test-concept` | Test Concept | title becomes the concept name |
| `tc` / `test-case` | Test Case | title, rich content and steps rows (see Test cases) |
| `chg` / `change` | Change Request | title + body |
| `def` / `defect` | Defect | title + body; plain text, no mentions |
