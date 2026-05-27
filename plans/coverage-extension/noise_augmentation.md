# TRACE Visual Augmentation Strategy

## Source

This note is based on the local paper:

- `plans/coverage-extension/NeurIPS-2025-noisyrollout-reinforcing-visual-reasoning-with-data-augmentation-Paper-Conference.pdf`

## Paper Takeaways

NoisyRollout trains VLM reasoning with mixed clean and distorted-image rollouts.
For each sample, the old policy samples rollouts from both the clean image and a
moderately distorted version of the same image. Rewards and group advantages are
computed over the combined rollout group, but the policy update is conditioned
on the clean image. The distortion strength is annealed down over training.

Useful findings for TRACE:

- Moderate visual distortion improves exploration and out-of-domain robustness.
- A clean/noisy rollout mix works better than simply increasing rollout
  temperature.
- A balanced clean/noisy rollout split was strongest in their ablations.
- Noise annealing matters; fixed strong noise can destabilize training.
- Gaussian noise worked best in their setup; rotation with expansion helped less
  but still helped.
- Cropping and rotation without expansion failed because they removed critical
  visual information.
- Too much noise produced near-zero noisy-rollout rewards and training
  instability.
- Penalizing noisy rollouts directly was harmful because the model learned to
  distinguish clean from noisy inputs instead of improving perception/reasoning.

## Paper Augmentations Vs TRACE

The paper's image augmentations were intentionally simple:

| Augmentation | Paper Result | TRACE Status | TRACE Recommendation |
|---|---|---|---|
| Gaussian image noise | Best tested augmentation; initial noise step around `450-500` worked best in their reported settings, while `600` diverged. | TRACE supports both alpha-blended grayscale grain and true Gaussian pixel noise as coordinate-preserving post-image edits. | Keep both: use Gaussian noise for paper-style robustness experiments and keep current grain/noise as a separate option. |
| Rotation with expansion | Helped, but less than Gaussian noise. | Not currently part of shared post-image noise, and should not be added as blind posthoc noise because it changes coordinates and canvas geometry. | Add only as a render-time/view transform with reprojected evidence, or as answer-only RL augmentation. |
| Cropping | Failed; removed critical information. | Not supported by TRACE post-image noise. | Keep disallowed by default. |
| Rotation without expansion | Failed; corners/content were cut off. | Not supported by TRACE post-image noise. | Keep disallowed by default. |

Important difference from TRACE:

- The paper used distorted images for rollout exploration during RL.
- TRACE can also generate semantically equivalent render views before evidence
  projection, which is safer and richer than pure posthoc distortion.
- For answer-plus-evidence training, coordinate-changing augmentations must
  carry view-specific evidence or stay out of clean-conditioned paired rollout.

## Current TRACE Post-Image Noise

TRACE already supports coordinate-preserving post-image noise in
`trace/core/visual/noise.py`:

- `blur`
- `downsample`
- `directional_blur`
- `edge_soften`
- `unsharp_mask`
- `jpeg`
- `posterize_quantization`
- `noise`
- `gaussian_noise`
- `poisson_noise`
- `salt_pepper_noise`
- `speckle_noise`
- `dust_speckle`
- `brightness_contrast`
- `exposure_shift`
- `gamma_shift`
- `low_contrast_fade`
- `uneven_illumination`
- `screen_or_paper_texture`
- `scanline_texture`
- `subpixel_display_texture`
- `neutral_moire_texture`
- `ink_bleed`
- `local_contrast_jitter`
- `vignette`

The current shared edit sampler applies at most the configured number of edits
after rendering. Existing domain configs generally use one edit when noise
applies. They no longer pin a small `edit_types` allowlist; the shared core
supplies the full coordinate-preserving safe set, while configs keep
domain-specific probabilities and any locally tuned parameter ranges.

Current broad defaults:

