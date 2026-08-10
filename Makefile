SHELL := /bin/bash
PYTHON ?= .venv/bin/python
CONFIG := configs/run_29820102138.yaml

.PHONY: bootstrap preflight acquire-run acquire-traces inspect build-source build-h200 join coverage analyze-ids analyze-concurrency validate figures report test lint secret-scan all mtp-acquire mtp-analyze mtp-id03 mtp-report mtp-all

bootstrap:
	bash scripts/bootstrap.sh

preflight:
	$(PYTHON) scripts/preflight.py

acquire-run:
	$(PYTHON) scripts/acquire_github_artifacts.py --config $(CONFIG)

acquire-traces:
	$(PYTHON) scripts/acquire_hf_trace.py --config $(CONFIG)

inspect:
	$(PYTHON) scripts/inspect_artifacts.py --config $(CONFIG)

build-source:
	$(PYTHON) scripts/build_source_trace_table.py --config $(CONFIG) --missing-policy empty
	$(PYTHON) scripts/analyze_source_workload.py --config $(CONFIG)

build-h200:
	$(PYTHON) scripts/build_h200_request_table.py --config $(CONFIG)

join:
	$(PYTHON) scripts/join_trace_ids.py --config $(CONFIG)

coverage:
	$(PYTHON) scripts/run_analysis.py --config $(CONFIG) --stage coverage

analyze-ids:
	$(PYTHON) scripts/run_analysis.py --config $(CONFIG) --stage ids

analyze-concurrency:
	$(PYTHON) scripts/run_analysis.py --config $(CONFIG) --stage concurrency

validate:
	$(PYTHON) scripts/run_analysis.py --config $(CONFIG) --stage validate

figures:
	$(PYTHON) scripts/build_reports.py --figures-only

report:
	$(PYTHON) scripts/build_reports.py --reports-only

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

secret-scan:
	$(PYTHON) scripts/secret_scan.py

# Study B: public 32×H200 GPU-resident KV + MTP run.  Acquisition is kept
# separate because it requires authenticated `gh` access and downloads raw
# artifacts intentionally excluded from Git.
mtp-acquire:
	$(PYTHON) scripts/h200_gpu_resident_mtp/acquire.py --download

mtp-analyze:
	$(PYTHON) scripts/h200_gpu_resident_mtp/analyze.py

mtp-id03:
	mkdir -p .mplconfig
	MPLCONFIGDIR=$(CURDIR)/.mplconfig $(PYTHON) scripts/h200_gpu_resident_mtp/id03_deep_dive.py

mtp-report:
	mkdir -p .mplconfig
	MPLCONFIGDIR=$(CURDIR)/.mplconfig $(PYTHON) scripts/h200_gpu_resident_mtp/build_reports.py

mtp-all: mtp-analyze mtp-id03 mtp-report

all: preflight
	$(MAKE) acquire-run
	$(MAKE) acquire-traces
	$(MAKE) inspect
	$(MAKE) build-source
	$(MAKE) build-h200
	$(MAKE) join
	$(MAKE) coverage
	$(MAKE) analyze-ids
	$(MAKE) analyze-concurrency
	$(MAKE) validate
	$(MAKE) figures
	$(MAKE) report
	$(MAKE) test
	$(MAKE) lint
	$(MAKE) secret-scan
