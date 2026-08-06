# 07. Raw-to-published aggregate validation

## Evidence

- **Evidence:** raw-to-published aggregate comparison은 `240`개이고 status 분포는 `pass`=232, `pass_alias_equivalent`=8이다. `pass` 또는 `pass_alias_equivalent` row는 `240/240`개다.
- **Evidence:** `pass_alias_equivalent`는 문서화된 target model label alias의 categorical comparison이며, 수치 metric의 추가 정밀도 검증을 뜻하지 않는다.
- **Evidence:** 검증 표에는 aggregate artifact context와 원본/재계산 값, tolerance, status를 함께 보존한다.

| concurrency | metric | published | recomputed | absolute_delta | relative_delta | status |
|---|---|---|---|---|---|---|
| 1 | successful_profiled_request_count | 355.0 | 355 | 0 | 0 | pass |
| 1 | total_input_tokens | 11688050.001050001 | 11688050.0 | 0.00105 | 8.98354e-11 | pass |
| 1 | total_output_tokens | 127262.00105 | 127262.0 | 0.00105 | 8.2507e-09 | pass |
| 1 | mean_ttft_ms | 1871.1 | 1871.0965438253522 | 0.00345617 | 1.84714e-06 | pass |
| 1 | p50_ttft_ms | 1300.5 | 1300.499699 | 0.000301 | 2.31449e-07 | pass |
| 1 | p75_ttft_ms | 2705.99 | 2705.9893604999997 | 0.0006395 | 2.36328e-07 | pass |
| 1 | p90_ttft_ms | 3334.05 | 3334.0481866 | 0.0018134 | 5.43903e-07 | pass |
| 1 | p95_ttft_ms | 3673.9500000000003 | 3673.9526914000007 | 0.0026914 | 7.32563e-07 | pass |
| 1 | mean_itl_ms | 30.52 | 30.515512542136182 | 0.00448746 | 0.000147033 | pass |
| 1 | p50_itl_ms | 30.200000000000003 | 30.20029034730539 | 0.000290347 | 9.61415e-06 | pass |
| 1 | p75_itl_ms | 31.26 | 31.25526011016949 | 0.00473989 | 0.000151628 | pass |
| 1 | p90_itl_ms | 32.02 | 32.02321716652892 | 0.00321717 | 0.000100474 | pass |
| 1 | p95_itl_ms | 32.51 | 32.514729774101006 | 0.00472977 | 0.000145487 | pass |
| 1 | mean_e2e_ms | 12690.699999999999 | 12690.698255340843 | 0.00174466 | 1.37475e-07 | pass |
| 1 | p50_e2e_ms | 3636.64 | 3636.640535 | 0.000535 | 1.47114e-07 | pass |
| 1 | p75_e2e_ms | 4969.56 | 4969.5579585 | 0.0020415 | 4.10801e-07 | pass |
| 1 | p90_e2e_ms | 11379.849999999999 | 11379.8456304 | 0.0043696 | 3.83977e-07 | pass |
| 1 | p95_e2e_ms | 80424.02 | 80424.0230741 | 0.0030741 | 3.82237e-08 | pass |
| 1 | input_throughput_tps | 3254.13832 | 3254.138321767971 | 1.76797e-06 | 5.43299e-10 | pass |
| 1 | output_throughput_tps | 35.43176 | 35.43175731664696 | 2.68335e-06 | 7.5733e-08 | pass |
| 1 | total_throughput_tps | 3289.57008 | 3289.5700790846176 | 9.15382e-07 | 2.78268e-10 | pass |
| 1 | duration_s | 3591.7496 | 3591.74959522 | 4.78e-06 | 1.33083e-09 | pass |
| 1 | gpu_count | 16.0 | 16.0 | 0 | 0 | pass |
| 1 | per_gpu_input_throughput_tps | 203.38365 | 203.38364511049818 | 4.8895e-06 | 2.40408e-08 | pass |
| 1 | per_gpu_output_throughput_tps | 2.21448 | 2.214484832290435 | 4.83229e-06 | 2.18213e-06 | pass |
| 1 | per_gpu_total_throughput_tps | 205.59813 | 205.5981299427886 | 5.72114e-08 | 2.78268e-10 | pass |
| 1 | target_model | zai-org/GLM-5.2-FP8 | GLM-5.2 FP8 |  |  | pass_alias_equivalent |
| 1 | precision | fp8 | FP8 |  |  | pass |
| 1 | framework | dynamo-sglang | Dynamo + SGLang |  |  | pass |
| 1 | metadata_concurrency | 1.0 | 1 | 0 | 0 | pass |
| 2 | successful_profiled_request_count | 395.0 | 395 | 0 | 0 | pass |
| 2 | total_input_tokens | 9403091.999 | 9403092.0 | 0.001 | 1.06348e-10 | pass |
| 2 | total_output_tokens | 125537.9994 | 125538.0 | 0.0006 | 4.77943e-09 | pass |
| 2 | mean_ttft_ms | 9306.6 | 9306.599976035443 | 2.39646e-05 | 2.57501e-09 | pass |
| 2 | p50_ttft_ms | 2234.24 | 2234.244938 | 0.004938 | 2.21015e-06 | pass |
| 2 | p75_ttft_ms | 3289.99 | 3289.9851595 | 0.0048405 | 1.47128e-06 | pass |
| 2 | p90_ttft_ms | 13053.26 | 13053.256985200002 | 0.0030148 | 2.30961e-07 | pass |
| 2 | p95_ttft_ms | 64202.71 | 64202.70840489966 | 0.0015951 | 2.48448e-08 | pass |
| 2 | mean_itl_ms | 32.77 | 32.76731079429029 | 0.00268921 | 8.2063e-05 | pass |
| 2 | p50_itl_ms | 32.02 | 32.019915132743364 | 8.48673e-05 | 2.65045e-06 | pass |
| 2 | p75_itl_ms | 32.43 | 32.432729349888014 | 0.00272935 | 8.41613e-05 | pass |
| 2 | p90_itl_ms | 33.39 | 33.38514424343356 | 0.00485576 | 0.000145425 | pass |
| 2 | p95_itl_ms | 34.73 | 34.73144009884057 | 0.0014401 | 4.14656e-05 | pass |
| 2 | mean_e2e_ms | 19353.21 | 19353.209090103795 | 0.000909896 | 4.70153e-08 | pass |
| 2 | p50_e2e_ms | 3112.38 | 3112.3802849999997 | 0.000285 | 9.15698e-08 | pass |
| 2 | p75_e2e_ms | 13825.14 | 13825.136777 | 0.003223 | 2.33126e-07 | pass |
| 2 | p90_e2e_ms | 60656.63 | 60656.63079960005 | 0.0007996 | 1.31824e-08 | pass |
| 2 | p95_e2e_ms | 88726.18 | 88726.18342479988 | 0.0034248 | 3.85997e-08 | pass |
| 2 | input_throughput_tps | 2612.47066 | 2612.470658663653 | 1.33635e-06 | 5.11526e-10 | pass |
| 2 | output_throughput_tps | 34.87835 | 34.878350817722264 | 8.17722e-07 | 2.3445e-08 | pass |

## Inference

- **Inference:** a pass supports only the encoded filter, unit conversion, percentile method, time window, and aggregate metric mapping; it does not validate every individual request attribution.

## Unknown

- **Unknown:** aggregate validation remains unavailable for any metric lacking a unique published candidate or a compatible raw recomputation.
