# Protocol-A Derived Analysis

- Input CSV: `Experiments/AblationStudies/protocolA_per_query_metrics.csv`
- Paired query count (TRR rows): 211
- Unique `query_name` labels in TRR rows: 210
- Pairing is performed by `query_idx`; one query label is reused in the CSV, so label-level uniqueness is lower than row count.

## TRR vs FeatureNN-RAG

- Shared paired queries: 211

| Metric | Wins | Losses | Ties | MeanΔ | MedianΔ | P25 | P75 | Min | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| l2 | 43 | 14 | 154 | 0.8666 | 0.0000 | 0.0000 | 0.0000 | -0.3441 | 20.8420 |
| acc@0.1 | 49 | 8 | 154 | 0.0489 | 0.0000 | 0.0000 | 0.0000 | -0.2381 | 0.6471 |
| recall | 28 | 22 | 161 | 0.0505 | 0.0000 | 0.0000 | 0.0000 | -0.4000 | 1.0000 |
| cosine | 43 | 14 | 154 | 0.0620 | 0.0000 | 0.0000 | 0.0000 | -0.4584 | 0.9954 |
| module | 14 | 21 | 176 | -0.0028 | 0.0000 | 0.0000 | 0.0000 | -0.6667 | 0.8333 |

### Largest TRR Gains by L2

| query_idx | Query | TRR retrieved | Baseline retrieved | ΔL2 | TRR L2 | Baseline L2 |
| --- | --- | --- | --- | --- | --- | --- |
| 19 | Hard Rock Crunch | Studio Clean | Auto-Tune Pop | 20.8420 | 0.1576 | 20.9996 |
| 52 | Hard Rock Crunch - Vintage Drive Mix | Studio Clean | Auto-Tune Pop | 20.8420 | 0.1576 | 20.9996 |
| 82 | Hard Rock Crunch - Raw Amp Pass | Studio Clean | Auto-Tune Pop | 20.8420 | 0.1576 | 20.9996 |
| 112 | Hard Rock Crunch - Grit Stack Take | Studio Clean | Auto-Tune Pop | 20.8420 | 0.1576 | 20.9996 |
| 142 | Hard Rock Crunch - Classic Crunch Edit | Studio Clean | Auto-Tune Pop | 20.8420 | 0.1576 | 20.9996 |

### Largest TRR Failures by L2

| query_idx | Query | TRR retrieved | Baseline retrieved | ΔL2 | TRR L2 | Baseline L2 |
| --- | --- | --- | --- | --- | --- | --- |
| 9 | Tweed Breakup | Vintage Tweed Breakup | Piano House | -0.3441 | 0.4935 | 0.1495 |
| 33 | Tweed Breakup - Vintage Drive Mix | Vintage Tweed Breakup | Piano House | -0.3441 | 0.4935 | 0.1495 |
| 63 | Tweed Breakup - Raw Amp Pass | Vintage Tweed Breakup | Piano House | -0.3441 | 0.4935 | 0.1495 |
| 93 | Tweed Breakup - Grit Stack Take | Vintage Tweed Breakup | Piano House | -0.3441 | 0.4935 | 0.1495 |
| 123 | Tweed Breakup - Classic Crunch Edit | Vintage Tweed Breakup | Piano House | -0.3441 | 0.4935 | 0.1495 |

## TRR vs Text-RAG

- Shared paired queries: 211

| Metric | Wins | Losses | Ties | MeanΔ | MedianΔ | P25 | P75 | Min | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| l2 | 43 | 14 | 154 | 0.1509 | 0.0000 | 0.0000 | 0.0000 | -0.3379 | 3.8830 |
| acc@0.1 | 35 | 22 | 154 | 0.0220 | 0.0000 | 0.0000 | 0.0000 | -0.3810 | 0.4706 |
| recall | 28 | 14 | 169 | 0.0583 | 0.0000 | 0.0000 | 0.0000 | -0.3636 | 1.0000 |
| cosine | 43 | 14 | 154 | 0.0972 | 0.0000 | 0.0000 | 0.0000 | -0.1335 | 0.9971 |
| module | 36 | 7 | 168 | 0.0949 | 0.0000 | 0.0000 | 0.0000 | -0.2000 | 0.8000 |

### Largest TRR Gains by L2

