# 06. Cross-concurrency matching

## Evidence

| left_group | right_group | matched_source_key_count | same_output_length_count | strict_ttft_count | strict_decode_count | median_ttft_ratio_right_over_left | median_itl_ratio_right_over_left | median_e2e_ratio_right_over_left | matching_method |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| conc12 | conc16 | 671 | 671 | 671 | 592 | 1.95557 | 1.00312 | 1.45093 | source_trace_id+source_outer_idx+source_inner_idx |
| conc8 | conc12 | 612 | 611 | 612 | 520 | 1.53825 | 1.00829 | 1.19072 | source_trace_id+source_outer_idx+source_inner_idx |
| conc8 | conc16 | 337 | 337 | 337 | 261 | 6.34167 | 1.01557 | 3.44874 | source_trace_id+source_outer_idx+source_inner_idx |

## Inference

- Pair rows collapse repeated records to a source-key/concurrency median before ratios; raw request rows are not treated as independent replicates.

## Unknown

- Identical source keys do not ensure identical output lengths under a speculative-decoding replay. Strict decode subsets require the observed output length to agree.