| Domain / family | Current probability | Current strength |
|---|---:|---|
| `charts` | `0.5` | full safe edit set; locally tuned light ranges for blur `0.1-0.3`, downsample `0.94-0.98`, JPEG `86-95`, noise alpha `0.008-0.025` |
| `graph` | `0.5` | full safe edit set; locally tuned light ranges for blur `0.1-0.3`, downsample `0.94-0.98`, JPEG `86-95`, noise alpha `0.008-0.025` |
| `geometry` | `0.5` | full safe edit set; locally tuned light-to-medium ranges for blur `0.15-0.4`, downsample `0.92-0.97`, JPEG `82-94`, noise alpha `0.01-0.04` |
| `physics` | `0.5` | full safe edit set; locally tuned light ranges for blur `0.1-0.32`, downsample `0.93-0.98`, JPEG `84-95`, noise alpha `0.008-0.03` |
| `charts/table` | `0.5` | full safe edit set; locally tuned light-to-medium ranges for blur `0.12-0.35`, downsample `0.9-0.97`, JPEG `80-94`, noise alpha `0.01-0.035` |
| `games` | `0.5` | full safe edit set; locally tuned medium ranges for blur `0.15-0.4`, downsample `0.9-0.97`, JPEG `78-94`, noise alpha `0.015-0.045` |
| `three_d` | `0.35` | full safe edit set; locally tuned light ranges for blur `0.1-0.26`, downsample `0.94-0.985`, JPEG `86-95`, noise alpha `0.006-0.024` |
| `pages` | group-specific | many groups use `0.5`; dense text groups such as `infographic`, `process_flow`, `concept_map`, and `schema` use lighter ranges |
| `puzzles` | mostly `0.0`; some groups `0.15` | conservative because crisp grids/cells often matter |
| `icons` / `illustrations` | no broad post-image default | visual variation tends to be render-time or per-object |

Current TRACE does **not** yet implement:

- NoisyRollout-style paired clean/noisy rollout grouping,
- noise annealing during RL,
- production-wide `clean/light/medium/hard` profile sampling and metadata,
- coordinate-aware rotation/affine evidence reprojection.

## Dataset-Time Probability And Strength Recommendation

TRACE's near-term goal is to bake useful visual diversity into generated dataset
records, not to reproduce the paper's RL-time clean/noisy rollout schedule.
NoisyRollout is useful evidence that moderate visual perturbation can improve
robustness, but the TRACE implementation should be a deterministic generation
policy with explicit metadata and review slices.

### Dataset Profiles

Use named augmentation profiles instead of one global noise knob:

| Profile | Default share | Post-image edits | Purpose |
|---|---:|---|---|
| `clean` | `25%` | none, aside from normal render-time style variation | Preserve the canonical task distribution and protect precision-heavy tasks. |
| `light` | `25%` | exactly one mild coordinate-preserving edit | Default robustness mixture for most accepted data. |
| `medium` | `25%` | exactly two mild-to-moderate coordinate-preserving edits | Stronger dataset-time diversity that remains human-answerable. |
| `hard` | `25%` | two or three stronger coordinate-preserving edits | Aggressive robustness slice, monitored closely in review. |

Recommended universal starting point:

- `clean`: `25%`
- `light`: `25%`
- `medium`: `25%`
- `hard`: `25%`

This balanced split should be the default across domains. Many benchmark images are
substantially noisier than current TRACE outputs, so we should not be overly
conservative. Individual task families can still veto or downshift unsafe
profiles if review shows a specific answer/evidence contract breaks.

For text-heavy, tiny-label, color-query, or pixel-precision tasks, start with
the universal split and only downshift unsafe `hard` or `medium` cases if
profile-sliced review shows the task becomes unreadable or semantically
ambiguous.

Example conservative fallback for fragile tasks:

- `clean`: `65-75%`
- `light`: `25-35%`
- `medium`: `0-5%`
- `hard`: `0%`

No domain should start with a higher-noise default than the universal split
until profile-sliced reviews show there is still comfortable headroom.

### Successive Edit Policy

Do not stack many independent corruptions by default.

