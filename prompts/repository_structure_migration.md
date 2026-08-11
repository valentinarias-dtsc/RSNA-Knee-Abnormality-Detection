# Task: reorganize completed project stages under the current repository structure and naming conventions

Work on the current repository:

`valentinarias-dtsc/RSNA-Knee-Abnormality-Detection`

## Primary objective

Reorganize the work already completed in previous project stages so that the repository consistently follows the current structural, documentation, artifact, figure, and naming conventions.

This is a **repository migration and documentation normalization task**.

Do not redesign previous analyses.

Do not change historical findings merely to make them look cleaner.

Do not retrain models.

Do not implement the next MRI preprocessing or baseline stage.

Do not rerun expensive dataset-wide operations unless strictly necessary to validate that a moved path or entry point still works.

The goal is:

```text
existing work
    ↓
inventory and stage ownership
    ↓
controlled moves / renames
    ↓
updated references
    ↓
consistent stage structure
    ↓
validation that nothing became orphaned or broken
```

---

# 1. Read the project context before making changes

First inspect the entire current repository and understand its actual state.

Read the consolidated project context and all existing reports relevant to completed stages.

Pay particular attention to the conventions already established for:

- stage reports;
- implementation reports;
- reusable Python modules;
- scripts / orchestrators;
- artifacts;
- figures;
- notebooks;
- tests;
- configuration;
- reproducibility;
- stage-to-stage narrative continuity.

Do not assume that historical file names still match the current conventions.

Locate files by their content and role.

---

# 2. Current project philosophy

The repository now follows this conceptual separation:

```text
CODE
    ↓
reproducible behavior

ARTIFACTS
    ↓
structured machine-readable outputs

FIGURES
    ↓
visual representations of results

STAGE REPORTS
    ↓
findings + interpretation + decisions + conclusions

IMPLEMENTATION REPORTS
    ↓
code architecture + files + execution + tests + outputs

NOTEBOOKS
    ↓
optional exploration / diagnostics only
```

No notebook should contain logic required to reproduce an official project result.

Official executable logic should live in Python modules, configuration, scripts, or orchestrators.

---

# 3. New naming convention — mandatory

From this migration onward, all project-owned file and directory names that belong to project stages must follow:

```text
<stage_number>_<descriptive_name>
```

using:

- two-digit stage number;
- underscore separator;
- `snake_case`;
- English naming;
- no spaces;
- no ` - `;
- no Spanish names;
- no title case in paths.

Examples:

```text
01_dataset_characterization.md
02_supervision_strategy_review.md
03_report_label_generation.md
03_report_label_generation_implementation.md

artifacts/03_report_label_generation/
figures/03_report_label_generation/
```

Do **not** use:

```text
03 - report label generation.md
03 report label generation.md
03-report-label-generation.md
03_generación_labels.md
```

---

# 4. Language convention

Apply English to:

- file names;
- directory names;
- Markdown headings and titles;
- code;
- Python identifiers;
- configuration keys;
- script names;
- test names;
- artifact field names created by project code.

The **body narrative of reports does not need to be translated wholesale** as part of this migration.

Preserve the existing report language where appropriate unless a small edit is necessary for coherence.

However, all Markdown headings should be normalized to English.

Do not turn this task into a full translation project.

The purpose is structural consistency, not rewriting every paragraph.

---

# 5. Stage numbering

Use the established logical project sequence, not file creation dates.

The currently established sequence is conceptually:

```text
00_competition_context
        ↓
01_dataset_characterization
        ↓
02_supervision_strategy_review
        ↓
03_report_label_generation
        ↓
04_mri_preprocessing
        ↓
05_first_visual_baseline
        ↓
...
```

Stages `04` and later are future work and must **not** be implemented here.

For stages `00–03`, inspect the repository and determine which stages have actual persisted work.

Do not fabricate analyses or implementation outputs simply to fill every stage number.

A stage may legitimately have:

