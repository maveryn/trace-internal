# Trace Related-Work Inventory

This directory supports the Trace manuscript's related-work analysis. It is
not capped at a fixed number of papers. Local PDFs are retained for the works
that require close comparison; the broader inventory below records additional
primary sources that should be covered by the manuscript.

## Scope

The multimodal RL-data inventory is intended to be comprehensive through
2026-07-14 under the following inclusion rule:

- the model consumes images and language;
- the work performs RL, RFT, or RLVR post-training of a VLM policy; and
- the work introduces, synthesizes, reconstructs, or materially curates the
  policy-training examples or their verifiable targets.

The core inventory excludes text-only reasoning, image-generation policies,
video-only systems, embodied or GUI agents, preference and safety alignment,
reward-model-only datasets, benchmark-only releases, and SFT-only datasets.
Those areas may still be cited when they establish a method or design lineage
relevant to Trace.

A paper is not included merely because its authors mirror the examples used in
their experiments. Data or environment construction, synthesis,
transformation, selection, or mixture design must be a stated contribution to
the policy post-training method.

The inventory was cross-checked against the primary paper and project pages,
the Reinforced MLLM survey, and the maintained multimodal-RL paper lists from
OpenDILab and Awesome RL-based Reasoning MLLMs. Completeness is date-bounded:
new preprints after the date above require a new literature pass.

## Local Deep-Reading Set

