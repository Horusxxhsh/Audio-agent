# Protocol-A Derived Analysis

- Input CSV: `Experiments/AblationStudies/protocolA_audio_grouped_per_query_metrics.csv`
- Paired query count (TRR rows): 204
- Unique `query_name` labels in TRR rows: 203
- Pairing is performed by `query_idx`; one query label is reused in the CSV, so label-level uniqueness is lower than row count.

## TRR vs CLAP

- Shared paired queries: 201

| Metric | Wins | Losses | Ties | MeanΔ | MedianΔ | P25 | P75 | Min | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| l2 | 130 | 54 | 17 | 14.1460 | 0.0658 | -0.0038 | 36.0774 | -57.3198 | 71.6821 |
| acc@0.1 | 104 | 66 | 31 | 0.0640 | 0.0099 | -0.0476 | 0.1905 | -0.7356 | 0.8125 |
| recall | 103 | 58 | 40 | 0.0600 | 0.0385 | -0.0588 | 0.2222 | -0.9286 | 0.8889 |
| cosine | 124 | 60 | 17 | 0.2503 | 0.0082 | -0.0011 | 0.8535 | -0.9362 | 1.0765 |
| module | 79 | 39 | 83 | 0.0781 | 0.0000 | 0.0000 | 0.4000 | -0.7143 | 0.7500 |

### Largest TRR Gains by L2

| query_idx | Query | TRR retrieved | Baseline retrieved | ΔL2 | TRR L2 | Baseline L2 |
| --- | --- | --- | --- | --- | --- | --- |
| 132 | Modular Hybrid Drift | Prepared Guitar Static | Ethereal Wave | 71.6821 | 0.1178 | 71.7999 |
| 29 | Smooth Jazz Lead Velvet | Middle Eastern Sahara | Japanese Ambient | 71.4698 | 0.0000 | 71.4698 |
| 88 | Overtone Drone Glitch | Latin Rock Fusion Moonrise | Japanese Ambient | 69.7621 | 1.7082 | 71.4703 |
| 195 | Shoegaze Wall Static | Nashville Session Sunrise | Post-Britpop | 69.6723 | 1.7101 | 71.3823 |
| 182 | Bluegrass Flatpick Rambler | Raw Black Metal Onslaught | Cinematic Trailer | 69.0382 | 0.4729 | 69.5110 |

### Largest TRR Failures by L2

| query_idx | Query | TRR retrieved | Baseline retrieved | ΔL2 | TRR L2 | Baseline L2 |
| --- | --- | --- | --- | --- | --- | --- |
| 48 | Talk Box Funk | Schlager Pop | Drum and Bass Synth | -57.3198 | 61.1606 | 3.8408 |
| 110 | Berlin Techno | Chromatic Jazz | Multicultural Fusion | -55.2634 | 60.1387 | 4.8754 |
| 185 | Qawwali Devotional | French Touch | Queercore DIY | -50.9122 | 51.4330 | 0.5208 |
| 94 | Lo-Fi House | Soft Grunge | Reverse Ambient Drift | -50.7864 | 54.8413 | 4.0549 |
| 13 | Wah-Wah Rock | Shimmer Reverb | Auto-Wah Funk - Velvet Groove Version | -49.4902 | 105.6809 | 56.1908 |

## TRR vs FeatureNN-RAG

- Shared paired queries: 204

| Metric | Wins | Losses | Ties | MeanΔ | MedianΔ | P25 | P75 | Min | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| l2 | 130 | 49 | 25 | 11.2146 | 0.2206 | 0.0000 | 26.6980 | -56.3859 | 72.1369 |
| acc@0.1 | 114 | 57 | 33 | 0.0971 | 0.0476 | -0.0256 | 0.2394 | -0.6364 | 0.7917 |
| recall | 103 | 57 | 44 | 0.0995 | 0.0385 | -0.0556 | 0.2800 | -0.9286 | 1.0000 |
| cosine | 122 | 57 | 25 | 0.2769 | 0.0081 | -0.0007 | 0.8409 | -0.9359 | 1.0719 |
| module | 86 | 40 | 78 | 0.0917 | 0.0000 | 0.0000 | 0.3333 | -0.7143 | 0.8889 |