- `clean`: zero post-image edits.
- `light`: exactly one post-image edit.
- `medium`: exactly two post-image edits.
- `hard`: two or three post-image edits.

For `medium`, choose at most one edit from each bucket:

- acuity: `blur`, `downsample`, `directional_blur`, `edge_soften`, or
  `unsharp_mask`,
- compression: `jpeg` or luminance-only `posterize_quantization`,
- stochastic texture: `gaussian_noise`, `salt_pepper_noise`, or current
  `noise`, plus luminance-preserving `poisson_noise`, `speckle_noise`, and
  `dust_speckle`,
- photometric/illumination: `brightness_contrast`, `low_contrast_fade`,
  `exposure_shift`, `gamma_shift`, `uneven_illumination`,
  `screen_or_paper_texture`, `scanline_texture`, `subpixel_display_texture`,
  `neutral_moire_texture`, `ink_bleed`, `local_contrast_jitter`, or
  `vignette`.

Avoid these default stacks:

- `blur` + `downsample` on dense text, tiny labels, grids, or point-evidence
  tasks,
- strong noise + strong JPEG on OCR-like pages,
- color jitter on tasks where color is queried semantically,
- any geometric transform after evidence projection.

### Initial Strength Buckets

Use conservative ranges first, then tune from review/solve-rate slices.

Suggested coordinate-preserving post-image ranges:

| Edit | `light` | `medium` |
|---|---|---|
| `blur` | radius `0.05-0.18` | radius `0.18-0.35` |
| `directional_blur` | length `3-5`, amount `0.16-0.32` | length `5-9`, amount `0.28-0.50` |
| `downsample` | scale `0.96-0.99` | scale `0.90-0.96` |
| `edge_soften` | amount `0.10-0.22` | amount `0.22-0.42` |
| `unsharp_mask` | radius `0.35-0.75`, percent `50-90` | radius `0.75-1.25`, percent `90-150` |
| `jpeg` | quality `88-97` | quality `76-88` |
| `posterize_quantization` | luminance levels `56-96`, blend `0.08-0.18` | luminance levels `32-56`, blend `0.18-0.34` |
| `noise` alpha | `0.004-0.015` | `0.015-0.04` |
| `gaussian_noise` sigma | `2-6` RGB levels | `6-14` RGB levels |
| `poisson_noise` peak | `900-1500` | `350-900` |
| `salt_pepper_noise` amount | `0.08-0.25%` pixels | `0.25-0.6%` pixels |
| `speckle_noise` sigma | `0.006-0.016` | `0.016-0.04` |
| `dust_speckle` amount | `0.08-0.25%` pixels | `0.25-0.6%` pixels |
| `brightness_contrast` | brightness/contrast within `±4%` | within `±8%` |
| `exposure_shift` | factor within about `±1.5-4.5%` | factor within about `±4.5-8.5%` |
| `gamma_shift` | luminance gamma `0.94-1.06` | luminance gamma `0.88-1.14` |
| `low_contrast_fade` | contrast drop `4-10%`, fade alpha `2-6%` | contrast drop `10-22%`, fade alpha `6-14%` |
| `uneven_illumination` | strength `2.5-7.5%` | strength `7.5-16%` |
| `scanline_texture` | alpha `0.8-1.8%` | alpha `1.8-3.5%` |
| `subpixel_display_texture` | neutral alpha `0.3-0.8%` | neutral alpha `0.8-1.4%` |
| `neutral_moire_texture` | neutral alpha `0.3-0.8%` | neutral alpha `0.8-1.8%` |
| `ink_bleed` | amount `4-10%` | amount `10-20%` |
| `local_contrast_jitter` | strength `1.5-4%` | strength `4-8.5%` |
| `vignette` | edge strength `4-10%` | edge strength `10-22%` |

The locally tuned source ranges already roughly match `light` for charts, graph,
physics, three_d, and dense pages. Games, geometry, and chart table scenes are closer
to light-to-medium. The new policy should make this explicit through
`augmentation_profile` rather than relying only on per-domain raw ranges.

