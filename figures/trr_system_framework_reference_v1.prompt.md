# TRR System Framework Reference v1

## Delivery contract

- Source of truth: the user-approved figure brief in this Codex task.
- Figure role: distinguish the evaluated offline retrieval protocol from the separately implemented real-time DSP chain.
- Raster reference: `figures/trr_system_framework_reference_v1.png`.
- Output mode: built-in `image_gen`.
- Reference image role: `/home/xyh/.codex/skills/draw-academic-framework/assets/style-reference.png` was used only as a style and composition reference.
- Publication boundary: this PNG is a visual design reference and must be manually redrawn and typeset as vector artwork before submission.

## One-sentence message

An evaluated offline TRR retrieval protocol maps an audio reference to an editable parameter vector, while a separately implemented real-time plugin chain exists below and the deployment bridge between them remains unvalidated.

## Arrow ledger

- Audio Reference -> Cached TRR Descriptor | data flow | solid charcoal arrow.
- Optional Text Query -> Cached TRR Descriptor | optional scope input | dashed neutral arrow.
- Cached TRR Descriptor -> Cosine Top-K Retrieval | procedure | solid charcoal arrow.
- Cosine Top-K Retrieval -> EPR-K5 Projection | procedure | solid charcoal arrow.
- EPR-K5 Projection -> Validity Check | procedure | vertical solid charcoal arrow.
- Validity Check -> Editable Parameter Vector | certified output flow | vertical solid charcoal arrow.
- Dry Guitar Input -> Compressor -> Equaliser -> Screamer -> Driver -> Delay -> Chorus -> Phaser -> Flanger -> Reverb -> Processed Audio Output | real-time DSP procedure | horizontal solid arrows.
- Upper panel -/- lower panel | unvalidated deployment relation | dashed barrier with no crossing arrow.

## Exact visible labels

- `(a) Evaluated offline protocol`
- `Audio Reference`
- `Cached TRR Descriptor`
- `Gram of mid-level Wav2Vec2`
- `Cosine Top-K Retrieval`
- `1,063-preset KB`
- `EPR-K5 Projection`
- `softmax blend`
- `Validity Check`
- `range / finite / On-Off`
- `Editable Parameter Vector`
- `offline output`
- `Optional Text Query`
- `(audio reference optional; text not used in the reported objective protocol)`
- `deployment bridge not validated`
- `(b) Implemented real-time plugin`
- `Dry Guitar Input`
- `Compressor`
- `Equaliser`
- `Screamer`
- `Driver`
- `Delay`
- `Chorus`
- `Phaser`
- `Flanger`
- `Reverb`
- `Processed Audio Output`
- `The nine modules form a simplified subset of the implemented chain, which also includes input gating, gain staging, wave-shaping, bit-crushing, cabinet, and limiter stages.`

## Final generation prompt

