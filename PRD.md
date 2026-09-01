# IKSHA
### Project Intelligence & Static Analysis Engine
### Product Requirements Document — v2.0 (Engineering Baseline, Revised)

**Product:** IKSHA
**Primary Goal:** Production-grade project intelligence and static analysis, with **accurate dead-CSS detection** as the flagship capability
**Initial Languages:** PHP, HTML, CSS, JavaScript
**Primary Platform:** Windows / Linux / macOS
**Interface:** CLI
**Architecture:** Modular static-analysis engine

---

## 0. What IKSHA Actually Does (Read This First)

IKSHA answers one question with rigor: **"Is this CSS actually unused, and how sure are we?"**

Everything else in this document — the project inventory, the dependency graph, the PHP/HTML/JS parsers, the reachability engine — exists **only** to make that judgment trustworthy. IKSHA is not a grep tool. It builds a structured model of the whole project (what files exist, how they reference each other, where every class/ID/selector is used across PHP, HTML, and JS) and only then reasons about whether a piece of CSS is dead.

The product's single most important behavior: **IKSHA must never claim CSS is dead when it actually can't prove that.** A false "this is dead, delete it" is worse than ten missed detections. When evidence is incomplete (dynamic class names, unresolved includes, ambiguous paths), IKSHA says `UNKNOWN` or `POSSIBLY_DEAD` — never `DEFINITELY_DEAD`.

Everything below supports that mission.

---

## 1. Executive Summary

IKSHA is a project intelligence and static-analysis platform designed to understand the structure, relationships, dependencies, usage, reachability, quality, and dead code within web projects — with CSS dead-code detection as the primary, most differentiated capability.

IKSHA must not behave as a collection of independent grep-like scanners. The engine builds a structured representation of the project (the **Project Map**) and uses evidence gathered across languages and files to produce accurate, explainable conclusions.

Core pipeline:

```
DISCOVER → IDENTIFY → PARSE → EXTRACT REFERENCES → BUILD PROJECT MAP
    → INDEX → ANALYZE → CORRELATE EVIDENCE → DETERMINE REACHABILITY
    → DETERMINE USAGE → DETERMINE FINDINGS → CALCULATE CONFIDENCE → REPORT
```

IKSHA's primary differentiator is **evidence-based analysis with explicit uncertainty**, not raw finding count.

---

## 2. Domain Model — Canonical State Enums

*(New section — this is the single source of truth for every status value used anywhere in the engine, CLI, or reports. All other sections reference these definitions rather than redefining their own.)*

### 2.1 Reachability State (file-level — "can this file be reached from an entry point?")

| Value | Meaning |
|---|---|
| `REACHABLE` | A confirmed static path exists from at least one entry point |
| `POTENTIALLY_REACHABLE` | Reachable only through an unresolved dynamic reference |
| `UNREACHABLE` | No static or dynamic path found from any known entry point |
| `UNKNOWN` | Insufficient evidence to determine (e.g. no entry points identified) |

### 2.2 Usage State (selector/class/ID-level — "is this specific thing referenced anywhere?")

| Value | Meaning |
|---|---|
| `DEFINITELY_USED` | High-confidence static reference found in HTML, PHP, or JS |
| `PROBABLY_USED` | Reference found but with reduced confidence (e.g. heuristic entry point, partially dynamic match) |
| `POSSIBLY_USED` | Only weak/dynamic evidence exists (e.g. one branch of a ternary) |
| `STATICALLY_UNUSED` | No static or dynamic evidence of use was found anywhere in the project |
| `UNKNOWN` | Analysis could not be completed (parse error, unsupported syntax) |

> Note: corrected from the v1.0 typo "STATISTICALLY_UNUSED" — this is a *static*-analysis result, not a statistical one.

### 2.3 Dead-Code State (file-level — "should this CSS file be considered for removal?")

Dead-Code State is **derived from, not identical to**, Reachability State + aggregated Usage State across all selectors in the file. It is a separate axis reported at the file level.

| Value | Meaning |
|---|---|
| `NOT_DEAD` | File is reachable and/or has selectors in active use |
| `POSSIBLY_DEAD` | Weak or partial evidence of disuse; dynamic references present |
| `PROBABLY_DEAD` | Strong evidence of disuse; no dynamic references detected |
| `DEFINITELY_DEAD` | File is unreachable AND all selectors are `STATICALLY_UNUSED` AND no dynamic evidence exists anywhere in the project that could plausibly reference it |
| `UNKNOWN` | Insufficient evidence (parse errors, unsupported constructs) |

**Derivation rule (must be implemented exactly, for determinism — see §54):**

