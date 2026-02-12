# Audit: Interview & Assessment Agent Prompt Files

**Date:** February 12, 2026

This audit traces which prompt/instruction text files are actually used at runtime, which are dead code, and which can be merged or removed.

---

## Executive Summary

| Status | Count |
|--------|-------|
| **Actively used** | 4 files |
| **Unused / dead** | 8 files |
| **Documentation only** | 1 file |
| **Merge candidates** | 2 pairs |

---

## 1. ACTIVELY USED

### Interview agent

| File | Loaded by | Platform |
|------|-----------|----------|
| `core/resources/interview_system_prompt.txt` | `web/backend/realtime_bridge.py` → `_load_interview_system_prompt()` | **Web** |
| *(removed)* `interview_guide.txt` | ~~obsolete~~ | — |

### Assessment agent

| File | Loaded by | Platform |
|------|-----------|----------|
| `core/resources/system_prompt.txt` | `core/assessment_agent.py` → `_load_system_prompt()` | **Web & Desktop** |

---

## 2. NOT USED (dead / obsolete)

### Can be removed

| File | Reason |
|------|--------|
| `core/resources/interview_system_prompt_old.txt` | Old backup; never referenced. Has UTF-16 BOM encoding issue. Superseded by `interview_system_prompt.txt`. |
| `resources/interview_guideline.pdf` | Superseded by `interview_guide.txt` (see CHANGES_INTERVIEW_GUIDANCE_UPDATE.md). No code references it. |
| `resources/assess_prot.txt` | Merged into `core/resources/system_prompt.txt` in optimization (OPTIMIZATION_SUMMARY.md). Assessment agent loads system_prompt.txt directly. |
| `tools/assess_prot.txt` | Orphaned. `tools/assessment_guidance.py` looks for `resources/assess_prot.txt`, not `tools/assess_prot.txt`. Neither path is used by AssessmentAgent. |
| `core/tools/assess_prot.txt` | Orphaned. `core/tools/assessment_guidance.py` looks for `core/resources/assess_prot.txt`, which does not exist. Assessment agent uses `system_prompt.txt`, not assess_prot. |

### Dead loader code (not loaded by runtime)

| File | Reason |
|------|--------|
| `tools/assessment_guidance.py` | `read_guidance()` is never called. AssessmentAgent loads `system_prompt.txt` directly. |
| `core/tools/assessment_guidance.py` | Same. Would fail if called (wrong path: expects `core/resources/assess_prot.txt`). |

---

## 3. DOCUMENTATION ONLY

| File | Purpose |
|------|---------|
| `core/resources/interview_system_prompt_flowchart.md` | Flowchart generated from `interview_system_prompt.txt`. Not loaded by code. Documentation/reference. |

---

## 4. DUPLICATES & MERGE OPPORTUNITIES

### ~~Duplicate: `interview_guide.txt` (identical content)~~ ✅ DONE

- ~~`resources/interview_guide.txt`~~ → **removed** (was used by desktop)
- `core/resources/interview_guide.txt` → **canonical** — used by both desktop and tests

**Done:** `tools/interview_guidance.py` now loads from `core/resources/interview_guide.txt`.

### ~~Different content: `interview_system_prompt.txt` vs `interview_guide.txt`~~ ✅ DONE

- **Web** uses `interview_system_prompt.txt` (pre-loaded)
- **Desktop** now uses `interview_system_prompt.txt` (pre-loaded via `core.prompt_loader`)

**Done:** Both platforms use `core/resources/interview_system_prompt.txt`. The `interview_guidance` tool and `interview_guide.txt` were removed.

### Duplicate: `tools/` vs `core/tools/`

- `tools/` (project root) → used by **desktop** (`desktop/handlers/function_handler.py` uses `from tools.interview_guidance import get_interview_guidance`)
- `core/tools/` → used by **test_uv_setup.py** only

**Recommendation:** Consolidate to `core/tools/` and update desktop to import from `core.tools`. Remove the project-root `tools/` directory after migration.

---

## 5. RECOMMENDED ACTIONS

### Phase 1: Remove dead files

1. Delete `core/resources/interview_system_prompt_old.txt`
2. Delete `resources/interview_guideline.pdf`
3. Delete `resources/assess_prot.txt`
4. Delete `tools/assess_prot.txt`
5. Delete `core/tools/assess_prot.txt`
6. Delete `tools/assessment_guidance.py` (and remove from `tools/__init__.py`)
7. Delete `core/tools/assessment_guidance.py` (and remove from `core/tools/__init__.py`)

### Phase 2: Consolidate structure

1. Pick one canonical interview prompt (recommend `interview_system_prompt.txt` for web + desktop).
2. Unify `interview_guide.txt` copies: keep `core/resources/interview_guide.txt` only, or merge its content into `interview_system_prompt.txt` and retire it.
3. Consolidate `tools/` into `core/tools/`, update desktop imports.

### Phase 3: Optional – simplify desktop

1. Consider having desktop pre-load `interview_system_prompt.txt` (like web) instead of using the `interview_guidance` tool.
2. This would remove the need for `interview_guidance` tool and `interview_guide.txt` on desktop.

---

## 6. FILE REFERENCE MAP

```
korean_voice_tutor/
├── core/
│   ├── resources/
│   │   ├── interview_system_prompt.txt    ✅ USED (web)
│   │   ├── interview_system_prompt_old.txt   ❌ DELETE
│   │   ├── interview_system_prompt_flowchart.md   📄 DOC only
│   │   ├── *(removed)* interview_guide.txt   — obsolete
│   │   └── system_prompt.txt              ✅ USED (assessment)
│   └── tools/
│       ├── *(removed)* interview_guidance.py   — obsolete
│       ├── assessment_guidance.py         ❌ DELETE (dead)
│       └── assess_prot.txt                 ❌ DELETE (orphaned)
├── resources/
│   ├── interview_guideline.pdf            ❌ DELETE (obsolete)
│   └── assess_prot.txt                    ❌ DELETE (merged)
└── tools/
    ├── *(removed)* interview_guidance.py   — obsolete
    ├── assessment_guidance.py              ❌ DELETE (dead)
    └── assess_prot.txt                    ❌ DELETE (orphaned)
```

---

## 7. CODE REFERENCES

| Loader | File Loaded |
|--------|-------------|
| `web/backend/realtime_bridge.py` | `core/resources/interview_system_prompt.txt` |
| `core/assessment_agent.py` | `core/resources/system_prompt.txt` |
| `desktop/interview_agent_v2.py` | `core.prompt_loader.load_interview_system_prompt()` → `core/resources/interview_system_prompt.txt` |
| `core.prompt_loader` | `core/resources/interview_system_prompt.txt` |