- only a stage report;
- a stage report + implementation report;
- artifacts and figures;
- executable code;
- no implementation report if no meaningful code implementation occurred.

Stage numbering expresses logical dependency.

---

# 6. Expected historical mapping

Use this only as an initial hypothesis and verify it against the repository.

## Stage 00 — Competition context

Purpose:

```text
competition scope
external sources
problem formulation
project conventions
```

If there is sufficient persisted historical material to justify a dedicated stage report, consolidate or place it under:

```text
reports/stages/00_competition_context.md
```

Do not invent findings.

If the material is better treated as global project documentation rather than a formal analytical stage, preserve that distinction and document the decision.

Do not create an implementation report for stage 00 unless there was actual stage-specific implementation.

---

## Stage 01 — Dataset characterization

Historical material currently includes the initial dataset characterization and its generated figures.

Target stage report naming:

```text
reports/stages/01_dataset_characterization.md
```

Associated figures should live under:

```text
figures/01_dataset_characterization/
```

If the characterization is backed by executable code such as a dataset characterization script, assess whether it justifies an implementation report:

```text
reports/implementation/01_dataset_characterization_implementation.md
```

If created, it must document actual existing code only.

Do not invent architectural complexity that did not exist.

---

## Stage 02 — Supervision strategy review

The review of Kaggle notebooks established the role of reports in weak supervision.

Target report:

```text
reports/stages/02_supervision_strategy_review.md
```

This stage is primarily analytical/research-oriented.

Unless it contains meaningful reusable implementation, it likely does **not** require a separate implementation report.

Do not create one merely for symmetry.

---

## Stage 03 — Report label generation

Stage 03 already has:

- Python implementation;
- executable pipeline;
- tests;
- artifacts;
- figures;
- stage report;
- implementation report.

Preserve all substantive content and results.

Normalize naming to:

```text
reports/stages/03_report_label_generation.md
reports/implementation/03_report_label_generation_implementation.md

artifacts/03_report_label_generation/
figures/03_report_label_generation/
```

The current stage 03 artifact and figure directory naming is already close to the new convention and should remain stable unless an actual inconsistency is found.

---

# 7. Inventory before migration — mandatory

Before moving anything, build an explicit internal inventory of existing project-owned files associated with stages `00–03`.

Inspect at least:

```text
reports/
reports/stages/
reports/implementation/
reports/figures/
figures/
artifacts/
scripts/
src/
tests/
config/
notebooks/
prompts/
README.md
.gitignore
```

For every relevant file determine:

```text
current_path
stage_owner
role
target_path
references_to_update
```

Roles may include:

```text
stage_report
implementation_report
artifact
figure
script
module
test
config
notebook
historical_reference
```

Do not begin moves until this mapping is coherent.

---

# 8. Preserve stage ownership

Every generated artifact and figure must have one clear owning stage.

For example:

```text
figures/01_dataset_characterization/
```

must contain only figures produced by stage 01.

```text
artifacts/03_report_label_generation/
```

must contain only artifacts produced by stage 03.

Do not create generic dumping grounds such as:

```text
reports/figures/
artifacts/misc/
figures/general/
```

when a stage owner can be determined.

If a file genuinely belongs to global project documentation rather than a stage, treat it explicitly as global instead of forcing stage ownership.

---

# 9. No orphan artifacts or figures

This is a mandatory repository invariant.

For every artifact and figure produced by a completed stage:

```text
file exists
    ↓
owning stage is identifiable
    ↓
respective stage report references it
    ↓
purpose and interpretation are documented
```

If an existing figure or artifact is not referenced by its stage report:

1. determine whether it is genuinely useful;
2. if useful, add it to the appropriate report with context and interpretation;
3. if obsolete/redundant and safely reproducible, remove it;
4. do not silently leave it orphaned.

Do not delete unique historical results merely because they are not currently linked.

---

# 10. Stage report standard

Every persisted stage report should be self-contained and understandable without opening code or notebooks.

