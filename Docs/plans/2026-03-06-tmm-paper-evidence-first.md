# TMM Paper Evidence-First Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Revise the TMM manuscript so the text, figures, claims, and reported numbers are submission-ready and strictly aligned with verified code/results in the repository.

**Architecture:** First audit the manuscript against local evidence and official TMM/IEEE expectations, then rewrite only the sections whose claims exceed the available evidence, and finally run LaTeX and consistency checks until the paper has no obvious submission blockers.

**Tech Stack:** LaTeX (`IEEEtran`, `natbib`), local experiment reports/CSVs/figures, shell-based audit commands, selective web verification for official IEEE/TMM guidance and key literature.

---

### Task 1: Build the manuscript audit map

**Files:**
- Modify: `/Users/xyh/Code/Audio-agent/docs/plans/2026-03-06-tmm-paper-evidence-first-design.md`
- Read: `/Users/xyh/Code/Audio-agent/Paper/main.tex`
- Read: `/Users/xyh/Code/Audio-agent/Paper/content.tex`
- Read: `/Users/xyh/Code/Audio-agent/Paper/TMM_Response_to_Reviewers.md`
- Read: `/Users/xyh/Code/Audio-agent/Paper/TMM_Revision_Checklist.md`
- Read: `/Users/xyh/Code/Audio-agent/Experiments/**`

**Step 1: Enumerate the major claim blocks**

List the paper's major claims by section:
- abstract
- introduction contribution sentence
- Protocol-A comparison
- RAG necessity
- Protocol-C robustness
- listening study
- memory/personalization
- latency/complexity

**Step 2: Map each block to evidence**

For each block, identify:
- exact supporting file(s)
- whether the support is numeric, narrative, figure-based, or only planned
- whether the evidence is directly reproducible from the repo

**Step 3: Tag each block**

Assign one of:
- `verified`
- `weak`
- `unsupported`

**Step 4: Record the rewrite action**

For each non-verified block, specify:
- keep as-is
- narrow the wording
- move to discussion/limitations
- remove entirely

### Task 2: Fix LaTeX submission hygiene

**Files:**
- Modify: `/Users/xyh/Code/Audio-agent/Paper/main.tex`
- Modify: `/Users/xyh/Code/Audio-agent/Paper/content.tex`

**Step 1: Fix figure path usage**

Normalize all `\\includegraphics{...}` calls so they work with the existing `\\graphicspath`.

**Step 2: Fix obvious compile blockers**

Resolve:
- missing figure path mismatches
- duplicate path prefixes
- other local compile blockers discovered by `latexmk`

**Step 3: Check reference hygiene**

Ensure bibliography and citation usage are consistent with the chosen style and that there are no avoidable undefined reference issues from local structure.

### Task 3: Rewrite the high-risk sections

**Files:**
- Modify: `/Users/xyh/Code/Audio-agent/Paper/content.tex`

**Step 1: Rewrite the abstract**

Constraints:
- keep journal tone
- prioritize verified contributions
- remove or soften unsupported "state-of-the-art" and incomplete experiment claims
- keep length in a normal IEEE journal range

**Step 2: Rewrite the introduction contribution framing**

Make the contribution paragraph align with the strongest verified evidence and reduce "agent" overclaiming.

**Step 3: Rewrite methodology framing where needed**

Especially:
- AEM
- latency/complexity
- adaptive fusion

Only keep claims that survive Task 1.

**Step 4: Rewrite experiments/discussion/limitations**

Goals:
- clearly separate retrieval-only benchmark results from system-level narrative
- make Protocol-C and AEM treatment evidence-bounded
- strengthen limitation language where evidence is incomplete

### Task 4: Verify literature positioning

**Files:**
- Modify: `/Users/xyh/Code/Audio-agent/Paper/content.tex`

**Step 1: Check key cited works**

Verify existence/relevance of the most claim-bearing references in:
- audio effect parameter inference/control
- retrieval-based audio control
- audio representation baselines
- RAG/tool-use comparisons

**Step 2: Remove weak comparison rhetoric**

Do not imply direct superiority over CLAP/PaSST/PANNs or other modern baselines unless the repo contains completed results that support that comparison.

**Step 3: Strengthen TMM-facing positioning**

Make the paper read as a multimedia signal processing/system contribution with executable parameter control relevance, not a generic agent paper.

### Task 5: Compile and produce the final gap report

**Files:**
- Modify: `/Users/xyh/Code/Audio-agent/docs/plans/2026-03-06-tmm-paper-evidence-first-design.md`
- Verify: `/Users/xyh/Code/Audio-agent/Paper/main.tex`
- Verify: `/Users/xyh/Code/Audio-agent/Paper/content.tex`

**Step 1: Run LaTeX compilation**

Run a full compile and capture:
- compile success/failure
- warnings that materially affect submission quality

**Step 2: Run a final consistency pass**

Check:
- abstract matches body
- tables/figures are actually present
- no section overclaims beyond local evidence

**Step 3: Produce a residual gap summary**

Document the remaining evidence gaps that still require new experiments rather than more writing.

