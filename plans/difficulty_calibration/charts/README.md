# Charts Calibration

Historical note: the numeric task stats in this table are from the earlier `Qwen/Qwen3-VL-2B-Instruct` 32-rollout probe and should be treated as reference only. Active calibration work should use fresh `Qwen/Qwen3-VL-8B-Instruct` `200 x 32` probes.
Tasks in this domain: 10

| Task | Direction | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Low omission frac | High omission frac | Task record |
|---|---|---:|---:|---:|---:|---:|---|
| task_charts_composition_subset_value | make_harder | 0.7512 | 0.0086 | 0.4773 | 0.0523 | 0.6219 | [task_charts_composition_subset_value](task_charts_composition_subset_value.md) |
| task_charts_counting_value_count | make_easier | 0.2843 | 0.0648 | 0.0102 | 0.2891 | 0.0547 | [task_charts_counting_value_count](task_charts_counting_value_count.md) |
| task_charts_distribution_boxplot_label | make_harder | 0.5306 | 0.1242 | 0.1922 | 0.2891 | 0.4492 | [task_charts_distribution_boxplot_label](task_charts_distribution_boxplot_label.md) |
| task_charts_distribution_density_label | make_harder | 0.5812 | 0.1625 | 0.2742 | 0.3000 | 0.5281 | [task_charts_distribution_density_label](task_charts_distribution_density_label.md) |
| task_charts_distribution_histogram_count | make_harder | 0.6257 | 0.0148 | 0.3102 | 0.0750 | 0.4062 | [task_charts_distribution_histogram_count](task_charts_distribution_histogram_count.md) |
| task_charts_multiseries_pairwise_comparison_count | review | 0.2890 | 0.0250 | 0.0000 | 0.1742 | 0.0109 | [task_charts_multiseries_pairwise_comparison_count](task_charts_multiseries_pairwise_comparison_count.md) |
| task_charts_readout_subset_value | make_harder | 0.5255 | 0.0477 | 0.0938 | 0.1508 | 0.3273 | [task_charts_readout_subset_value](task_charts_readout_subset_value.md) |
| task_charts_statistics_summary_label | make_harder | 0.7037 | 0.0555 | 0.4430 | 0.1297 | 0.6148 | [task_charts_statistics_summary_label](task_charts_statistics_summary_label.md) |
| task_charts_statistics_summary_value | make_harder | 0.6520 | 0.0195 | 0.2586 | 0.0891 | 0.4906 | [task_charts_statistics_summary_value](task_charts_statistics_summary_value.md) |
| task_charts_trend_structure_value | make_easier | 0.1760 | 0.1891 | 0.0000 | 0.5203 | 0.0156 | [task_charts_trend_structure_value](task_charts_trend_structure_value.md) |

Active note: [task_charts_composition_subset_value](task_charts_composition_subset_value.md) has been semantically redesigned into a stacked-only composition-arithmetic task and reevaluated with fresh `200 x 32` `Qwen/Qwen3-VL-8B-Instruct` probes. It is currently blocked: the two sum-style variants remain too easy even after structural hardening, so the next step is either another semantic redesign or dropping the task.

Active note: [task_charts_counting_value_count](task_charts_counting_value_count.md) remains calibratable. The current best `Qwen/Qwen3-VL-8B-Instruct` checkpoint is iter1 (`hard_frac=0.035`, `easy_frac=0.340`, `band_frac=0.625`). Later threshold-allocation experiments passed distribution but did not beat iter1, so the next move should be a stronger semantic redesign of the threshold variants rather than more local threshold-count tweaks.

Active note: [task_charts_distribution_boxplot_label](task_charts_distribution_boxplot_label.md) has been semantically redesigned. The old `highest_median` variant was replaced with `median_above_reference_q3`, and the current best `Qwen/Qwen3-VL-8B-Instruct` checkpoint is iter1 (`hard_frac=0.100`, `easy_frac=0.540`, `band_frac=0.360`). This is better than the retired median-ranking semantics but still too easy, so the next pass should keep targeting only the relational median variant.

Active note: [task_charts_distribution_density_label](task_charts_distribution_density_label.md) now has a fresh `Qwen/Qwen3-VL-8B-Instruct` `200 x 32` baseline (`hard_frac=0.235`, `easy_frac=0.630`, `band_frac=0.135`). It has a split-tail failure rather than a single direction: `highest_mode` and `lowest_mode` are too easy, while `bimodal_label` is too hard. The next pass should tune those variants separately instead of applying one uniform harder/easier update.

Active note: the first split-tail pass for [task_charts_distribution_density_label](task_charts_distribution_density_label.md) was worse than baseline (`hard_frac=0.185`, `easy_frac=0.715`, `band_frac=0.100`). It over-softened `bimodal_label` into the easy tail while leaving `highest_mode` too easy, so the current best checkpoint remains the recorded baseline.

Active note: the second split-tail pass for [task_charts_distribution_density_label](task_charts_distribution_density_label.md) targeted only `highest_mode` / `lowest_mode` and did reduce the easy tail (`easy_frac=0.520` vs `0.630` baseline), but it raised the hard tail too far (`hard_frac=0.340`). It is not a clean retained checkpoint either, so the task likely needs a semantic redesign of the extreme-mode queries if we continue.

Active note: [task_charts_distribution_histogram_count](task_charts_distribution_histogram_count.md) now has a fresh `Qwen/Qwen3-VL-8B-Instruct` `200 x 32` baseline (`hard_frac=0.000`, `easy_frac=0.930`, `band_frac=0.070`). It is saturated across all variants and bin counts, so the next pass should be semantic hardening rather than only increasing the existing bin-count support.