The body should preserve the established professional, technical, precise tone oriented toward data science teammates.

Normalize headings to English.

Where applicable, stage reports should contain headings equivalent to:

```text
# <Stage title>

## Executive Summary
## Previous Stage Connection
## Objective and Questions
## Data / Inputs
## Methodology
## Findings
## Interpretation
## Decisions
## Artifacts and Figures
## Limitations
## Conclusions
## Next Stage Connection
```

Do not mechanically add empty sections.

Adapt them to the actual content of the stage.

The report must clearly distinguish:

```text
observed finding
vs
interpretation
vs
engineering / methodological decision
```

Preserve historical findings.

Do not recalculate or alter metrics merely to normalize presentation.

---

# 11. Implementation report standard

Implementation reports exist only when a stage contains meaningful project code.

Normalize headings to English.

They should explain:

```text
what was implemented
why
code architecture
modules and responsibilities
entry points
configuration
tests
artifacts
figures
reproduction commands
technical limitations
contract with the next stage
```

Typical headings:

```text
# <Stage title> — Implementation

## Technical Summary
## Stage Context
## Architecture
## Files Created or Modified
## Modules and Responsibilities
## Entry Points
## Configuration
## Tests
## Dependencies
## Generated Artifacts
## Generated Figures
## Reproduction
## Technical Limitations
## Interface With the Next Stage
```

Do not duplicate the full statistical narrative from the stage report.

---

# 12. Figures migration

Move historical figures out of legacy locations such as:

```text
reports/figures/
```

when they have a clear stage owner.

For dataset characterization, the expected destination is conceptually:

```text
figures/01_dataset_characterization/
```

For report label generation:

```text
figures/03_report_label_generation/
```

Preserve image contents.

Update all Markdown references.

Update code paths if scripts generate those figures.

After migration, legacy figure directories should not remain merely as aliases unless required for backward compatibility.

Prefer one canonical path.

---

# 13. Artifacts migration

Organize machine-readable outputs by stage.

Use:

```text
artifacts/<stage_number>_<stage_name>/
```

Examples:

```text
artifacts/03_report_label_generation/
```

For previous stages, only create an artifact directory when actual machine-readable artifacts exist or should legitimately be persisted.

Do not manufacture CSV/JSON files merely to satisfy directory symmetry.

If stage 01 only produced a Markdown report and figures, that is acceptable.

---

# 14. Code naming

Project-owned code should remain English and snake_case.

Inspect:

```text
src/
scripts/
tests/
config/
```

Do not rename stable Python modules purely for aesthetics if they already conform to English snake_case and references are widespread.

Rename only when necessary to satisfy the current convention or to remove obsolete historical naming.

Any rename must update:

- imports;
- scripts;
- tests;
- documentation;
- report references;
- config references.

Do not break public internal APIs without reason.

---

# 15. Notebook treatment

Notebooks are not official stage execution entry points.

Existing useful notebooks may remain for:

```text
exploration
diagnostics
error_analysis
inspection
```

If their names are project-owned and part of a stage sequence, normalize them to:

```text
<stage_number>_<descriptive_name>.ipynb
```

using English snake_case.

If a notebook is only an exploratory historical artifact and no longer provides value, do not automatically delete it.

Classify it first.

Do not modify notebook logic merely as part of structural cleanup unless required to repair references.

---

# 16. Prompt and private reference material

Do not treat:

```text
private/kaggle_notebooks/
```

or similar third-party reference material as official stage outputs.

Do not rename external notebooks simply to enforce the project's naming convention if doing so would obscure their provenance.

The new naming convention applies to **project-owned outputs and code**.

Preserve third-party source identity where useful.

---

# 17. Update all references

After moves and renames, search the entire repository for stale paths.

Update references in:

- Markdown links;
- image links;
- README;
- scripts;
- Python constants;
- tests;
- config;
- notebooks when practical;
- `.gitignore`;
- reproduction commands;
- generated metadata where paths are intentionally recorded.