```
IF reachability == UNREACHABLE AND all_selectors == STATICALLY_UNUSED AND no_dynamic_evidence:
    DEFINITELY_DEAD
ELIF reachability in (UNREACHABLE, UNKNOWN) AND most_selectors == STATICALLY_UNUSED AND no_dynamic_evidence:
    PROBABLY_DEAD
ELIF any_dynamic_evidence_present OR reachability == POTENTIALLY_REACHABLE:
    POSSIBLY_DEAD
ELIF reachability == REACHABLE OR any_selector in (DEFINITELY_USED, PROBABLY_USED):
    NOT_DEAD
ELSE:
    UNKNOWN
```

### 2.4 Confidence Level (categorical) — with numeric mapping

Confidence is computed internally as a **weighted numeric score (0–100%)** derived from evidence quality, and then **mapped to a categorical band** for display and comparison. The percentage is the source of truth; the category is a derived, user-facing label. Both must always be reported together.

| Band | Range | Typical Source |
|---|---|---|
| `CERTAIN` | 95–100% | Static exact path match, literal string reference |
| `HIGH` | 80–94% | Resolvable constant expression, known static HTML occurrence |
| `MEDIUM` | 50–79% | Heuristic entry point, one branch of a statically-inferable conditional |
| `LOW` | 20–49% | Weak heuristic, indirect inference |
| `UNKNOWN` | 0–19% / not computable | Dynamic variable, unresolved expression |

Exact weighting formula is an implementation detail (Phase 17) but must be documented, versioned, and covered by regression tests, since it directly determines Dead-Code State via §2.3.

### 2.5 Severity Level