### Largest TRR Gains by L2

| query_idx | Query | TRR retrieved | Baseline retrieved | ΔL2 | TRR L2 | Baseline L2 |
| --- | --- | --- | --- | --- | --- | --- |
| 65 | Sub-Bass Drone | Hauntology Library | Dark Ambient Drone Prism | 72.1369 | 0.6874 | 72.8242 |
| 101 | Shoegaze Drone | Floating Synth | Modular Hybrid Flux | 70.3057 | 1.2174 | 71.5231 |
| 195 | Shoegaze Wall Static | Nashville Session Sunrise | Ethereal Wave | 70.0780 | 1.7101 | 71.7880 |
| 192 | Ambient Guitar Loop | Post-Britpop | Lo-Fi Bedroom Pop Dream | 67.8665 | 1.8636 | 69.7300 |
| 84 | Spectral Freeze Drift | Celtic Folk Sahara | Ritual Ambient | 67.2165 | 1.7966 | 69.0130 |

### Largest TRR Failures by L2

| query_idx | Query | TRR retrieved | Baseline retrieved | ΔL2 | TRR L2 | Baseline L2 |
| --- | --- | --- | --- | --- | --- | --- |
| 181 | Rave Hardcore | Dark Ambient | Melodic Death Metal | -56.3859 | 56.6368 | 0.2509 |
| 102 | Urban Cowboy | Fender Rhodes Jazz | Sonic Youth Noise | -53.0948 | 56.7918 | 3.6970 |
| 76 | Stripped Acoustic | Piano Ballad | Country Telecaster Outlaw | -52.8245 | 56.4782 | 3.6537 |
| 110 | Berlin Techno | Chromatic Jazz | West Coast Hip Hop | -52.5144 | 60.1387 | 7.6243 |
| 148 | Phased Synth | London Jazz | Nightcore Speed | -51.6878 | 59.1761 | 7.4883 |

## TRR vs Text-RAG

- Shared paired queries: 204

| Metric | Wins | Losses | Ties | MeanΔ | MedianΔ | P25 | P75 | Min | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| l2 | 117 | 69 | 18 | 16.1238 | 0.1248 | -0.1482 | 47.1945 | -57.3623 | 72.2040 |
| acc@0.1 | 97 | 80 | 27 | 0.0453 | 0.0000 | -0.0952 | 0.1655 | -0.6667 | 0.7692 |
| recall | 97 | 68 | 39 | 0.0628 | 0.0000 | -0.0800 | 0.1667 | -0.7222 | 0.8182 |
| cosine | 117 | 69 | 18 | 0.3304 | 0.0311 | -0.0168 | 0.9567 | -0.7853 | 0.9972 |
| module | 73 | 56 | 75 | 0.0595 | 0.0000 | -0.1111 | 0.4444 | -0.7143 | 0.8571 |

### Largest TRR Gains by L2

| query_idx | Query | TRR retrieved | Baseline retrieved | ΔL2 | TRR L2 | Baseline L2 |
| --- | --- | --- | --- | --- | --- | --- |
| 65 | Sub-Bass Drone | Hauntology Library | Studio Clean | 72.2040 | 0.6874 | 72.8914 |
| 59 | Ghostly Pad | Rainforest Ambient | Studio Clean | 70.6486 | 0.1251 | 70.7736 |
| 101 | Shoegaze Drone | Floating Synth | Studio Clean | 70.3506 | 1.2174 | 71.5679 |
| 195 | Shoegaze Wall Static | Nashville Session Sunrise | Shoegaze Wall | 70.2720 | 1.7101 | 71.9821 |
| 142 | Chamber Pop Dream | Motown Soul Philly | Dream Pop Wash | 68.7643 | 0.1543 | 68.9185 |

