# 07. HiSparse c8 vs GPU-resident MTP c8

## Evidence

| comparison_scope | metric | hisparse_c8_value | gpu_resident_mtp_c8_value | gpu_resident_over_hisparse_ratio | sample_count | caveat |
| --- | --- | --- | --- | --- | --- | --- |
| run_level_unpaired_observed_system_difference | ttft_median_ms | 228708 | 1471.05 | 0.00643201 | 219 | 16→32 GPUs, 1P1D→2P2D, KV mode/dtype, MTP, and software may differ; not a causal HiSparse estimate. |
| run_level_unpaired_observed_system_difference | weighted_decode_tps | 32.5161 | 92.4771 | 2.84404 | 219 | 16→32 GPUs, 1P1D→2P2D, KV mode/dtype, MTP, and software may differ; not a causal HiSparse estimate. |
| run_level_unpaired_observed_system_difference | wall_output_tps | 23.5666 | 210.505 | 8.93234 | 219 | 16→32 GPUs, 1P1D→2P2D, KV mode/dtype, MTP, and software may differ; not a causal HiSparse estimate. |
| run_level_unpaired_observed_system_difference | output_tokens_total | 84618 | 760694 | 8.98974 | 219 | 16→32 GPUs, 1P1D→2P2D, KV mode/dtype, MTP, and software may differ; not a causal HiSparse estimate. |
| source_key_matched_median_observed_system_ratio | ttft_ratio_gpu_resident_over_hisparse |  | 0.00880767 | 0.00880767 | 83 | Source-key matching controls workload identity only; it does not isolate a single architecture change. |
| source_key_matched_median_observed_system_ratio | itl_ratio_gpu_resident_over_hisparse |  | 0.353382 | 0.353382 | 64 | Source-key matching controls workload identity only; it does not isolate a single architecture change. |
| source_key_matched_median_observed_system_ratio | e2e_ratio_gpu_resident_over_hisparse |  | 0.0482293 | 0.0482293 | 83 | Source-key matching controls workload identity only; it does not isolate a single architecture change. |

| root_trace_id | left_group | right_group | matched_source_key_count | same_output_length_count | strict_ttft_count | strict_decode_count | median_ttft_ratio_right_over_left | median_itl_ratio_right_over_left | median_e2e_ratio_right_over_left | matching_method |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 006c98de37d819e95b0840e25426bb7ca99d | hisparse_c8 | gpu_resident_mtp_c8 | 13 | 13 | 13 | 13 | 0.0297453 | 0.347908 | 0.0685781 | source_trace_id+source_outer_idx+source_inner_idx |
| 0196085d85d2075a50b74cd8795ffbdcea9a | hisparse_c8 | gpu_resident_mtp_c8 | 11 | 11 | 11 | 0 | 0.00880767 |  | 0.00880767 | source_trace_id+source_outer_idx+source_inner_idx |
| 03e110ac6921c2fe9ac7772a9654314a2beb | hisparse_c8 | gpu_resident_mtp_c8 | 14 | 14 | 14 | 6 | 0.00777687 | 0.366592 | 0.0147972 | source_trace_id+source_outer_idx+source_inner_idx |
| 0470d446a4514dfe0c6ad0be92853bd13287 | hisparse_c8 | gpu_resident_mtp_c8 | 33 | 33 | 33 | 33 | 0.0202705 | 0.350423 | 0.0561087 | source_trace_id+source_outer_idx+source_inner_idx |
| 05c249572509162371b7b82339674db64b5d | hisparse_c8 | gpu_resident_mtp_c8 | 6 | 6 | 6 | 6 | 0.00428604 | 0.385369 | 0.0381468 | source_trace_id+source_outer_idx+source_inner_idx |
| 05f72f78a037cfa5cd4e4541960a574701d9 | hisparse_c8 | gpu_resident_mtp_c8 | 5 | 5 | 5 | 5 | 0.00470956 | 0.438718 | 0.0282238 | source_trace_id+source_outer_idx+source_inner_idx |
| 063179eb93f4337a662e859c5a2c5638e03f | hisparse_c8 | gpu_resident_mtp_c8 | 1 | 1 | 1 | 1 | 0.0109322 | 12.9633 | 0.0464868 | source_trace_id+source_outer_idx+source_inner_idx |

## Inference

- Every ratio is an **observed system-level difference**, not a causal HiSparse effect: GPU count, P/D topology, KV dtype/residency, MTP, routing, and software can all differ.

## Unknown

- The available evidence cannot isolate the contribution of any one of those changes.