### Supported Extended Post-Image Edits

These are implemented in shared post-image noise and should remain the default
extension set before considering any geometric corruption:

1. `gaussian_noise`
   - Additive per-channel Gaussian noise with clipped RGB output.
   - More directly matches the paper than current alpha-blended grayscale
     `noise`.
2. `brightness_contrast`
   - Mild coordinate-preserving photometric variation.
   - Disable for color-query tasks unless color semantics use metadata and
     visual names remain unchanged.
3. `screen_or_paper_texture`
   - Low-alpha synthetic paper grain or screen texture.
   - Useful for pages/charts/screens without moving evidence.
4. `directional_blur`
   - Mild horizontal or vertical blur that mimics screenshot/camera softness
     without rotating or moving evidence coordinates.
5. `salt_pepper_noise`
   - Sparse black/white speckle as an alternative to Gaussian noise.
   - Keep probabilities low, especially for tiny text and grid cells; even the
     hard profile should cap at `1.5%`, below the old `2.5%` level.
6. `low_contrast_fade`
   - Lowers contrast and blends lightly toward a paper-like background.
   - Useful for scanned pages, charts, geometry, and faint-line stress tests.
7. `vignette`
   - Mild radial edge falloff that preserves coordinates.
   - Keep strength capped so border evidence remains readable.
8. `poisson_noise`
   - Signal-dependent luminance-preserving sensor/shot noise.
   - Useful as a more realistic alternative to plain Gaussian grain.
9. `speckle_noise`
   - Multiplicative achromatic grain applied equally across channels.
   - Preserves hue while adding screen/camera-like texture.
10. `exposure_shift`
   - Mild global brighten/darken factor.
   - Keep ranges conservative because color-query tasks can still be affected by
     very strong exposure changes.
11. `uneven_illumination`
   - Smooth horizontal or vertical light gradient, like scanner/photo lighting.
   - Does not move pixels or evidence.
12. `scanline_texture`
   - Faint neutral horizontal/vertical display lines.
   - Useful for screenshots and screen-like pages.
13. `subpixel_display_texture`
   - Extremely low-alpha neutral pixel-grid texture, not RGB color-channel
     shifting.
   - Avoid colored subpixel fringing for universal use.
14. `posterize_quantization`
   - Mild luminance-only quantization blended back into RGB.
   - Avoids hue/saturation changes while simulating export/compression limits.
15. `dust_speckle`
   - Sparse light/dark small specks, softer than salt-and-pepper noise.
16. `edge_soften`
   - Mild coordinate-preserving line/text edge softening.
17. `ink_bleed`
   - Mild dark-stroke spread based on luminance so hue is preserved.
18. `local_contrast_jitter`
   - Smooth blockwise achromatic contrast variation.
   - Useful for scanner/camera unevenness without moving evidence.
19. `gamma_shift`
   - Mild luminance-curve change applied through the image luminance channel.
   - Simulates display/camera tone response while avoiding hue or white-balance
     shifts.
20. `unsharp_mask`
   - Mild sharpening and edge haloing from screenshots/scans/export pipelines.
   - Complements blur and edge softening.
21. `neutral_moire_texture`
   - Low-alpha achromatic wave/grid interference.
   - Simulates photo-of-screen artifacts without RGB color fringing.

Keep these out of default post-image noise:

- crop,
- translation,
- rotation,
- perspective warp.

If rotation is desired, implement it as a render-time/view transform with
reprojected evidence, not as blind final-image corruption.

## TRACE-Specific Interpretation

TRACE has a better option than pure posthoc image corruption: because images are
synthetically rendered from metadata, many augmentations can be sampled during
scene generation or rendering while preserving the verifier contract.

The central distinction:

- **Render-time augmentation** changes the scene/image before evidence
  projection, then recomputes answer evidence from the same trace.
- **Post-image noise** changes the final image after evidence projection and
  must preserve pixel coordinates.