| Local file | Paper | Why it is read closely |
|---|---|---|
| `clevr_1612.06890.pdf` | [CLEVR](https://arxiv.org/abs/1612.06890) | Canonical synthetic scenes, functional programs, and controlled question families. |
| `task_me_anything_2406.11775.pdf` | [Task Me Anything](https://arxiv.org/abs/2406.11775) | Extensible taxonomy and programmatic multimodal task generation. |
| `puzzlevqa_2403.13315.pdf` | [PuzzleVQA](https://arxiv.org/abs/2403.13315) | Procedural abstract visual reasoning and concept-level diagnosis. |
| `visual_rft_2503.01785.pdf` | [Visual-RFT](https://arxiv.org/abs/2503.01785) | Early visual RFT with task-specific verifiable rewards, including grounding rewards. |
| `vision_r1_2503.06749.pdf` | [Vision-R1](https://arxiv.org/abs/2503.06749) | Large cold-start multimodal reasoning data followed by rule-based RL. |
| `lmm_r1_2503.07536.pdf` | [LMM-R1](https://arxiv.org/abs/2503.07536) | Two-stage rule-based RL for compact multimodal models. |
| `curr_reft_2503.07065.pdf` | [Curr-ReFT](https://arxiv.org/abs/2503.07065) | Curriculum construction and rejected-sampling self-improvement for multimodal post-training. |
| `r1_onevision_2503.10615.pdf` | [R1-Onevision](https://arxiv.org/abs/2503.10615) | Cross-modal formalization and mixed multimodal reasoning data. |
| `reason_rft_2503.20752.pdf` | [Reason-RFT](https://arxiv.org/abs/2503.20752) | Reconstructed visual counting, structure, and spatial-transformation data. |
| `vlm_r1_2504.07615.pdf` | [VLM-R1](https://arxiv.org/abs/2504.07615) | Stable R1-style training and released visual RL data. |
| `sota_with_less_2504.07934.pdf` | [SoTA with Less](https://arxiv.org/abs/2504.07934) | MCTS-guided selection of compact, appropriately difficult visual RFT data. |
| `noisyrollout_2504.13055.pdf` | [NoisyRollout](https://arxiv.org/abs/2504.13055) | Image perturbation and annealing as policy-exploration data augmentation. |
| `game_rl_2505.13886.pdf` | [Game-RL](https://arxiv.org/abs/2505.13886) | Code-to-task synthesis of verifiable game reasoning data. |
| `jigsaw_r1_2505.23590.pdf` | [Jigsaw-R1](https://arxiv.org/abs/2505.23590) | Narrow procedural puzzle environment used to isolate visual RL behavior. |
| `visualsphinx_2505.23977.pdf` | [VisualSphinx](https://arxiv.org/abs/2505.23977) | Large-scale rule-to-image synthesis of visual logic puzzles for RL. |
| `modomodo_2505.24871.pdf` | [MoDoMoDo](https://arxiv.org/abs/2505.24871) | Explicit study of multi-domain multimodal RL data mixtures. |
| `vigorl_2505.23678.pdf` | [ViGoRL](https://arxiv.org/abs/2505.23678) | Coordinate-grounded reasoning and visual-search supervision. |
| `synthrl_2506.02096.pdf` | [SynthRL](https://arxiv.org/abs/2506.02096) | Difficulty-aware synthesis and verification of harder visual RL questions. |
| `rap_2506.04755.pdf` | [RAP](https://arxiv.org/abs/2506.04755) | Causal and attention-based selection of high-value multimodal reasoning data. |
| `revisual_r1_2506.04207.pdf` | [ReVisual-R1](https://arxiv.org/abs/2506.04207) | GRAMMAR data curation and staged multimodal/text reinforcement learning. |
| `wethink_2506.07905.pdf` | [WeThink](https://arxiv.org/abs/2506.07905) | Scalable QA synthesis and a 120K general-purpose multimodal reasoning collection. |
| `vision_matters_2506.09736.pdf` | [Vision Matters](https://arxiv.org/abs/2506.09736) | Visual perturbations that alter the effective policy-training distribution. |
| `vicrit_2506.10128.pdf` | [ViCrit](https://arxiv.org/abs/2506.10128) | Synthetic, exactly verifiable visual-error localization as an RL proxy task. |
| `deepvision_2602.16742.pdf` | [DeepVision-103K](https://arxiv.org/abs/2602.16742) | Broad-coverage, visually diverse mathematical data constructed for multimodal RLVR. |
| `vision_g1_2508.12680.pdf` | [Vision-G1](https://arxiv.org/abs/2508.12680) | Broad RL-ready visual-reasoning mixture with influence-based filtering and curriculum design. |
| `rewardmap_2510.02240.pdf` | [RewardMap](https://arxiv.org/abs/2510.02240) | ReasonMap-Plus and staged data for fine-grained transit-map reasoning. |
| `cogs_2510.15040.pdf` | [COGS](https://arxiv.org/abs/2510.15040) | Factor decomposition and recomposition for chart and webpage RL data synthesis. |
| `vero_2604.04917.pdf` | [Vero](https://arxiv.org/abs/2604.04917) | Broad open visual RL data mixture, task-routed rewards, and controlled ablations. |
| `ivgr_2605.31096.pdf` | [iVGR](https://arxiv.org/abs/2605.31096) | Evidence that mandatory explicit grounding can interfere with answer prediction. |
| `tron_2606.01599.pdf` | [TRON](https://arxiv.org/abs/2606.01599) | Closest concurrent environment-level work: 520 online visual generator--verifier environments with ability buckets, difficulty ladders, and substrate audits. |
| `worldbench_2606.06538.pdf` | [WorldBench](https://arxiv.org/abs/2606.06538) | Broad visual-concept coverage and taxonomy-guided benchmark construction. |

Sphinx source and OpenThoughts are kept in their existing paper workspaces and
remain part of the close-reading set.

## Dataset-Bearing Multimodal RL Papers

### Early General and Task-Specific Recipes

| Paper | Data contribution relevant to Trace |
|---|---|
| [Visual-RFT](https://arxiv.org/abs/2503.01785) | Few-shot visual classification, detection, and grounding data paired with task-specific rewards. |
| [URSA](https://arxiv.org/abs/2501.04686) | MMathCoT-1M and DualMath-1.1M for multimodal mathematics, process supervision, and PS-GRPO. |
| [Vision-R1](https://arxiv.org/abs/2503.06749) | Automatically constructed multimodal chain-of-thought cold-start data and visual-math RL data. |
| [MM-Eureka](https://arxiv.org/abs/2503.07365) | Open rule-based multimodal RL pipeline and training data. |
| [LMM-R1](https://arxiv.org/abs/2503.07536) | Two-stage rule-based training data spanning text and multimodal reasoning. |
| [R1-Onevision](https://arxiv.org/abs/2503.10615) | Cross-modal formalization data for generalized multimodal reasoning. |
| [Seg-Zero](https://arxiv.org/abs/2503.06520) | Reinforcement-only reasoning segmentation data with positional targets and segmentation rewards. |
| [OpenVLThinker](https://arxiv.org/abs/2503.17352) | Iteratively regenerated SFT data interleaved with visual-reasoning RL cycles. |
| [Reason-RFT](https://arxiv.org/abs/2503.20752) | Reconstructed visual counting, structure-perception, and spatial-transformation data. |
| [MAYE](https://arxiv.org/abs/2504.02587) | Transparent RL framework with released visual-reasoning training data. |
| [CrowdVLM-R1](https://arxiv.org/abs/2504.03724) | Crowd-counting data for fuzzy group-relative visual rewards. |
| [VLM-R1](https://arxiv.org/abs/2504.07615) | Released R1-style visual reasoning and referring-expression RL data. |
| [Perception-R1](https://arxiv.org/abs/2504.07954) | Reformulated recognition, grounding, counting, and OCR examples for perception-policy RL. |
| [VL-Rethinker](https://arxiv.org/abs/2504.08837) | ViRL39K, a mixed visual-reasoning RL collection. |
| [VLAA-Thinking](https://arxiv.org/abs/2504.11468) | Verified SFT traces plus a separate 25K-example RL split assembled from nine visual sources. |
| [SophiaVL-R1](https://arxiv.org/abs/2505.17018) | Released multimodal reasoning data paired with outcome and learned thinking rewards. |
| [SRPO](https://arxiv.org/abs/2506.01713) | Reflection-focused multimodal reasoning data for staged SFT and reflection-aware RL. |
| [RewardMap](https://arxiv.org/abs/2510.02240) | ReasonMap-Plus perception and reasoning questions for staged transit-map RL. |

### Selection, Transformation, and Augmentation

| Paper | Data contribution relevant to Trace |
|---|---|
| [Curr-ReFT](https://arxiv.org/abs/2503.07065) | Difficulty-ordered visual curricula plus rejected-sampling self-improvement data. |
| [SoTA with Less](https://arxiv.org/abs/2504.07934) | MCTS-guided filtering of 70K open examples into compact visual RFT subsets. |
| [NoisyRollout](https://arxiv.org/abs/2504.13055) | Clean and perturbed image trajectories mixed with an annealed augmentation schedule. |
| [RAP](https://arxiv.org/abs/2506.04755) | Causal-discrepancy and attention-confidence selection of high-value multimodal examples. |
| [Vision Matters](https://arxiv.org/abs/2506.09736) | Distractor, mixup, and rotation transformations applied inside multimodal post-training. |
| [PAPO](https://arxiv.org/abs/2507.06448) | Perception-aware construction and optimization of multimodal reasoning rollouts. |
| [VisionThink](https://arxiv.org/abs/2507.13348) | Training data and policy routing for selective visual reasoning. |

### Synthetic, Procedural, and Verifiable Data

| Paper | Data contribution relevant to Trace |
|---|---|
| [Jigsaw-R1](https://arxiv.org/abs/2505.23590) | Procedurally controlled jigsaw-puzzle instances and exact rewards. |
| [Game-RL](https://arxiv.org/abs/2505.13886) | Code2Logic synthesis of GameQA across 30 games and 158 verifiable tasks. |
| [VisualSphinx](https://arxiv.org/abs/2505.23977) | Rule-to-image synthesis for large-scale visual logic-puzzle training data. |
| [SynthRL](https://arxiv.org/abs/2506.02096) | Verified harder variants synthesized from visual-math seed questions. |
| [COGS](https://arxiv.org/abs/2510.15040) | Perception/reasoning factor recomposition for chart and webpage question synthesis. |
| [ViCrit](https://arxiv.org/abs/2506.10128) | Synthetic caption corruptions with exact localized targets for visual-perception RL. |
| [Play to Generalize / ViGaL](https://arxiv.org/abs/2506.08011) | Game-play environments used to produce verifiable visual-reasoning experience. |
| [VL-DAC](https://arxiv.org/abs/2508.04280) | Visual RL training in synthetic worlds for real-image transfer. |
| [MetaSpatial](https://arxiv.org/abs/2503.18470) | Multi-turn rendered-layout experience with physics-aware rewards for 3D spatial reasoning. |
| [3D-R1](https://arxiv.org/abs/2507.23478) | Scene-30K, a synthetic 3D reasoning collection with chain-of-thought cold-start data. |
| [Table2LaTeX-RL](https://arxiv.org/abs/2509.17589) | Large-scale table-image reconstruction data optimized with structural and rendered-fidelity rewards. |
| [TRON](https://arxiv.org/abs/2606.01599) | 520 online visual generator--verifier environments organized into five ability buckets with local difficulty ladders and exact rewards. |
| Sphinx | Procedural visual task environment with deterministic task verifiers. |

### Mixtures, Curricula, and Open Collections

| Paper | Data contribution relevant to Trace |
|---|---|
| [One RL to See Them All](https://arxiv.org/abs/2505.18129) | Orsta-Data-47K spanning visual recognition, grounding, and reasoning. |
| [Advancing Multimodal Reasoning with Cold Start](https://arxiv.org/abs/2505.22334) | Released multimodal cold-start data followed by RL. |
| [MM-UPT](https://arxiv.org/abs/2505.22453) | Directly synthesized data for unsupervised multimodal post-training. |
| [MoDoMoDo](https://arxiv.org/abs/2505.24871) | Curated multi-domain data and learned mixture selection for multimodal RLVR. |
| [GThinker](https://arxiv.org/abs/2506.01078) | Cue-guided multimodal reasoning data and RL recipe. |
| [ReVisual-R1](https://arxiv.org/abs/2506.04207) | GRAMMAR cold-start and multimodal RL data used in a staged recipe. |
| [WeThink](https://arxiv.org/abs/2506.07905) | More than 120K synthesized and curated multimodal QA pairs with reasoning paths. |
| [VL-Cogito](https://arxiv.org/abs/2507.22607) | Released curriculum-organized multimodal RL data. |
| [Vision-SR1](https://arxiv.org/abs/2508.19652) | Vision-SR1-47K for self-rewarding decomposed visual reasoning. |
| [We-Math 2.0](https://arxiv.org/abs/2508.10433) | MathBook-generated visual-mathematics data for reasoning post-training. |
| [MMR1](https://arxiv.org/abs/2509.21268) | Open multimodal reasoning resources selected with variance-aware sampling. |
| [OneThinker](https://arxiv.org/abs/2512.03043) | Unified image/video reasoning data and training resources. |
| [Vision-G1](https://arxiv.org/abs/2508.12680) | RL-ready mixture assembled from 46 visual data sources with filtering and curriculum design. |
| [DeepVision-103K](https://arxiv.org/abs/2602.16742) | Visually diverse K--12 mathematical examples constructed explicitly for RLVR training. |
| [Vero](https://arxiv.org/abs/2604.04917) | Vero-600K, assembled from 59 sources with task-routed rewards. |

### Grounded and Spatial Supervision

| Paper | Data contribution relevant to Trace |
|---|---|
| [ViGoRL](https://arxiv.org/abs/2505.23678) | Coordinate-grounded reasoning and visual-search trajectories. |
| [Point-RFT](https://arxiv.org/abs/2505.19702) | Point-grounded multimodal reasoning targets. |
| [SATORI-R1](https://arxiv.org/abs/2505.19094) | Explicit visual anchors and verifiable spatial rewards. |
| [OpenThinkIMG](https://arxiv.org/abs/2505.08617) | Scalable chart-reasoning trajectories for learning adaptive visual-tool invocation. |
| [VisionReasoner](https://arxiv.org/abs/2505.12081) | Multi-object detection, segmentation, and counting examples reformulated for unified RL. |
| [UniVG-R1](https://arxiv.org/abs/2505.14231) | Unified visual-grounding data and task-specific verifiable rewards. |
| [Visual-ARFT](https://arxiv.org/abs/2505.14246) | Agentic visual-search trajectories and reinforcement fine-tuning data. |
| [DeepEyes](https://arxiv.org/abs/2505.14362) | DeepEyes-47K visual-tool trajectories for image-centric reasoning. |
| [GRIT](https://arxiv.org/abs/2505.15879) | Existing QA examples transformed into interleaved language-and-box reasoning targets. |
| [Pixel Reasoner](https://arxiv.org/abs/2505.15966) | Pixel-space action trajectories induced through curiosity-driven visual RL. |
| [ViLaSR](https://arxiv.org/abs/2506.09965) | Interwoven text reasoning and visual drawing for spatial RL. |
| [Rex-Thinker](https://arxiv.org/abs/2506.04034) | HumanRef-CoT grounded referring data. |
| [RRVF](https://arxiv.org/abs/2507.20766) | Chart reasoning and rendering trajectories trained from visual feedback. |
| [Thyme](https://arxiv.org/abs/2508.11630) | Visual-tool interaction data for reasoning beyond a fixed image view. |
| [ReVPT](https://arxiv.org/abs/2509.01656) | Reinforcement trajectories over four visual-perception tools. |
| [iVGR](https://arxiv.org/abs/2605.31096) | Dual-stream grounded/textual RL used to internalize localization. |

## Adjacent Foundations

- [DeepSeekMath](https://arxiv.org/abs/2402.03300),
  [DeepSeek-R1](https://arxiv.org/abs/2501.12948), and
  [Kimi k1.5](https://arxiv.org/abs/2501.12599) establish the broader
  verifiable-RL and scaling context.
- [GQA](https://arxiv.org/abs/1902.09506), CLEVR, PuzzleVQA, and Task Me
  Anything establish executable programs, controlled visual grammars, and
  taxonomy-driven generation.
- [Reasoning Gym](https://arxiv.org/abs/2505.24760) and
  [Enigmata](https://arxiv.org/abs/2505.19914) establish scalable
  generator-verifier environments outside the visual setting.
- OpenThoughts informs controlled data-recipe analysis; WorldBench informs
  broad visual-coverage analysis. Neither is treated as a Trace-equivalent
  multimodal RL task environment.

## Reading and Writing Rule

Use primary papers for claims. The inventory identifies coverage; it does not
authorize copying paper language or reported numbers. Trace-specific counts,
results, and comparisons must be verified against canonical repository
artifacts before entering the manuscript.
