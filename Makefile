# One command rebuilds everything from the fixed seed:  make all
PY      ?= python3
DBT     ?= dbt
TARGET  ?= duckdb
DBT_DIR := dbt
DBT_ARGS := --project-dir $(DBT_DIR) --profiles-dir $(DBT_DIR) --target $(TARGET)

.PHONY: all setup data sanity models test docs dashboard pytest clean

all: data models test dashboard   ## generate data, build warehouse, run tests, export dashboard data

setup:                            ## install Python deps + dbt packages
	$(PY) -m pip install -r requirements.txt
	$(DBT) deps $(DBT_ARGS)

data:                             ## run the simulator (seeded) -> data/raw/*.csv.gz
	$(PY) -m simulator.run --config config/sim_config.yaml --out data/raw --answer-key data/answer_key

sanity:                           ## plausibility report + shape charts
	$(PY) -m simulator.sanity --raw data/raw --charts analysis/sanity

models:                           ## build staging -> intermediate -> marts
	$(DBT) run $(DBT_ARGS)

test:                             ## dbt data tests (grain, ranges, reconciliation)
	$(DBT) test $(DBT_ARGS)

pytest:                           ## unit tests for simulator logic
	$(PY) -m pytest -q tests

docs:                             ## dbt docs site = metric dictionary + lineage
	$(DBT) docs generate $(DBT_ARGS) --static

dashboard:                        ## export mart tables to JSON for the hosted dashboard
	$(PY) -m dashboard.export --db data/warehouse.duckdb --out dashboard/site/data

clean:
	rm -rf data/raw data/answer_key data/warehouse.duckdb $(DBT_DIR)/target $(DBT_DIR)/logs