*(New — v1.0 defined confidence but never defined severity, despite §46 insisting they're independent axes.)*

| Value | Meaning |
|---|---|
| `CRITICAL` | Likely to break the project (e.g. circular dependency causing infinite recursion in a naive traversal) |
| `HIGH` | Significant impact if wrong (e.g. large dead CSS file, conflicting declarations shipping the wrong style) |
| `MEDIUM` | Moderate impact (e.g. duplicate declaration, unused custom property) |
| `LOW` | Cosmetic or minor (e.g. redundant declaration overridden later in same cascade) |
| `INFO` | Informational only, not actionable (e.g. `!important` usage detected, no judgment implied) |

Severity and confidence remain independent (§46 preserved as-is): a `HIGH` severity finding can have `LOW` confidence, and must be reported as such, never collapsed into one number.

---

## 3. Product Vision

Build a trustworthy developer tool that can answer:

- "What exists in this project?"
- "How are the files connected?"
- "Which files depend on which other files?"
- "Which files are actually reachable?"
- "Where is this CSS class used?"
- "Is this stylesheet really unused?"
- "Is this selector used by HTML, PHP, or JavaScript?"
- "Which CSS rules are duplicated or conflicting?"
- "What code is potentially dead — and how sure are you?"
- "Why did IKSHA reach this conclusion?"

Long-term: evolve from a CSS-focused analyzer into a general project intelligence platform — but CSS dead-code accuracy is the initial product's reason to exist.

---

## 4. Product Objectives

### 4.1 Primary objectives
1. Build an authoritative project inventory.
2. Build an accurate, bidirectional dependency graph.
3. Resolve relative/absolute/dynamic references correctly.
4. Preserve full dependency evidence (never discard, even for dynamic refs).
5. Analyze PHP, HTML, CSS, and JS **together**, not in isolation.
6. Determine file reachability and selector usage using the Domain Model in §2.
7. Detect CSS dead-code candidates and CSS quality problems.
8. Attach confidence + severity + evidence to every finding.
9. Explain every important finding (What/Where/Why/How/Confidence — §85).
10. Scale to large projects with deterministic, reproducible output.
11. Separate engine logic from CLI and reporting (§76 ownership rules).

### 4.2 Secondary objectives
1. Framework-specific adapters (later).
2. Additional languages (later).
3. Incremental analysis (architected for now, built later — §54).
4. Machine-readable output (JSON now, SARIF later).
5. IDE integration (future).

### 4.3 Non-objectives for initial release
IKSHA will **not**, in v1:
1. Execute arbitrary application code.
2. Guarantee runtime behavior.
3. Fully evaluate arbitrary dynamic PHP or JavaScript.
4. Replace a compiler/interpreter.
5. Prove that every unused-looking file is safely deletable — IKSHA reports confidence, not certainty of safety.

Static analysis limitations must always be explicitly represented in output, never hidden.

---

## 5. Core Design Principles

**5.1 Evidence over assumptions.** Every conclusion traces to recorded evidence (see Evidence Model, §51).

**5.2 One source of truth.** The Project Inventory is authoritative; no analyzer independently rediscovers files.

**5.3 Canonical file identity.** Files are identified by canonical project-relative/physical identity, never by filename alone. `css/main.css` and `css/admin/css/main.css` are different files even though both are named `main.css`. `css/main.css` and `css/../css/main.css` are the same file after normalization.

**5.4 Preserve raw evidence.** Every reference retains: raw text, normalized form, resolved target, source location, reference type, resolution method, confidence.

**5.5 Unknown is a valid result.** When analysis cannot determine something, return `UNKNOWN` — never guess.

**5.6 Separation of concerns.** Parsing ≠ reporting. Analyzers ≠ terminal output. CLI ≠ analysis logic. Reports ≠ analysis (see §76 module ownership).

**5.7 Determinism.** Same project + same config ⇒ same result, byte-for-byte in JSON output.

**5.8 Explainability.** Every finding must be understandable by a developer without reading engine source code.

---

## 6. Configuration Model

*(New section — v1.0 repeatedly said things "must be configurable" without ever specifying how.)*

### 6.1 Configuration sources, in precedence order (highest wins)
1. CLI flags (e.g. `--ignore node_modules,vendor`)
2. Project-local config file: `iksha.config.json` at project root
3. Built-in defaults

### 6.2 Config file schema (initial)

```json
{
  "extensions": {
    "php": [".php"],
    "html": [".html", ".htm"],
    "css": [".css"],
    "js": [".js", ".mjs", ".cjs"]
  },
  "ignore": ["node_modules", "vendor", ".git", "dist", "build"],
  "entryPoints": ["index.php", "admin/index.php"],
  "followSymlinks": false,
  "caseSensitivity": "auto",
  "maxFileSizeMB": 20,
  "severityThresholdForExitCode": "HIGH"
}
```

### 6.3 Rules
- Config is loaded once at scan start and is part of the deterministic analysis identity — the same project with different config may legitimately produce different results, and the config used must be recorded in the AnalysisResult (§64).
- Unknown config keys produce a warning diagnostic, not a crash.
- `caseSensitivity: "auto"` detects OS/filesystem behavior at runtime (see §11.4).

---

## 7. Target Project Types

Initial target: plain PHP websites, PHP template systems, mixed PHP/HTML apps, multi-page sites, admin dashboards, legacy sites, static HTML sites, JS-enhanced sites.

Future: Blade, Twig, WordPress, Laravel, React, Vue, other framework adapters.

---

## 8. System Architecture

```
                    ┌──────────────────────┐
                    │      CLI / API        │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │  ENGINE ORCHESTRATOR  │   ← renamed from v1.0 to avoid
                    └──────────┬───────────┘      duplicate "ANALYSIS ENGINE" label
                               ▼
                    ┌──────────────────────┐
                    │   PROJECT INVENTORY   │
                    └──────────┬───────────┘
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
                PHP/HTML     CSS         JS
                parsing     parsing    parsing
                    └──────────┼──────────┘
                               ▼
                    ┌──────────────────────┐
                    │ REFERENCE EXTRACTION  │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │   DEPENDENCY GRAPH     │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │        INDEXES         │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │    ANALYSIS PHASE      │
                    │  usage · reachability  │
                    │  CSS semantics         │
                    │  dead code · cross-lang│
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │ EVIDENCE + CONFIDENCE  │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │    FINDING ENGINE      │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │    ANALYSIS RESULT     │
                    └──────────┬───────────┘
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
                Terminal     JSON        HTML
                Report      Report      Report
```

---

## 9. Project Inventory

First engine stage: discover and classify project files.

Inventory record includes: file identity, absolute path, project-relative path, filename, extension, language/type, file size, readable status, parseable status, ignored status, generated status, **minified status** (new — see §10.5), source errors.

Efficient lookup required by: canonical path, relative path, filename, extension, file type.

---

## 10. File Discovery Requirements

**10.1 Supported initial extensions** — PHP `.php`; HTML `.html` `.htm`; CSS `.css`; JS `.js` `.mjs` `.cjs`. Configurable per §6.2.

**10.2 Ignored directories** — defaults: `.git`, `.venv`, `__pycache__`, `node_modules`, `vendor`, `dist`, `build`, `logs`, `output`. User-configurable.

**10.3 Generated files** — recognized separately from source; generated ≠ ignored.

**10.4 Symlinks** *(new)* — Symlinks are **not followed by default** (`followSymlinks: false`). If enabled, the engine must track visited canonical (real) paths and refuse to re-descend into an already-visited real path, to prevent infinite loops from symlink cycles. A symlinked file's canonical identity is its resolved real path, not the link path.

**10.5 Minified / generated source files** *(new)* — Files matching common minified patterns (`.min.css`, `.min.js`, or a single line exceeding a configurable length threshold, e.g. 2000 chars) are flagged `minified: true` in the inventory. Minified files:
- Still get parsed for reference extraction.
- Get excluded from line/column-precision reporting (column tracking degrades gracefully; report character offset instead).
- Are excluded from CSS quality findings (duplicate/redundant declarations) by default, since minifiers already do this transformation and false positives are near-guaranteed.

**10.6 File errors** — unreadable files must not crash the scan; represented as diagnostics (§53 categories).

---

## 11. Canonical File Identity & Path Resolution

**11.1** Files are never identified by filename alone (see §5.3).

**11.2** Path normalization must understand `.`, `..`, separators, relative/absolute paths, query strings, fragments, URL paths.

**11.3 OS-awareness.** The resolver must not blindly lowercase every path. Windows and Unix separator/case behavior must not be cross-applied.

**11.4 macOS case handling** *(new — v1.0 only addressed Windows vs. Linux)*. macOS's default filesystem (APFS) is **case-insensitive but case-preserving**: `Main.css` and `main.css` refer to the same file on disk, but the original casing is preserved in directory listings. The resolver must:
- Detect actual filesystem case-sensitivity at runtime (don't assume from OS name — some macOS/Linux volumes are configured either way) via a low-cost probe (e.g. attempt to stat a case-toggled version of a known file), or default conservatively per `caseSensitivity: "auto"` (§6.2).
- On case-insensitive filesystems, treat `Main.css` and `main.css` as the same canonical identity but preserve and report the on-disk casing.
- Never silently merge files that differ only in case on a case-*sensitive* filesystem.

**11.5 Reference resolution.** References are resolved relative to their source when appropriate; the same reference string may resolve to different files depending on source location (see v1.0 §10 examples — preserved, correct as written).

**11.6** Resolution strategies: `source-relative`, `project-relative`, `absolute`, `import-relative`, `url`, `dynamic`, `unknown`.

**11.7 Ambiguous references** (v1.0 §24, preserved): never silently choose between candidates. Return `AMBIGUOUS` with a candidate list and `UNKNOWN` confidence.

---

## 12. External References

External resources (CDN URLs, `data:` URIs) are represented as external references, not local project files, and are never fetched over the network by default (see Security, §46).

---

## 13. Source Ingestion

Centralized source loading providing: file identity, text, encoding, line offsets, line count, language, read errors — for consistent line/column tracking across all analyzers. Large files handled safely (streamed or size-capped per `maxFileSizeMB`).

---

## 14. PHP Analysis

Detect `include`, `require`, `include_once`, `require_once`. Attempt constant/static expression resolution (`__DIR__`, `__FILE__`, `dirname(...)`, known constant concatenation). Fully dynamic includes (`include $template;`) are recorded as dynamic/unknown evidence — never silently dropped.

---

## 15. PHP Template Analysis

Embedded HTML is parsed with awareness that attributes may be dynamically generated:
- `<div class="card">` → definite evidence.
- `<div class="<?= $class ?>">` → must **not** be treated as proof any given class is unused.
- `<div class="<?= $condition ? 'card' : 'panel' ?>">` → possible evidence for both `card` and `panel` when statically inferable.

---

## 16. HTML Analysis

Detect elements, classes, IDs, attributes, stylesheet links, script references, inline styles, relevant resource references. Each usage retains value, source file, line, column, origin, certainty.

---

## 17. CSS Analysis

CSS engine understands: selectors, selector lists, declarations, at-rules, imports, media queries, supports rules, layers, keyframes, custom properties, pseudo-classes/elements, specificity, source order. Source locations preserved throughout.

---

## 18. CSS Selector Model

Semantic selector representation (`.card`, `#modal`, `.container > .card`, `:not(.card)`, `[data-state="open"]`, etc.). Custom property names, attribute values, and pseudo-class names must never be misclassified as HTML elements/classes/IDs.

---

## 19. CSS Import Analysis

Detect `@import "..."` / `@import url(...)`. Handle relative paths, query strings, external URLs, nested import chains — full chain represented in the dependency graph.

---

## 20. JavaScript Analysis

**Static evidence sources:** `querySelector`, `querySelectorAll`, `getElementById`, `getElementsByClassName`, `getElementsByTagName`, `matches`, `closest`, `classList.add/remove/toggle/contains/replace`, `className`, `setAttribute("class"/"id", ...)`, `element.id = ...`, dynamic import, stylesheet loading.

**Dynamic references:** `element.classList.add(className)` → recorded as dynamic, confidence `UNKNOWN`. Partially static (`condition ? "active" : "hidden"`) → possible evidence for both branches. Dynamic evidence is never discarded.

---

## 21. Reference Extraction

Reference extraction is distinct from analysis. Reference types: PHP dependency, HTML stylesheet/script, CSS import, JS import/stylesheet, template dependency, DOM selector/class/ID reference. Every reference carries: source file, target/value, type, source location, confidence, resolution status, evidence.

---

## 22. Dependency Graph

Central relationship model: `source → target` edges. Supports `dependencies(file)`, `dependents(file)`, incoming/outgoing edges, children/parents, path search, **cycle detection**, reachability traversal.

---

## 23. Dependency Edge

Preserves: source file, target file, dependency type, source line/column, confidence, resolved status, evidence, resolution strategy.

---

## 24. Dynamic Dependencies

Unresolved dynamic references (`include $template;`) produce an unresolved dynamic dependency edge. Presence of an unresolved dynamic dependency lowers confidence in downstream dead-code conclusions (§2.3) but must never automatically mark everything as used.

---

## 25. Entry Point Discovery

Explicit, heuristic, or (future) framework-specific. Examples: `index.php`, `index.html`, `admin/index.php`, `login.php`, `api/index.php`. Heuristic entry points are marked as heuristic evidence (confidence `MEDIUM` per §2.4).

---

## 26. Reachability Engine

Traverses the dependency graph from entry points, assigning Reachability State (§2.1) to every file. A file affected only by an unresolved dynamic loader is `POTENTIALLY_REACHABLE`, never `UNREACHABLE`.

---

## 27. Project Map

Combination of: project inventory, file identities, references, dependency graph, entry points, reachability information. Answers: what exists, what references what, what depends on what, how was it discovered, can it be resolved, how confident are we.

---

## 28. Indexing

Large projects avoid repeated full scans via indexes: `ClassIndex`, `IDIndex`, `SelectorIndex`, `FileReferenceIndex`, `DependencyIndex`, `EntryPointIndex`.

---

## 29. CSS Usage Analysis

Combines HTML, PHP, JS, dynamic evidence, selector matching, and file reachability to assign Usage State (§2.2) per selector.

---

## 30. CSS Selector Matching

Semantic CSS selector parsing against a representative HTML DOM. Supports class/ID/element/descendant/child/attribute selectors, statically-meaningful pseudo-classes. Unsupported selector behavior produces controlled `UNKNOWN`, never a crash.

---

## 31. HTML/PHP Dynamic Usage

Dynamic class/ID construction affects confidence but never zeroes out usage for every class project-wide (see §15).

---

## 32. JavaScript CSS Usage

`document.querySelector(".sidebar-open")` and `classList.add("sidebar-open")` are both usage evidence for `.sidebar-open`, correlated against the CSS selector index.

---

## 33. Cross-Language Correlation

Example chain: `admin.php → admin.js → classList.add("sidebar-open") → sidebar.css → .sidebar-open`. This is the core mechanism that makes CSS usage analysis trustworthy across languages rather than CSS-only grep.

---

## 34. CSS Dead-Code Analysis

Combines: file reachability, stylesheet references, CSS imports, HTML/PHP/JS usage, dynamic references, dependency graph, entry points → produces Dead-Code State (§2.3) with full evidence trail.

---

## 35. File-Level Dead-Code Score

Example:

```
css/legacy.css
  stylesheet references: none
  CSS imports: none
  JS stylesheet references: none
  dependency reachability: none
  selectors: 18 total, 17 unused, 1 dynamic
  dynamic references: detected
  dead-code state: POSSIBLY_DEAD   (dynamic evidence present — not DEFINITELY_DEAD)
  confidence: 82%
```

The score is an analytical confidence signal, **not** a deletion recommendation.

---

## 36. Selector-Level Dead Code

Each selector carries: selector text, source file/location, Usage State, matched files, evidence, confidence. A selector may be a stronger dead-code candidate than its containing file.

---

## 37. CSS Declaration Analysis

Detect duplicate, conflicting, redundant, and overridden declarations, plus suspicious `!important` usage — always considering project-wide cascade (§40) before calling anything redundant.

---

## 38. CSS Rule Analysis (Cross-File)

Duplicate/conflicting rules are detected across files, not just within one file, accounting for source order, specificity, media/supports conditions, layers, and importance.

---

## 39. `!important` Analysis

Never automatically flagged as a defect. Classified by context (e.g. accessibility overrides may be intentional). Findings report `!important detected` with severity `INFO` by default, not `bad CSS`.

---

## 40. Cascade Analysis

Models selector specificity, source order, importance, **`@layer` cascade layers** (new — v1.0 didn't mention layers here despite listing them in §17; layers invert normal importance ordering and must be modeled explicitly, not just parsed), media conditions, supports conditions.

---

## 41. Custom Property Analysis

Tracks defined vs. referenced (`var(--x)`) custom properties; determines unused/unresolved custom properties with confidence.

---

## 42. Keyframe Analysis

Detects `@keyframes` and references via `animation-name`/`animation`; flags potentially unused keyframes while accounting for dynamic animation names.

---

## 43. Media/Conditional Analysis

Conditional context (`@media`, `@supports`) is preserved and available to all downstream analysis — a selector inside a media query is not equivalent to an unconditional selector.

---

## 44. Finding Engine

### 44.1 Finding ID scheme *(new)*

Every finding has a stable, deterministic ID for reference in `iksha explain <finding-id>` and CI diffing:

```
IKSHA-<CATEGORY>-<short-hash>
```

Where `<CATEGORY>` is a short code (e.g. `DEADCSS`, `DEP`, `CASCADE`) and `<short-hash>` is a deterministic hash of `(finding type, canonical source file, source line/column, target identity)`. The hash must be stable across runs given identical input (required for §54 determinism and CI diffing).

### 44.2 Finding types

`UNREACHABLE_FILE`, `POSSIBLY_DEAD_FILE`, `PROBABLY_DEAD_FILE`, `DEFINITELY_DEAD_FILE`, `UNUSED_SELECTOR`, `UNUSED_DECLARATION`, `DUPLICATE_DECLARATION`, `CONFLICTING_DECLARATION`, `DUPLICATE_RULE`, `REDUNDANT_DECLARATION`, `IMPORTANT_DECLARATION`, `UNRESOLVED_DEPENDENCY`, `DYNAMIC_DEPENDENCY`, `AMBIGUOUS_DEPENDENCY`, `CIRCULAR_DEPENDENCY`, `UNUSED_CUSTOM_PROPERTY`, `UNUSED_KEYFRAME`.

> Note: the four dead-file finding types now mirror the four Dead-Code States (§2.3) exactly, closing the v1.0 gap where only one finding type existed for four possible states.

### 44.3 Finding record

`id`, `finding type`, `severity` (§2.5), `confidence` (§2.4), `source file`, `source line/column`, `message`, `explanation`, `evidence`, `related files`, `related entities`.

---

## 45. Severity vs. Confidence

Independent axes (preserved from v1.0, now both formally defined in §2.4/§2.5). `severity: MEDIUM, confidence: HIGH` = "we're highly confident this medium-impact issue exists." `severity: HIGH, confidence: LOW` = "could be serious, evidence is weak." Never collapsed into one score.

---

## 46. Security Requirements

IKSHA treats project source as **untrusted input**. Requirements: no PHP/JS/shell execution from project source; no arbitrary network requests by default; safe, bounded path resolution that cannot escape the project root; bounded resource consumption; safe parsing (no crashes on malformed input); no writes into the scanned project unless explicitly requested (e.g. `--fix`, future). External URLs never trigger network access automatically.

---

## 47. Performance Requirements

Targets: small projects near-instant, medium projects seconds, large projects (10,000 files) predictable scaling. Achieved via indexes, caches, normalized identities, graph traversal, selective matching, memoization.

**47.1 Concurrency** *(new — v1.0 didn't address this)*. File-level parsing (PHP/HTML/CSS/JS extraction) is embarrassingly parallel and should be parallelized across files once dependency-graph construction doesn't require ordering. Cross-file analysis phases (usage, dead-code correlation) run after all parsing completes, since they require the full Project Map. Parallelism must not affect determinism (§54) — results are merged into a canonically-ordered structure regardless of completion order.

---

## 48. Memory Requirements

Source text loaded once; parsed representations reference source metadata rather than duplicating it; indexes store references, not duplicated structures.

---

## 49. Incremental Analysis (Future Architecture)

If `css/cards.css` changes, the engine should eventually identify and recompute only affected selectors/dependencies/usage/findings. Not implemented in v1, but the module boundaries (§76) must not preclude it later.

---

## 50. Deterministic Output

Same project + config ⇒ same result, byte-for-byte. Collections sorted where order matters. Findings have stable ordering and stable IDs (§44.1). Required for testing, CI, diffing, caching.

---

## 51. Evidence Model

Every conclusion answers: WHAT was found? WHERE? HOW? WHAT does it point to? HOW certain?

```
Evidence
  source: index.php
  line: 12
  raw: css/main.css
  type: stylesheet reference
  resolution: source-relative
  target: css/main.css
  confidence: 96%  (CERTAIN)
```

---

## 52. Confidence Model

See §2.4 for the full categorical/numeric definition and mapping table. This section is retained as a pointer to avoid duplicate/conflicting definitions (fixes v1.0 §47).

---

## 53. Error Handling

A malformed file must not terminate the full scan. Diagnostic categories: `FILE_READ_ERROR`, `ENCODING_ERROR`, `PARSE_ERROR`, `RESOLUTION_ERROR`, `UNSUPPORTED_SYNTAX`, `ANALYSIS_ERROR`. Engine continues analyzing unaffected files.

---

## 54. Engine API

```
result = engine.analyze(project_path, config)
```

Caller does not need to know about individual scanners — those are internal implementation details owned per §76.

---

## 55. Analysis Result

Contains: project inventory, dependency graph, references, indexes, entry points, reachability, usage analysis, CSS analysis, findings, diagnostics, statistics, **and the resolved configuration used for the run** (new — required for reproducibility per §6.3). Structured and serializable.

---

## 56. CLI Requirements

Initial command: `iksha scan .`

Future: `iksha files <path>`, `iksha dependencies <path>`, `iksha unused <path>`, `iksha css <path>`, `iksha explain <finding-id>`, `iksha report <path>`.

**56.1 Verbose/trace mode** *(new)*. `iksha scan . --trace` streams the evidence-gathering process for each finding as it's computed — reinforces explainability (§85) as a debuggable, inspectable process rather than a black box, and is invaluable for debugging the resolver itself during development.

**56.2 CI exit code contract** *(new)*. Exit code `0` if no findings meet or exceed `severityThresholdForExitCode` (§6.2, default `HIGH`); nonzero otherwise. This must be explicit since §60 targets CI/CD integration but v1.0 never specified the contract.

CLI must not implement analysis logic (owned by Engine/Analyzers per §76).

---

## 57. CLI Output

Terminal output: project information, scan progress, file statistics, dependency statistics, reachability statistics, usage statistics, finding summary, severity summary, high-confidence issues. Detailed analysis available via dedicated reports.

---

## 58. Reporting

Separate subsystem. Required formats: terminal, JSON. Future: HTML, CSV, SARIF. Reports consume `AnalysisResult` only — never re-run or modify analysis.

---

## 59. JSON Output

Machine-readable: project, files, dependencies, references, usage, reachability, findings (with stable IDs), diagnostics, confidence, statistics, resolved config. Enables CI/CD, IDE, dashboard integration.

---

## 60. Testing Strategy

Unit, integration, end-to-end, regression, performance, fixture tests — mandatory for every engine component.

**60.1 Confidence-formula regression tests** *(new)*. Since the confidence percentage → category mapping (§2.4) and the Dead-Code State derivation rule (§2.3) are both load-bearing for the product's core promise, they require dedicated test suites that pin exact expected outputs for a fixed set of evidence combinations, so any future change to the weighting formula is caught immediately.

---

## 61. Real-World Fixtures

Include: nested templates, multiple `main.css` files (duplicate filenames), CSS imports, PHP includes, dynamic PHP, JS class manipulation, dynamic JS selectors, circular dependencies, missing files, malformed files, multiple entry points, conditional templates, media queries, external stylesheets, query-string CSS references, **symlinked files, minified CSS/JS, mixed-case filenames on case-insensitive filesystems** (new, per §10.4/§10.5/§11.4).

---

## 62. Path Testing

`.`, `..`, nested paths, Windows/Unix separators, absolute/relative paths, duplicate filenames, query strings, fragments, **and case-sensitivity behavior across all three target OSes** (expanded from v1.0's Windows/Linux-only framing).

---

## 63. False Positive Testing

Dedicated tests to prevent over-aggressive dead-code detection: dynamic PHP classes, dynamic JS selectors, multiple entry points, runtime stylesheet loading, ambiguous paths, conditional classes. **This test category is the single most important test suite in the product**, given §0's core mission.

---

## 64. Regression Policy

Every discovered bug gets a regression test: failing test → implementation → passing test. No exceptions.

---

## 65. Code Quality Requirements

Type hints, clear domain boundaries, small cohesive components, deterministic behavior, meaningful names, documentation for public APIs, no hidden global state, no unnecessary duplication.

---

## 66. Dependency Policy

Prefer mature third-party parsers over handwritten regex for full-language syntax. Regex acceptable only for narrow lexical detection, never as the primary parser for PHP/CSS/JS grammar.

---

## 67. Architectural Anti-Patterns

Do **not**: create a new scanner per small feature; duplicate file discovery logic; identify files by filename; silently discard dynamic references; classify unresolved references as dead; let CLI or reports perform analysis; mix parsing with finding generation; use global mutable state; silently swallow errors; add special-case regexes indefinitely; create duplicate domain models for the same concept (this PRD's §2 exists specifically to prevent that last one).

---

## 68. Module Ownership

| Module | Owns |
|---|---|
| Project Inventory | Files |
| Path/Identity | Canonical file identity, resolution |
| Parsers | Source structure |
| Reference Extraction | Discovering relationships |
| Dependency Graph | Relationships |
| Indexes | Efficient lookup |
| Analyzers | Interpretation |
| Evidence | Proof/uncertainty |
| Finding Engine | Final issue representation |
| Engine | Orchestration |
| CLI | User interaction |
| Reports | Presentation |

---

## 69. No File-Sprawl Rule

Before creating a new module: does an existing module already own this responsibility? If yes, extend it. Create new only for a genuine domain boundary that cannot reasonably belong elsewhere.

---

## 70. Project Directory Structure (conceptual)

```
src/iksha/
    domain/       ← §2 enums live here, imported everywhere else
    config/       ← §6
    inventory/
    parsing/
    references/
    graph/
    indexes/
    analysis/
    findings/
    engine/
    cli/
    reporting/
```

Finalize exact physical structure after domain model implementation. Do not create empty directories to match a diagram.

---

## 71. Development Order

```
PHASE 0   PRD + architecture contract
PHASE 1   Domain model (§2 — enums, confidence formula, evidence model)
PHASE 2   Configuration model (§6)
PHASE 3   Project inventory
PHASE 4   Canonical path/file identity (incl. case-sensitivity, symlinks)
PHASE 5   Source ingestion (incl. minified-file handling)
PHASE 6   PHP/HTML/CSS/JS parsing
PHASE 7   Reference extraction
PHASE 8   Dependency graph
PHASE 9   Indexing
PHASE 10  Entry-point discovery
PHASE 11  Reachability
PHASE 12  CSS semantic analysis
PHASE 13  HTML/PHP usage analysis
PHASE 14  JavaScript usage analysis
PHASE 15  Cross-language correlation
PHASE 16  Dead-code analysis (the flagship capability — §0)
PHASE 17  CSS quality analysis
PHASE 18  Evidence + confidence scoring
PHASE 19  Finding engine (incl. finding IDs)
PHASE 20  Incremental analysis (future)
PHASE 21  Performance + concurrency
PHASE 22  Engine integration
PHASE 23  CLI (incl. --trace, exit codes)
PHASE 24  Reporting
PHASE 25  Integration fixtures
PHASE 26  Production hardening
```

Each phase requires: implementation, unit tests, integration tests where applicable, edge-case tests, regression tests, documentation, architecture review. All tests pass before advancing.

---

## 72. Initial Release Success Criteria

IKSHA v1 is production-ready when it:

1. Reliably inventories supported project files.
2. Maintains canonical file identities (incl. case-sensitivity and symlink safety).
3. Correctly resolves common relative/absolute references.
4. Distinguishes duplicate filenames in different directories.
5. Builds a bidirectional dependency graph and detects cycles.
6. Preserves dependency evidence, including dynamic/unresolved references.
7. Analyzes PHP/HTML/CSS/JS together, not in isolation.
8. Detects CSS usage from HTML/PHP/JS with correct cross-language correlation.
9. Provides reachability information per §2.1.
10. Classifies dead-code candidates using the exact §2.3 derivation rule, with zero false `DEFINITELY_DEAD` classifications on the false-positive fixture suite (§63).
11. Reports confidence (numeric + categorical) and severity as independent axes on every finding.
12. Detects major CSS quality issues (duplicates, conflicts, unused custom properties/keyframes).
13. Explains every finding per the What/Where/Why/How/Confidence template (§85).
14. Never executes project code.
15. Handles malformed files, minified files, and symlinks safely.
16. Produces deterministic, byte-identical output for identical input+config.
17. Passes the complete automated test suite, especially the false-positive suite (§63).
18. Performs acceptably on the 10,000-file fixture project.
19. Exposes a documented JSON schema and correct CI exit-code behavior.

---

## 73. Future Features

Framework adapters (React, Vue, Blade, Twig, WordPress), TypeScript/SCSS/LESS support, source maps, SARIF, IDE integration, VS Code extension, incremental analysis, project history, CI integration, automated cleanup suggestions, safe refactoring assistance, dependency/architecture visualization, interactive HTML report.

---

## 74. Long-Term Product Direction

```
                    PROJECT
                       │
                 PROJECT GRAPH
          ┌────────────┼────────────┐
       STRUCTURE     USAGE      DEPENDENCY
          └────────────┼────────────┘
                    EVIDENCE
                       │
                    FINDINGS
                       │
                 DEVELOPER ACTION
```

---

## 75. Final Engine Philosophy

A tool reporting 100 false "dead CSS" files is worse than one reporting 20 high-confidence dead files with evidence. IKSHA favors correctness, explainability, uncertainty-awareness, determinism, traceability, and scalability over aggressive guessing or maximum finding count.

---

## 76. Final Product Principle — The Explanation Template

Every important conclusion must answer WHAT / WHERE / WHY / HOW / CONFIDENCE:

```
Finding: css/legacy.css is probably unused.

What:    Potentially dead stylesheet.
Where:   css/legacy.css
Why:     No static stylesheet reference was found.
         No CSS import reaches it.
         No JavaScript stylesheet reference was found.
         None of its selectors have definite HTML/PHP usage.
How:     Evidence gathered from the project dependency graph,
         HTML/PHP analysis, CSS analysis, and JavaScript references.
Confidence: 91% (HIGH)
Uncertainty: One dynamic stylesheet loader was detected elsewhere
             in the project, which is why this is POSSIBLY_DEAD
             rather than DEFINITELY_DEAD.
```

This is a core product requirement, not an optional reporting feature.

---

## 77. Glossary

*(New section)*

- **Canonical identity** — a file's unique project-relative, OS-normalized path, used instead of filename for all internal references.
- **Entry point** — a file assumed to be directly loaded by a user/browser (e.g. `index.php`), the starting point for reachability traversal.
- **Evidence** — a recorded, attributable fact (with source location and confidence) supporting a conclusion.
- **Project Map** — the combined structural model: inventory + identities + references + graph + entry points + reachability.
- **Resolution strategy** — the method used to turn a raw reference string into a resolved file (e.g. `source-relative`, `dynamic`).
- **Dead-Code State** — file-level classification of CSS disuse; see §2.3.
- **Usage State** — selector-level classification of whether a specific selector is referenced; see §2.2.
- **Reachability State** — file-level classification of whether a file can be reached from an entry point; see §2.1.

---

*End of PRD v2.0*