Render-time augmentation should be the primary TRACE strategy. Post-image noise
should remain a secondary, mild, coordinate-preserving robustness layer.

## Recommended Universal Policy

### 1. Separate Semantic Instance From Render View

Each training item should conceptually have:

- a semantic scene/query/verifier spec,
- one or more render views of that same semantic instance,
- per-view projected evidence,
- per-view augmentation metadata.

The semantic answer remains unchanged across views, but evidence coordinates may
change if the render view changes geometry, layout, camera, or scale.

Suggested metadata:

- `semantic_instance_id`
- `render_view_id`
- `augmentation_profile`
- `augmentation_strength`
- `augmentation_spec`
- `coordinate_preserving`
- `evidence_projected_for_view`

### 2. Prefer Render-Time Domain Randomization

Use synthetic renderer controls before applying post-image noise:

- layout jitter,
- object/mark/edge style variation,
- font and typography variation,
- line width and stroke variation,
- palette/theme variation,
- background and paper texture variation,
- chart/page/graph renderer idioms,
- camera/viewpoint and lighting for 3D,
- controlled clutter and distractor text,
- controlled occlusion that does not hide required evidence.

These are usually better than blind image corruption because they remain
metadata-aware and can be tuned per task family.

### 3. Keep Post-Image Noise Mild And Coordinate-Preserving

Allowed post-image edits:

- blur and edge softening/sharpening,
- downsample/resample,
- JPEG compression and luminance-only quantization,
- achromatic pixel/sensor/speckle noise,
- neutral paper/screen/scanline/moire textures,
- luminance-preserving exposure, gamma, contrast, illumination, ink, and
  vignette changes.

Disallowed as post-image edits by default:

- crop,
- translation,
- rotation,
- perspective warp,
- padding changes,
- any operation that moves pixels without updating evidence.

If a geometric transform is needed, implement it as a render-time variant or a
post-transform with explicit coordinate transforms and reprojected evidence.

### 4. Use Strength Buckets Rather Than One Global Noise Knob

Define common strength buckets that domains can map to their own parameters:

- `clean`: no post-image noise; normal renderer variation only.
- `light`: subtle blur/compression/grain; should not affect human readability.
- `medium`: visible but non-destructive degradation; useful for robustness and
  stress coverage.
- `hard`: stronger but still coordinate-preserving degradation; include by
  default when profile-sliced review shows it remains answerable.

Initial policy:

- Default dataset generation should use a balanced `clean/light/medium/hard`
  mixture after profile-sliced review.
- `medium` and `hard` should stay in the accepted mixture only while human
  review and solve-rate slices show that the task remains answerable.

### 5. Treat RL-Time Noisy Rollout As A Later Training-System Option

NoisyRollout-style paired rollout is not the near-term data-generation goal.
If we revisit it later, TRACE evidence outputs add one important constraint:

- If the model outputs **answer only**, noisy render-time views can be mixed
  freely as long as the answer is unchanged.
- If the model outputs **answer plus evidence coordinates**, clean-conditioned
  updates should only use noisy rollouts whose evidence coordinates are still
  valid for the clean image. That generally means coordinate-preserving
  post-image noise.
- If a noisy render-time view changes coordinates, treat it as a separate
  training sample with its own evidence, or modify the RL objective/reward
  plumbing to keep evidence coordinates tied to the input view used for that
  rollout.

Future training-system rule:

- For answer-and-evidence RL, use clean plus coordinate-preserving noisy views.
- For answer-only RL, allow broader render-time augmented views.
- For supervised or offline data export, allow multiple render views as separate
  records because each record carries its own projected evidence.

### 6. Do Not Bake Heavy Noise Uniformly Into The Dataset

The paper's instability result still matters: too much distortion can produce
near-zero-reward examples. TRACE should avoid a static “everything is noisy”
dataset.

For dataset generation:

- Store the augmentation strength/profile in metadata.
- Keep clean examples in the exported mixture.
- Keep profile balance explicit so noisy views do not silently dominate.
- Avoid oversampling noisy views beyond the reviewed universal split if clean
  distribution performance regresses.

## Candidate Universal Augmentation Families

### Coordinate-Preserving Post-Image Noise

Applies broadly, with task exceptions:

- Gaussian/pixel grain,
- mild blur,
- mild JPEG compression,
- mild downsample/upsample,
- subtle paper/screen texture,
- subtle brightness/contrast variation.

### Render-Time Visual Randomization

Applies broadly, because evidence can be recomputed:

- background style,
- palette/theme,
- font family/weight/size within readability constraints,
- stroke width,
- marker shape,
- line/edge routing style,
- label placement,
- layout jitter within margins,
- distractor text or non-answer objects,
- controlled occlusion and overlap caps,
- shadows, depth cues, and anti-aliasing choices.

### Domain-Specific Render-Time Examples

- Charts: chart wrappers, unusual chart idioms, tick density, label rotation,
  direct labels, legends, callouts.
- Graph: layout family, edge curvature, node shapes, label type, edge style,
  background and annotation treatment.
- Pages: document density, page chrome, cards/tables/lists, GUI themes, sidebar
  and dialog variants, source notes and footnotes.
- Geometry/physics: graph-paper or plain-paper style, line thickness, label
  placement, controlled construction marks, non-semantic distractors.
- Games/puzzles/cell-board scenes: board theme, piece style, mild camera/screen texture,
  non-semantic UI chrome; avoid ambiguity in grid cells.
- 3D: camera pose, lighting, material, shadows, background, object style.
- Icons/illustrations: per-object tint/noise before compositing, controlled
  clutter, pose/style variants.

## Exceptions And Caution Zones

Use lighter or no augmentation only when profile-sliced review shows a concrete
failure mode, such as:

- the task queries exact colors and color jitter could change semantics,
- tiny text or dense labels are already near readability limits,
- point evidence needs high pixel precision,
- graph-paper measurement depends on exact grid visibility,
- a puzzle/grid task relies on crisp cell boundaries,
- occlusion order or visibility is itself the semantic target,
- evidence boxes are very small,
- the solve rate is already near acceptance thresholds,
- augmentation introduces alternate valid answers.

Do not auto-relax task constraints to survive augmentation. If an augmented view
is not answerable, reject that view.

## Review And Acceptance Policy

Every new augmentation family should be reviewed at three levels:

- `clean`: current expected task behavior.
- `light`: intended default robustness mixture.
- `medium`: RL exploration/stress view.

Suggested gates:

- clean solve-rate/review must remain unchanged,
- light augmented samples should pass normal review,
- medium samples should be reviewed separately and used only where answerability
  and evidence alignment are clear,
- task review sheets should record augmentation profile/strength,
- solve-rate summaries should be sliceable by augmentation profile.

## Implementation Plan

1. Add a shared augmentation policy layer that names strength buckets and
   records `augmentation_profile` in `render_spec`.
2. Keep existing `trace/core/visual/noise.py` for coordinate-preserving
   post-image edits, but normalize configs around `clean/light/medium/hard`.
3. Add render-time augmentation hooks per domain where they already have style
   samplers; avoid forcing one renderer API onto every task at once.
4. Update review tooling to sample and report augmentation profiles.
5. Start with domains and scene families that already tolerate visual variation well:
   charts, graph, pages, geometry, physics, chart tables, games, and 3D.
6. Keep icons, illustrations, tiny-grid puzzles, and color-query tasks opt-in
   until their local evidence/readability contracts are checked.
7. Keep RL-time paired clean/noisy rollout support out of scope for the first
   implementation; revisit only after dataset-time augmentation profiles and
   review slices are stable.

## Near-Term Recommendation

Before implementing chart-specific visual variety, define the shared
augmentation profile metadata and review slices. Then chart renderer work can
emit its variations through the same policy rather than inventing chart-only
noise controls.