Search specifically for legacy names such as:

```text
dataset_initial_characterization.md
kaggle_notebooks_supervision_strategy_review.md
03 - report label generation.md
03 - report label generation implementation.md
reports/figures/
reports/implementation/figures/
artifacts/labels/
```

but do not assume this list is exhaustive.

Perform a repository-wide reference audit.

---

# 18. README update

Update `README.md` so a teammate can immediately understand the stage structure.

Keep it concise.

It should point to the canonical stage reports and establish the naming convention, for example:

```text
00_competition_context
01_dataset_characterization
02_supervision_strategy_review
03_report_label_generation
04_mri_preprocessing          # next
05_first_visual_baseline      # future
```

Do not present future stages as completed.

Clearly distinguish:

```text
completed
current / next
future
```

The README should link to canonical reports rather than duplicate their content.

---

# 19. Do not rewrite historical evidence

The migration may improve:

- structure;
- headings;
- naming;
- links;
- stage transitions;
- artifact inventory;
- implementation documentation.

It must not silently change:

- dataset counts;
- metrics;
- weak-label performance;
- reported findings;
- methodological conclusions;
- historical limitations.

If an old report contains an actual factual inconsistency discovered during migration:

1. do not silently correct it;
2. document the inconsistency;
3. make the smallest justified correction;
4. preserve traceability.

This task is primarily structural.

---

# 20. Avoid unnecessary recomputation

Do not rescan ~500 GiB of DICOM data merely to migrate paths.

Do not rerun dataset characterization unless required to validate a path-dependent execution contract.

Do not regenerate stage 03 weak labels unless required to prove the pipeline still writes to the new canonical paths.

Prefer:

```text
existing reproducible output
→ move / rename
→ path updates
→ lightweight validation
```

over:

```text
delete
→ recompute everything
```

---

# 21. Generated report links must remain valid

For every stage report:

- verify embedded figures resolve;
- verify relative links to artifacts resolve;
- verify references to implementation reports resolve;
- verify previous/next stage links resolve where those reports exist.

A stage narrative should allow:

```text
previous_stage
    ↓
current_stage
    ↓
next_stage
```

to be navigated cleanly.

For stage 03, the next stage may be described as planned:

```text
04_mri_preprocessing
```

without creating a fake completed report for it.

---

# 22. Recommended canonical structure after migration

Use the actual repository as the source of truth, but aim conceptually for:

```text
reports/
├── stages/
│   ├── 00_competition_context.md            # only if justified
│   ├── 01_dataset_characterization.md
│   ├── 02_supervision_strategy_review.md
│   └── 03_report_label_generation.md
│
└── implementation/
    ├── 01_dataset_characterization_implementation.md   # if justified
    └── 03_report_label_generation_implementation.md

artifacts/
└── 03_report_label_generation/
    └── ...

figures/
├── 01_dataset_characterization/
│   └── ...
└── 03_report_label_generation/
    └── ...

src/
└── ...

scripts/
└── ...

tests/
└── ...
```

Do not create empty directories for absent outputs.

Do not force an implementation report for an analytical-only stage.

---

# 23. Naming examples after the new convention

Correct:

```text
01_dataset_characterization.md
01_dataset_characterization_implementation.md
02_supervision_strategy_review.md
03_report_label_generation.md
03_report_label_generation_implementation.md

figures/01_dataset_characterization/
figures/03_report_label_generation/

artifacts/03_report_label_generation/

scripts/generate_report_labels.py
src/report_labels/
tests/test_report_labels.py
```

Incorrect:

```text
01 - dataset characterization.md
01 Dataset Characterization.md
01-dataset-characterization.md
01_caracterizacion_dataset.md
Report Label Generation.md
reportes/
figuras/
```

---

# 24. Validation after migration

After all changes:

## Filesystem checks

Verify:

- no duplicated canonical reports;
- no obsolete copies of moved reports;
- no orphan stage figures;
- no orphan stage artifacts;
- no empty legacy directories unless intentionally retained;
- no project-owned stage file violating naming conventions.

## Reference checks

Verify:

- Markdown image paths;
- Markdown document links;
- README links;
- code output paths;
- config paths;
- imports;
- tests.

## Execution checks

Run the relevant lightweight tests.

For stage 03, verify the existing test suite still passes.

If possible without expensive recomputation, validate the stage 03 orchestrator in a non-destructive way or ensure its output paths now target the canonical directories.

For stage 01, do not execute a full dataset scan merely for validation.

## Git diff review

Review the final diff and distinguish:

```text
move / rename
content normalization
reference repair
actual behavioral change
```

There should be no unintended behavioral change.

---

# 25. Migration report

Create one dedicated migration report documenting this structural change.

This report is **repository-level documentation**, not a new analytical stage.

Name it in English snake_case without assigning a fake project stage number unless the repository already has a convention for repository-maintenance documents.

Place it in an appropriate documentation/report location determined from the repository.

It should include:

```text
## Summary
## Motivation
## Naming Convention
## Stage Mapping
## Files Moved or Renamed
## Legacy Paths Removed
## References Updated
## Validation Performed
## Remaining Exceptions
## Canonical Structure After Migration
```

The report body may remain in the project's established narrative language, but all headings must be English.

Explicitly document any intentionally retained exception.

---

# 26. Migration table — mandatory

Include a clear old → new path mapping in the migration report.

For example:

```text
reports/dataset_initial_characterization.md
→
reports/stages/01_dataset_characterization.md
```

and:

```text
reports/stages/03 - report label generation.md
→
reports/stages/03_report_label_generation.md
```

Do this for every moved or renamed relevant file/directory.

This table is necessary for team catch-up and historical traceability.

---

# 27. Important constraints

Do not:

- implement stage 04;
- build an MRI baseline;
- change weak-label methodology;
- tune extraction rules;
- change gold-label handling;
- recalculate metrics merely for formatting;
- delete useful historical evidence;
- rename third-party notebooks unnecessarily;
- create empty symmetrical folders;
- create implementation reports for stages with no implementation;
- translate entire reports unless required;
- introduce unrelated dependencies;
- alter competition data;
- overwrite raw data.

---

# 28. Acceptance criteria

The migration is complete only if:

1. project-owned stage naming follows `<NN>_<english_snake_case>`;
2. stage reports are under a canonical stage-report directory;
3. implementation reports are separate from analytical stage reports;
4. Markdown headings/titles are in English;
5. project-owned code naming remains English snake_case;
6. stage 01 historical figures have a clear canonical owner/path;
7. stage 03 artifacts and figures have a clear canonical owner/path;
8. no figure is orphaned;
9. no artifact is orphaned;
10. every output is documented by its owning stage;
11. legacy duplicate reports have been removed after safe migration;
12. all internal links and figure references have been updated;
13. README points to canonical stage documentation;
14. existing executable behavior remains unchanged;
15. existing tests pass;
16. no expensive unnecessary recomputation was performed;
17. a migration report records old → new paths and exceptions;
18. stage numbering reflects logical project dependency;
19. stages `04+` remain unimplemented;
20. the repository is ready for the next logical stage: `04_mri_preprocessing`.

---

# 29. Final expected result

The repository should communicate its history structurally:

```text
00_competition_context
        ↓
01_dataset_characterization
        ↓
02_supervision_strategy_review
        ↓
03_report_label_generation
        ↓
04_mri_preprocessing
```

with the first completed stages represented consistently through:

```text
stage report
+
implementation report when applicable
+
artifacts when applicable
+
figures when applicable
+
reproducible code when applicable
```

and with all project-owned naming following:

```text
stage_number
+
english
+
snake_case
```

The migration should make the repository easier to inspect, reproduce, review, and extend without changing the substance of the work already completed.