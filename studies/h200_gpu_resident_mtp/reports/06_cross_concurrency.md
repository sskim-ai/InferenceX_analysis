# 06. Cross-concurrency matching

## Evidence

| left_group | right_group | matched_source_key_count | same_output_length_count | strict_ttft_count | strict_decode_count | median_ttft_ratio_right_over_left | median_itl_ratio_right_over_left | median_e2e_ratio_right_over_left | matching_method |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| conc12 | conc16 | 671 | 671 | 671 | 592 | 1.95557 | 1.00312 | 1.45093 | source_trace_id+source_outer_idx+source_inner_idx |
| conc8 | conc12 | 612 | 611 | 612 | 520 | 1.53825 | 1.00829 | 1.19072 | source_trace_id+source_outer_idx+source_inner_idx |
| conc8 | conc16 | 337 | 337 | 337 | 261 | 6.34167 | 1.01557 | 3.44874 | source_trace_id+source_outer_idx+source_inner_idx |

### ID03 strict source-key subsets

| pair | left_concurrency | right_concurrency | matched_source_key_count | same_output_length_count | strict_ttft_count | strict_decode_count | median_ttft_ratio_right_over_left | p90_ttft_ratio_right_over_left | median_itl_ratio_right_over_left | weighted_itl_left_ms | weighted_itl_right_ms | weighted_itl_ratio_right_over_left | median_e2e_ratio_right_over_left | coverage_overlap_ratio_jaccard | matching_method |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| c8_c12 | 8 | 12 | 112 | 112 | 112 | 112 | 1.45117 | 14.064 | 0.992266 | 11.1574 | 11.3219 | 1.01475 | 1.14901 | 0.941176 | source_trace_id+source_outer_idx+source_inner_idx; source-key median per concurrency |
| c8_c16 | 8 | 16 | 13 | 13 | 13 | 13 | 1.28084 | 17.2266 | 1.00834 | 10.962 | 11.4114 | 1.041 | 1.14554 | 0.109244 | source_trace_id+source_outer_idx+source_inner_idx; source-key median per concurrency |
| c12_c16 | 12 | 16 | 13 | 13 | 13 | 13 | 0.32583 | 11.2269 | 1.00706 | 11.3456 | 11.4114 | 1.0058 | 0.894576 | 0.116071 | source_trace_id+source_outer_idx+source_inner_idx; source-key median per concurrency |

- Per-pair request rows are versioned in ../processed/id03_exact_match_c8_c12.csv, ../processed/id03_exact_match_c8_c16.csv, and ../processed/id03_exact_match_c12_c16.csv; three-way overlap is in ../processed/id03_exact_match_all.csv.


## Inference

- Pair rows collapse repeated records to a source-key/concurrency median before ratios; raw request rows are not treated as independent replicates.

## Unknown

- Identical source keys do not ensure identical output lengths under a speculative-decoding replay. Strict decode subsets require the observed output length to agree.