| query_idx | Query | TRR retrieved | Baseline retrieved | ΔL2 | TRR L2 | Baseline L2 |
| --- | --- | --- | --- | --- | --- | --- |
| 15 | Brown Sound | Brown Sound Modern | Saturated Drive Rhythm | 3.8830 | 0.1053 | 3.9883 |
| 46 | Brown Sound - Vintage Drive Mix | Brown Sound Modern | Saturated Drive Rhythm | 3.8830 | 0.1053 | 3.9883 |
| 76 | Brown Sound - Raw Amp Pass | Brown Sound Modern | Saturated Drive Rhythm | 3.8830 | 0.1053 | 3.9883 |
| 106 | Brown Sound - Grit Stack Take | Brown Sound Modern | Saturated Drive Rhythm | 3.8830 | 0.1053 | 3.9883 |
| 136 | Brown Sound - Classic Crunch Edit | Brown Sound Modern | Saturated Drive Rhythm | 3.8830 | 0.1053 | 3.9883 |

### Largest TRR Failures by L2

| query_idx | Query | TRR retrieved | Baseline retrieved | ΔL2 | TRR L2 | Baseline L2 |
| --- | --- | --- | --- | --- | --- | --- |
| 6 | Acoustic Sim | Acoustic Sim Natural | Studio Clean | -0.3379 | 0.3595 | 0.0215 |
| 39 | Acoustic Sim - Warm Room Take | Acoustic Sim Natural | Studio Clean | -0.3379 | 0.3595 | 0.0215 |
| 69 | Acoustic Sim - Open Chord Mix | Acoustic Sim Natural | Studio Clean | -0.3379 | 0.3595 | 0.0215 |
| 99 | Acoustic Sim - Glass Tone Pass | Acoustic Sim Natural | Studio Clean | -0.3379 | 0.3595 | 0.0215 |
| 129 | Acoustic Sim - Natural Body Edit | Acoustic Sim Natural | Studio Clean | -0.3379 | 0.3595 | 0.0215 |

## TRR vs Wav2Vec-RAG

- Shared paired queries: 211

| Metric | Wins | Losses | Ties | MeanΔ | MedianΔ | P25 | P75 | Min | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| l2 | 43 | 14 | 154 | 0.0561 | 0.0000 | 0.0000 | 0.0000 | -0.3317 | 0.5282 |
| acc@0.1 | 49 | 8 | 154 | 0.0819 | 0.0000 | 0.0000 | 0.0000 | -0.2308 | 0.6439 |
| recall | 50 | 7 | 154 | 0.1242 | 0.0000 | 0.0000 | 0.0000 | -0.2143 | 0.8333 |
| cosine | 43 | 14 | 154 | 0.1012 | 0.0000 | 0.0000 | 0.0000 | -0.1335 | 0.8987 |
| module | 22 | 14 | 175 | 0.0458 | 0.0000 | 0.0000 | 0.0000 | -0.6667 | 0.8000 |

### Largest TRR Gains by L2

| query_idx | Query | TRR retrieved | Baseline retrieved | ΔL2 | TRR L2 | Baseline L2 |
| --- | --- | --- | --- | --- | --- | --- |
| 8 | Math Rock Crystal | Math Rock Crystal Cleans | Telephone EQ | 0.5282 | 0.1945 | 0.7227 |
| 35 | Math Rock Crystal - Alt Take | Math Rock Crystal Cleans | Telephone EQ | 0.5282 | 0.1945 | 0.7227 |
| 65 | Math Rock Crystal - Studio Mix | Math Rock Crystal Cleans | Telephone EQ | 0.5282 | 0.1945 | 0.7227 |
| 95 | Math Rock Crystal - Session Pass | Math Rock Crystal Cleans | Telephone EQ | 0.5282 | 0.1945 | 0.7227 |
| 125 | Math Rock Crystal - Extended Edit | Math Rock Crystal Cleans | Telephone EQ | 0.5282 | 0.1945 | 0.7227 |

### Largest TRR Failures by L2

| query_idx | Query | TRR retrieved | Baseline retrieved | ΔL2 | TRR L2 | Baseline L2 |
| --- | --- | --- | --- | --- | --- | --- |
| 18 | Saturated Rhythm | Saturated Drive Rhythm | Texas Blues | -0.3317 | 0.6068 | 0.2751 |
| 36 | Saturated Rhythm - Alt Take | Saturated Drive Rhythm | Texas Blues | -0.3317 | 0.6068 | 0.2751 |
| 66 | Saturated Rhythm - Studio Mix | Saturated Drive Rhythm | Texas Blues | -0.3317 | 0.6068 | 0.2751 |
| 96 | Saturated Rhythm - Session Pass | Saturated Drive Rhythm | Texas Blues | -0.3317 | 0.6068 | 0.2751 |
| 126 | Saturated Rhythm - Extended Edit | Saturated Drive Rhythm | Texas Blues | -0.3317 | 0.6068 | 0.2751 |

