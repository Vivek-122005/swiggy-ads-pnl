#!/usr/bin/env bash
# Download the two public Kaggle datasets that give the simulator real names (needs a Kaggle API token).
# The files stay in data/external (gitignored) - only the generator is published, never the data.
set -euo pipefail
pip install -q kaggle
mkdir -p data/external
kaggle datasets download -d himanshupoddar/zomato-bangalore-restaurants -p data/external --unzip -q
kaggle datasets download -d surajjha101/bigbasket-entire-product-list-28k-datapoints -p data/external --unzip -q
python scripts/slim_zomato.py data/external/zomato.csv data/external/zomato_slim.csv
ls -la data/external