### Largest TRR Failures by L2

| query_idx | Query | TRR retrieved | Baseline retrieved | ΔL2 | TRR L2 | Baseline L2 |
| --- | --- | --- | --- | --- | --- | --- |
| 48 | Talk Box Funk | Schlager Pop | Studio Clean | -57.3623 | 61.1606 | 3.7983 |
| 76 | Stripped Acoustic | Piano Ballad | Studio Clean | -52.8607 | 56.4782 | 3.6175 |
| 94 | Lo-Fi House | Soft Grunge | Studio Clean | -51.1435 | 54.8413 | 3.6978 |
| 13 | Wah-Wah Rock | Shimmer Reverb | Studio Clean | -43.6487 | 105.6809 | 62.0322 |
| 181 | Rave Hardcore | Dark Ambient | Studio Clean | -34.7080 | 56.6368 | 21.9288 |

## TRR vs Wav2Vec-RAG

- Shared paired queries: 204

| Metric | Wins | Losses | Ties | MeanΔ | MedianΔ | P25 | P75 | Min | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| l2 | 125 | 40 | 39 | 15.7730 | 0.1238 | 0.0000 | 38.3635 | -51.6878 | 76.2671 |
| acc@0.1 | 107 | 46 | 51 | 0.0918 | 0.0312 | 0.0000 | 0.2389 | -0.7356 | 0.7692 |
| recall | 102 | 49 | 53 | 0.1091 | 0.0192 | 0.0000 | 0.2500 | -0.9286 | 0.9091 |
| cosine | 121 | 44 | 39 | 0.2956 | 0.0142 | 0.0000 | 0.8385 | -0.9318 | 1.0693 |
| module | 84 | 43 | 77 | 0.1008 | 0.0000 | 0.0000 | 0.3500 | -0.7143 | 0.8000 |

### Largest TRR Gains by L2

| query_idx | Query | TRR retrieved | Baseline retrieved | ΔL2 | TRR L2 | Baseline L2 |
| --- | --- | --- | --- | --- | --- | --- |
| 79 | 3-Chord Punk | Distorted Cassette | Britpop Jangle | 76.2671 | 3.9496 | 80.2167 |
| 65 | Sub-Bass Drone | Hauntology Library | Dark Ambient Drone Flux | 72.1587 | 0.6874 | 72.8461 |
| 191 | Japanese Enka Sunset | Middle Eastern Andean | Tangerine Dream Style | 71.9205 | 0.1385 | 72.0590 |
| 84 | Spectral Freeze Drift | Celtic Folk Sahara | Space Ambient | 70.8148 | 1.7966 | 72.6114 |
| 101 | Shoegaze Drone | Floating Synth | Modular Hybrid Flux | 70.3057 | 1.2174 | 71.5231 |

### Largest TRR Failures by L2

| query_idx | Query | TRR retrieved | Baseline retrieved | ΔL2 | TRR L2 | Baseline L2 |
| --- | --- | --- | --- | --- | --- | --- |
| 148 | Phased Synth | London Jazz | Nightcore Speed | -51.6878 | 59.1761 | 7.4883 |
| 13 | Wah-Wah Rock | Shimmer Reverb | Auto-Wah Funk Rhythm | -49.4903 | 105.6809 | 56.1906 |
| 181 | Rave Hardcore | Dark Ambient | Drum and Bass Beat | -34.7370 | 56.6368 | 21.8998 |
| 102 | Urban Cowboy | Fender Rhodes Jazz | Reggae Dubplate | -30.9581 | 56.7918 | 25.8337 |
| 202 | Chinese Guzheng Ambient | Horror Movie Score | Bell Choir Ambient | -20.5573 | 21.5778 | 1.0205 |

