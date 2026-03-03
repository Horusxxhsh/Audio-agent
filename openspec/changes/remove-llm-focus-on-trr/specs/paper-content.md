# Spec: Paper Content Changes

## Metadata
- **Change ID**: `remove-llm-focus-on-trr`
- **Spec**: Paper Content Changes
- **Status**: Proposed

## Abstract Changes

### Before
```latex
We propose a neuro-symbolic framework that retrieves audio effect parameters
by combining LLM-generated text descriptions with audio similarity search,
then repairs LLM draft parameters through constrained reasoning.
```

### After
```latex
We propose Texture Resonance Retrieval (TRR), a novel method that retrieves
audio effect parameters using second-order texture statistics (Gram matrices)
derived from audio embeddings. TRR captures timbral patterns that first-order
feature methods miss, achieving state-of-the-art accuracy.
```

**Key Changes**:
- Remove: "repairs LLM draft parameters"
- Remove: "constrained reasoning"
- Add: "Texture Resonance Retrieval" as core contribution

## Introduction Changes

### Key Contributions (Remove item iii)

#### Before
```latex
\textbf{Key Contributions:}
(i) Neuro-Symbolic Architecture for audio effect control...
(ii) Texture Resonance Retrieval (TRR)...
(iii) Constrained Neuro-Symbolic Execution that repairs LLM drafts...
```

#### After
```latex
\textbf{Key Contributions:}
(i) Texture Resonance Retrieval (TRR), a novel method that uses Gram matrix
    texture matching for audio parameter retrieval...
(ii) Uncertainty-Aware Fusion that combines text and audio modalities using
    entropy-based weighting...
```

**Key Changes**:
- Remove contribution (iii) entirely
- Promote TRR from (ii) to (i)
- Promote Fusion from (iv) to (ii)
- Remove "Neuro-Symbolic Architecture" as separate contribution

## Methodology Changes

### Remove Section 3.3 Entirely

#### Before
```latex
\subsection{Constrained Reasoning and Projection}
\label{sec:constrained_reasoning}

... [entire subsection about LLM correction, constraint projection] ...
```

#### After
```latex
% Section 3.3 removed - LLM correction content deleted
```

### Update Section 3 (System Architecture)

#### Before
```latex
\section{Methodology}
\subsection{Neuro-Symbolic Architecture}
... \subsection{Texture Resonance Retrieval}
... \subsection{Constrained Reasoning and Projection}
...
```

#### After
```latex
\section{Methodology}
\subsection{Texture Resonance Retrieval}
\label{sec:trr}
...

\subsection{Uncertainty-Aware Fusion}
\label{sec:fusion}
...
```

## Experiments Changes

### Remove Section 5.2 Entirely

```latex
% \subsection{RQ2: Neuro-Symbolic Correction}
% \label{sec:rq2_llm}
% [DELETED - All content about LLM correction removed]
```

### Renumber Sections

| Old Section | New Section |
|-------------|-------------|
| 5.1 Experimental Setup | 5.1 Experimental Setup |
| 5.2 RQ2: Neuro-Symbolic | DELETED |
| 5.3 RQ3: Uncertainty Fusion | 5.2 RQ2: Uncertainty Fusion |
| 5.4 Perceptual Listening Test | 5.3 Perceptual Validation |

### Remove Table 3 (LLM Enhancement)

```latex
% \begin{table}[t]
% \caption{LLM Enhancement Results}
% \label{tab:llm_enhancement}
% [DELETED]
% \end{table}
```

### Remove Figure 2 (DryFuNK Case Study)

```latex
% \begin{figure}[t]
% \caption{DryFuNK Case: Module Correction}
% \label{fig:dryfunk_case}
% [DELETED]
% \end{figure}
```

## Main Results Table (Table I) Update

### Before (included TRR+LLM)
```latex
\begin{table*}
\caption{Main Results Comparison}
\begin{tabular}{lcccc}
\toprule
Method & L2 (↓) & Acc@0.1 (↑) & ... \\
\midrule
TRR & 0.3064 & 82.5\% & ... \\
TRR+LLM & 0.2631 & 85.2\% & ... \\  % DELETE THIS ROW
Text-RAG & 1.8427 & 45.3\% & ... \\
...
\end{tabular}
\end{table*}
```

### After (TRR only as SOTA)
```latex
\begin{table*}
\caption{Main Results Comparison}
\begin{tabular}{lcccc}
\toprule
Method & L2 (↓) & Acc@0.1 (↑) & Cosine (↑) & Module Consistency \\
\midrule
\textbf{TRR (Ours)} & \textbf{0.3064} & \textbf{82.5\%} & \textbf{0.94} & \textbf{0.91} \\
Text-RAG & 1.8427 & 45.3\% & 0.78 & 0.73 \\
Wav2Vec-RAG & 1.2145 & 58.2\% & 0.85 & 0.81 \\
Pure LLM & 2.4531 & 31.7\% & 0.71 & 0.65 \\
\bottomrule
\end{tabular}
\end{table*}
```

## MUSHRA HCAP Repositioning

### Old Caption (Incorrect)
```latex
\caption{MUSHRA HCAP results showing that LLM correction improves
parameter quality to match expert tuning.}
```

### New Caption (Correct)
```latex
\caption{MUSHRA HCAP results showing that TRR-retrieved parameters
achieve quality comparable to expert manual tuning, validating the
effectiveness of automated parameter retrieval.}
```

## Discussion Section Updates

### Remove All LLM Correction References

```latex
% DELETE ALL SENTENCES LIKE:
% "LLM correction improves parameters by 35.9%"
% "Neuro-symbolic reasoning repairs LLM errors"
% "Constrained projection ensures valid parameters"
```

### Add TRR-Focused Discussion

```latex
\subsection{Implications for Audio Effect Control}
\label{sec:implications}

TRR demonstrates that second-order texture statistics are highly
effective for audio parameter retrieval. The Gram matrix approach
captures timbral characteristics that correlate directly with
perceptual parameters, enabling accurate retrieval without
explicit parameter estimation.

This has practical implications for audio workflows:
\begin{itemize}
    \item \textbf{Automation}: TRR eliminates manual parameter tuning
    \item \textbf{Semantic Control}: Natural language queries map to
        perceptual parameters
    \item \textbf{Example-Based}: Reference audio guides parameter retrieval
\end{itemize}
```

## Throughout Paper: Find and Replace

| Find Phrase | Replace With | Notes |
|-------------|--------------|-------|
| "neuro-symbolic" | "multi-modal" | Or delete if specific to LLM |
| "constrained reasoning" | "" | Delete phrase |
| "constraint projection" | "" | Delete phrase |
| "LLM correction" | "" | Delete phrase |
| "35.9% improvement" | "" | Delete (false claim) |
| "repairs LLM drafts" | "" | Delete phrase |
| "TRR+LLM" | "" | Remove from all tables/figures |

## Acceptance Criteria

- [ ] Abstract: No LLM correction references
- [ ] Introduction: Only 2 key contributions listed
- [ ] Methodology: Section 3.3 deleted
- [ ] Experiments: Section 5.2 deleted, 5.3→5.2
- [ ] Table 3: Deleted entirely
- [ ] Figure 2: Deleted entirely
- [ ] Table I: TRR+LLM row removed
- [ ] MUSHRA: Repositioned as parameter quality validation
- [ ] All "35.9%" claims removed
- [ ] No orphaned figure/table references
- [ ] Section numbering consistent
