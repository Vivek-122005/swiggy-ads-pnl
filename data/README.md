# data/ (not committed)

Everything here is generated or downloaded locally and is gitignored. Only this README is in the repo.

| Folder | What | How it gets here |
|---|---|---|
| `raw/` | Simulator output (`raw_*.csv.gz`) — the raw layer dbt reads | `make data` |
| `answer_key/` | Planted anomalies + hidden truth (incrementality, patience). **Never read by dbt or the dashboard.** | `make data` |
| `external/` | Optional public Kaggle datasets that give advertisers real names | download yourself (below) |
| `warehouse.duckdb` | Local warehouse | `make models` |

## Optional Kaggle inputs (`data/external/`)

| File name (either works) | Dataset |
|---|---|
| `zomato.csv` or `zomato_slim.csv` | [Zomato Bangalore Restaurants](https://www.kaggle.com/datasets/himanshupoddar/zomato-bangalore-restaurants) |
| `BigBasket Products.csv` or `bigbasket.csv` | [BigBasket Entire Product List](https://www.kaggle.com/datasets/surajjha101/bigbasket-entire-product-list-28k-datapoints) |

`python scripts/slim_zomato.py data/external/zomato.csv data/external/zomato_slim.csv` drops the review text
(570 MB → 5 MB). Without these files the simulator generates a synthetic advertiser base with the same shape.
The datasets are not redistributed here; only the generator is published.