```text
Use case: infographic-diagram
Asset type: high-resolution academic systems-framework design reference for an IEEE Transactions on Multimedia full-width 7.16-inch paper figure.
Input image: Image 1 is a STYLE AND COMPOSITION REFERENCE ONLY. Reuse its crisp icon-first stage-card grammar, unified line-icon family, strong alignment, and technical density. Do not copy any of its subject matter, words, symbols, colors verbatim, or conclusions.

Primary request:
Create a refined, highly technical, publication-style system framework figure for “Texture Resonance Retrieval for Guitar-Effect Preset Selection.” The reader must understand in five seconds that an evaluated offline retrieval protocol converts an audio reference into an editable parameter vector, while a separately implemented real-time guitar-effect chain exists below; the deployment bridge between them has NOT been validated.

Scientific and visual contract:
- Pure opaque white background, wide landscape approximately 2.2:1, intended for double-column IEEE layout.
- Two large horizontal stage panels separated by a full-width neutral dashed barrier.
- Upper panel title, verbatim: “(a) Evaluated offline protocol”
- Lower panel title, verbatim: “(b) Implemented real-time plugin”
- Center barrier label, verbatim and lowercase: “deployment bridge not validated”
- Make the non-transfer boundary visually impossible to misread: use a subtle broken-link or interrupted-connector symbol at the center of the dashed barrier. NO arrow, cable, feedback loop, or visual path may cross between the upper and lower panels.

Upper panel structure:
1. A true left-to-right solid-arrow main flow across the upper row:
“Audio Reference” -> “Cached TRR Descriptor” -> “Cosine Top-K Retrieval” -> “EPR-K5 Projection”
2. From “EPR-K5 Projection”, a solid orthogonal arrow goes vertically down to “Validity Check”, then vertically down to “Editable Parameter Vector”.
3. Below the descriptor card, add a dashed neutral scope arrow pointing upward from “Optional Text Query” to “Cached TRR Descriptor”.
4. Place this exact small note beside the optional input:
“(audio reference optional; text not used in the reported objective protocol)”
5. Exact qualifiers:
- under “Cached TRR Descriptor”: “Gram of mid-level Wav2Vec2”
- under “Cosine Top-K Retrieval”: “1,063-preset KB”
- under “EPR-K5 Projection”: “softmax blend”
- under “Validity Check”: “range / finite / On-Off”
- under “Editable Parameter Vector”: “offline output”

Upper-panel icon roles, all in one coherent thin rounded line-icon family:
- Audio Reference: guitar waveform entering a compact audio document.
- Cached TRR Descriptor: a small encoder stack feeding a symmetric Gram-matrix heatmap grid; make the second-order matrix idea visually explicit and technical.
- Cosine Top-K Retrieval: magnifier over a ranked preset list with similarity bars and top-K highlight.
- EPR-K5 Projection: five weighted nodes converging into a mixer/sliders vector; visibly communicate soft weighted blending.
- Validity Check: shield with checkmark plus miniature range brackets, finite-value dots, and On/Off toggle.
- Editable Parameter Vector: aligned parameter sliders/knobs with a clean output-vector bracket.
- Optional Text Query: small text bubble/document icon, secondary and grey.

Lower panel:
A single uninterrupted horizontal solid-arrow DSP chain in this exact order, with exactly eleven compact cards:
“Dry Guitar Input” -> “Compressor” -> “Equaliser” -> “Screamer” -> “Driver” -> “Delay” -> “Chorus” -> “Phaser” -> “Flanger” -> “Reverb” -> “Processed Audio Output”
The first and last cards are stronger endpoint cards; the nine inner cards share one modular effect-pedal/signal-processing grammar. Give every inner module a distinct tiny technical line icon:
Compressor = gain-reduction meter; Equaliser = multiband response sliders; Screamer = overdrive waveform; Driver = clipped transfer curve; Delay = repeated echoes; Chorus = paired modulated waves; Phaser = phase-shifted circles/waves; Flanger = comb-filter response; Reverb = room impulse decay.
Below the chain, typeset this exact note in two clean lines:
“The nine modules form a simplified subset of the implemented chain, which also includes input gating, gain staging, wave-shaping, bit-crushing, cabinet, and limiter stages.”

Visual grammar:
- More precise and technical than a generic flowchart: compact scientific line icons, small matrix cells, waveform traces, similarity bars, weight nodes, vector brackets, sliders, meters, response curves, and signal-flow arrows.
- Stage cards with subtle very-light blue and very-light amber-grey tints, flat opaque fills, dark charcoal text and arrows, teal/blue for offline representation and validity, restrained orange only for real-time DSP identity, neutral grey for scope boundary.
- Grayscale-safe: differentiate by position, labels, border style, icon motif, and line style, never by color alone.
- Helvetica/Arial-like sans-serif; bold panel heading, medium action label, small qualifier.
- Thin 1.5–2 px optical strokes at this design scale, rounded caps and joins, modest arrowheads, even corner radii, strict baseline grid, generous outer margin, tightly controlled internal padding.
- Use nested icon/action cards inside the two outer panels, with professional IEEE figure density and clean whitespace.
- Flat vector-style scientific infographic; no photorealism, no 3D, no shadows, no glassmorphism, no decorative gradients, no neon, no glossy effects, no bitmap textures, no watermark.
- All visible text must be English and rendered verbatim. Do not invent headings, equations, metrics, legends, abbreviations, or results.

Critical prohibitions:
- Do NOT imply a validated end-to-end online closed loop.
- Do NOT connect the two panels.
- Do NOT reorder any DSP module.
- Equaliser must be before Screamer. Delay must be before Chorus.
- Do NOT show words copied from the reference image. In particular, never show “GATE”, “artifact”, “archived”, “frozen”, “legacy”, “local”, “in-repo”, or “pipeline”.
- Do not add people, guitars as decorative illustrations, scenery, or marketing elements.
- Preserve crisp traceable boundaries so a designer can manually redraw every card, icon, and connector as vector artwork.
```

## Known limitation

The separator glyph resembles a linked-chain symbol more than an explicitly broken link. The text boundary and lack of a crossing arrow remain correct, but the next revision should replace only this glyph with an unmistakable broken-link mark.
