# Pipeline — installable, standalone CI/CD toolkit for GenLayer contracts.
# Thin wrappers over the `genlayer-pipeline` console script so `make ci` ==
# what GitHub runs.
#
# This workspace is self-contained. It runs the pipeline AGAINST a target
# GenLayer project (TARGET) and always writes artifacts INTO this workspace
# (ARTIFACTS), so a run never leaves traces in the target repo.
#
#   make install                             # pip install -e .[toolchain]
#   make ci                                  # target = this dir
#   make ci TARGET=/path/to/genlayer-project # target = an external project

# Use the installed console script; fall back to module form if not on PATH.
RUNNER    ?= genlayer-pipeline
TARGET    ?= .
ARTIFACTS := artifacts/pipeline
RUN       := $(RUNNER) --root $(TARGET) --artifacts-dir $(ARTIFACTS)

.DEFAULT_GOAL := help
.PHONY: help install install-dev doctor selftest ci lint test build deploy plan \
        report report-md ledger build-dist validate-dist release-check dist-clean clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:  ## Editable install of the CLI + GenLayer toolchain (pip install -e .[toolchain])
	pip install -e '.[toolchain]'

install-dev:  ## Editable install + test deps (pip install -e .[toolchain,dev])
	pip install -e '.[toolchain,dev]'

doctor:  ## Clean-config check: assert the toolkit is generic + show resolved config
	$(RUN) --self-check

selftest:  ## Run the toolkit's own regression suite (incl. zero-trace guard)
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest selftests/ -q

ci:  ## Full local CI (lint -> test -> build) against TARGET
	$(RUN) --stages default

lint:  ## Stage 1 — lint contracts
	$(RUN) --stages lint

test:  ## Stage 2 — run test suites
	$(RUN) --stages test

build:  ## Stage 3 — build validation (schema + frontend)
	$(RUN) --stages build

deploy:  ## Stage 4 — deploy to Studionet (requires env / .env)
	$(RUN) --stages deploy

plan:  ## Dry-run: print the full 4-stage plan
	$(RUN) --stages all --dry-run

report:  ## Regenerate the analytics report from the last run's artifacts
	genlayer-pipeline-report --artifacts-dir $(ARTIFACTS) --format text

report-md:  ## Print the Markdown analytics report
	genlayer-pipeline-report --artifacts-dir $(ARTIFACTS) --format md

ledger:  ## Show the deployment ledger (current live address + history)
	@cat $(ARTIFACTS)/deployments/ledger.json 2>/dev/null || echo "no deployments yet"

# ------------------------------------------------------------------ packaging
build-dist: dist-clean  ## Build wheel (.whl) + sdist (.tar.gz) into dist/
	python -m build
	@echo; echo "Artifacts:"; ls -lh dist/

validate-dist:  ## Validate dist/ artifacts (metadata, contents, temp-venv install)
	bash tools/validate_dist.sh

release-check: build-dist validate-dist  ## Build + validate in one shot
	@echo "release artifacts ready in dist/"

dist-clean:  ## Remove build/dist/egg-info packaging artifacts
	rm -rf dist build src/*.egg-info

clean:  ## Remove pipeline artifacts (keeps the deployment ledger)
	rm -rf $(ARTIFACTS)/*.log $(ARTIFACTS)/*.xml $(ARTIFACTS)/*.json \
		$(ARTIFACTS)/events.ndjson $(ARTIFACTS)/report.md $(ARTIFACTS)/gltest
