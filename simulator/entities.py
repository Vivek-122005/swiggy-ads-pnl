"""Zones, advertisers and campaigns.

If the Kaggle files are present (data/external/zomato.csv, data/external/bigbasket.csv)
real restaurant / brand names and attributes are used; otherwise a synthetic advertiser
base with the same shape is generated. Either way, ALL ad behaviour is simulated.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

CUISINES = ["north_indian", "south_indian", "biryani", "chinese", "pizza", "burger",
            "desserts", "cafe", "healthy", "andhra", "kerala", "street_food", "rolls", "bakery"]

_RESTO_A = ["Royal", "Green Leaf", "Spice", "Urban", "Namma", "Old Town", "Golden", "Little",
            "Blue Door", "Corner", "Masala", "Tandoor", "Coastal", "Udupi", "Brick Oven", "Hungry",
            "Saffron", "Copper", "Silver Spoon", "Twin Tree", "Lotus", "Mango", "Pepper", "Ragi"]
_RESTO_B = {
    "north_indian": ["Dhaba", "Rasoi", "Kitchen"], "south_indian": ["Tiffins", "Darshini", "Bhavan"],
    "biryani": ["Biryani House", "Biryani Co", "Dum Pot"], "chinese": ["Wok", "Dragon Bowl", "Noodle Bar"],
    "pizza": ["Pizzeria", "Slice Co", "Pizza Lab"], "burger": ["Burger Joint", "Grill Co", "Patty Shack"],
    "desserts": ["Creamery", "Sweet Shop", "Dessert Bar"], "cafe": ["Cafe", "Coffee House", "Brew Co"],
    "healthy": ["Salad Bar", "Bowl Co", "Greens"], "andhra": ["Andhra Mess", "Meals", "Spice Mess"],
    "kerala": ["Kerala Kitchen", "Appam House", "Toddy Shop"], "street_food": ["Chaat Corner", "Chaat Co", "Pani Puri Hub"],
    "rolls": ["Roll Co", "Kathi House", "Wrap Shack"], "bakery": ["Bakery", "Bake House", "Patisserie"],
}
_BRAND_A = ["Crunch", "Fresh", "Daily", "Pure", "Nutri", "Zing", "Happy", "Golden", "Farm", "Urban",
            "Spark", "Bloom", "Kosha", "Tara", "Vela", "Mitra", "Sona", "Amara", "Nila", "Ojas"]
_BRAND_B = ["ly", "ful", "ora", "ica", "ence", "o", "nest", "veda", "mart", "kart", "bite", "leaf",
            "drop", "wave", "root", "glow", "pod", "nova", "crest", "field"]


def build_zones(cfg: dict) -> pd.DataFrame:
    z = pd.DataFrame(cfg["zones"])
    z["weight"] = z["weight"] / z["weight"].sum()
    return z


def _neighbours(zones: pd.DataFrame, k: int = 3) -> dict[str, list[str]]:
    xy = zones[["lat", "lon"]].to_numpy()
    d = ((xy[:, None, :] - xy[None, :, :]) ** 2).sum(-1)
    out = {}
    for i, zid in enumerate(zones["zone_id"]):
        order = np.argsort(d[i])
        out[zid] = [zones["zone_id"].iloc[j] for j in order[1:k + 1]]
    return out


def _unique_names(rng, n, make):
    names, seen = [], {}
    for _ in range(n):
        base = make()
        seen[base] = seen.get(base, 0) + 1
        names.append(base if seen[base] == 1 else f"{base} ({seen[base]})")
    return names


ZONE_ALIASES = {  # Zomato "location" strings -> zone names
    "koramangala": "Koramangala", "indiranagar": "Indiranagar", "hsr": "HSR Layout", "whitefield": "Whitefield",
    "jayanagar": "Jayanagar", "btm": "BTM Layout", "marathahalli": "Marathahalli", "electronic city": "Electronic City",
    "jp nagar": "JP Nagar", "j p nagar": "JP Nagar", "bellandur": "Bellandur", "malleshwaram": "Malleshwaram",
    "hebbal": "Hebbal", "yelahanka": "Yelahanka", "banashankari": "Banashankari", "rajajinagar": "Rajajinagar",
    "sarjapur": "Bellandur", "brookefield": "Whitefield", "kalyan nagar": "Hebbal", "basavanagudi": "Jayanagar",
    "ejipura": "Koramangala", "domlur": "Indiranagar", "old airport road": "Indiranagar", "kammanahalli": "Hebbal",
}
CUISINE_MAP = {"north indian": "north_indian", "south indian": "south_indian", "biryani": "biryani", "chinese": "chinese",
               "pizza": "pizza", "burger": "burger", "desserts": "desserts", "ice cream": "desserts", "cafe": "cafe",
               "beverages": "cafe", "healthy food": "healthy", "salad": "healthy", "andhra": "andhra", "kerala": "kerala",
               "street food": "street_food", "fast food": "burger", "rolls": "rolls", "bakery": "bakery", "momos": "chinese"}
BB_CATEGORY_MAP = {"snacks & branded foods": "snacks", "gourmet & world food": "snacks", "beverages": "beverages",
                   "bakery, cakes & dairy": "dairy", "eggs, meat & fish": "dairy", "foodgrains, oil & masala": "staples",
                   "fruits & vegetables": "staples", "beauty & hygiene": "personal_care", "cleaning & household": "household",
                   "kitchen, garden & pets": "household", "baby care": "baby_care"}


def _first(folder: Path, names: list[str]) -> Path:
    """First existing file among accepted names (Kaggle downloads keep their original names)."""
    for n in names:
        if (folder / n).exists():
            return folder / n
    return folder / names[0]


def _cols(raw: pd.DataFrame) -> dict:
    return {c.lower().strip(): c for c in raw.columns}


def _load_kaggle_restaurants(path: Path, zones: pd.DataFrame, n: int, rng) -> pd.DataFrame | None:
    """Zomato Bangalore Restaurants (Kaggle). Real names/attributes; ad behaviour stays simulated."""
    if not path.exists():
        return None
    raw = pd.read_csv(path, low_memory=False)
    cols = _cols(raw)
    need = ["name", "location", "rate", "approx_cost(for two people)", "cuisines"]
    if not all(c in cols for c in need):
        print(f"  [entities] {path.name}: unexpected columns, using synthetic restaurants")
        return None
    df = raw[[cols[c] for c in need]].copy()
    df.columns = ["name", "location", "rate", "cost_for_two", "cuisines"]
    df["rating"] = pd.to_numeric(df["rate"].astype(str).str.split("/").str[0], errors="coerce")
    df["cost_for_two"] = pd.to_numeric(df["cost_for_two"].astype(str).str.replace(",", ""), errors="coerce")
    df = df.dropna(subset=["rating", "cost_for_two", "name"])
    outlets = df.groupby("name")["location"].nunique()          # real multi-location brands = chains
    zid = dict(zip(zones["name"], zones["zone_id"]))

    def to_zone(loc):
        l = str(loc).lower()
        for k, v in ZONE_ALIASES.items():
            if k in l:
                return zid[v]
        return None
    df["home_zone"] = df["location"].map(to_zone)
    if "listed_in(city)" in cols:   # fall back to the delivery area the listing appears under
        city = raw.loc[df.index, cols["listed_in(city)"]].map(to_zone)
        df["home_zone"] = df["home_zone"].fillna(city)
    df = df.dropna(subset=["home_zone"]).drop_duplicates("name")
    if len(df) < n:
        print(f"  [entities] {path.name}: only {len(df)} mappable restaurants, using synthetic")
        return None
    # zone quotas follow demand (weight x density); sparse outer zones are topped up with
    # restaurants from the nearest covered localities (they deliver across zone borders)
    zw = (zones["weight"] * zones["density"]).to_numpy()
    quota = np.maximum(np.round(n * zw / zw.sum()).astype(int), 25)
    quota[np.argmax(quota)] += n - quota.sum()
    nb = _neighbours(zones, k=len(zones) - 1)
    pools = {z: list(rng.permutation(df.index[df["home_zone"] == z])) for z in zones["zone_id"]}
    picked, homes = [], []
    for z, q in zip(zones["zone_id"], quota):
        take = pools[z][:q]
        pools[z] = pools[z][q:]
        picked += take
        homes += [z] * len(take)
    for z, q in zip(zones["zone_id"], quota):
        short = q - homes.count(z)
        for donor in nb[z]:
            if short <= 0:
                break
            take = pools[donor][:short]
            pools[donor] = pools[donor][short:]
            picked += take
            homes += [z] * len(take)
            short -= len(take)
    df = df.loc[picked].copy()
    df["home_zone"] = homes

    def cuisine(c):
        for part in str(c).lower().split(","):
            part = part.strip()
            if part in CUISINE_MAP:
                return CUISINE_MAP[part]
        return None
    df["cuisine"] = df["cuisines"].map(cuisine)
    miss = df["cuisine"].isna()
    df.loc[miss, "cuisine"] = rng.choice(CUISINES, miss.sum())
    df["is_chain"] = df["name"].map(outlets).fillna(1).to_numpy() >= 2
    df["rating"] = df["rating"].clip(2.5, 4.9)
    df["cost_for_two"] = df["cost_for_two"].clip(100, 4000)
    print(f"  [entities] using {n} real restaurant names from {path.name} ({df['is_chain'].mean():.0%} chains)")
    return df[["name", "home_zone", "rating", "cost_for_two", "cuisine", "is_chain"]].reset_index(drop=True)


def _load_kaggle_brands(path: Path, n: int, rng, cat_weights: list[dict]) -> pd.DataFrame | None:
    """BigBasket product list (Kaggle) -> brand advertisers with category and basket value."""
    if not path.exists():
        return None
    raw = pd.read_csv(path, low_memory=False)
    cols = _cols(raw)
    if not all(c in cols for c in ["brand", "category", "sale_price"]):
        print(f"  [entities] {path.name}: unexpected columns, using synthetic brands")
        return None
    df = raw[[cols["brand"], cols["category"], cols["sale_price"]] + ([cols["rating"]] if "rating" in cols else [])].copy()
    df.columns = ["brand", "category", "sale_price"] + (["rating"] if "rating" in cols else [])
    if "sub_category" in cols:
        df["sub"] = raw[cols["sub_category"]].astype(str).str.lower()
    else:
        df["sub"] = ""
    df["cat"] = df["category"].astype(str).str.lower().str.strip().map(BB_CATEGORY_MAP)
    df.loc[df["sub"].str.contains("frozen"), "cat"] = "frozen"
    df["sale_price"] = pd.to_numeric(df["sale_price"], errors="coerce")
    df = df.dropna(subset=["brand", "cat", "sale_price"])
    g = df.groupby("brand").agg(skus=("cat", "size"), category=("cat", lambda x: x.mode().iloc[0]),
                                price=("sale_price", "median"),
                                rating=("rating", "mean") if "rating" in df else ("sale_price", lambda x: np.nan))
    g = g[g["skus"] >= 3].sort_values("skus", ascending=False)
    if len(g) < n:
        print(f"  [entities] {path.name}: only {len(g)} brands, using synthetic")
        return None
    # category quotas follow Instamart search demand; within a category, brands with the
    # widest range (most SKUs) advertise first
    cw = pd.Series({c["category"]: c["weight"] for c in cat_weights})
    quota = np.round(n * cw / cw.sum()).astype(int)
    quota[quota.idxmax()] += n - quota.sum()
    parts = [g[g["category"] == c].head(q) for c, q in quota.items()]
    got = pd.concat(parts)
    rest = g.drop(got.index).head(n - len(got))   # categories with too few brands -> fill by size
    g = pd.concat([got, rest]).reset_index()
    out = pd.DataFrame({
        "name": g["brand"].astype(str).str.strip(),
        "home_zone": None,
        "rating": g["rating"].fillna(pd.Series(rng.normal(4.1, 0.25, n))).clip(3.0, 4.9).round(1),
        "cost_for_two": np.clip(g["price"] * rng.uniform(1.8, 3.2, n), 120, 2500).round(-1),  # basket value
        "cuisine": None,
        "category": g["category"],
    })
    print(f"  [entities] using {n} real brand names from {path.name}")
    return out


def build_advertisers(cfg: dict, zones: pd.DataFrame, rng: np.random.Generator,
                      external_dir: Path | None = None) -> pd.DataFrame:
    a = cfg["advertisers"]
    n_r, n_b = a["n_restaurants"], a["n_brands"]
    start = pd.Timestamp(cfg["calendar"]["start_date"])
    n_weeks = cfg["calendar"]["weeks"]

    # ---- restaurants -------------------------------------------------------
    ext = Path(external_dir or "data/external")
    kag = _load_kaggle_restaurants(_first(ext, ["zomato_slim.csv", "zomato.csv"]), zones, n_r, rng)
    if kag is not None:
        r = kag
        r["name_source"] = "kaggle_zomato"
    else:
        zone_p = (zones["weight"] * zones["density"]).to_numpy()
        zone_p = zone_p / zone_p.sum()
        cuisine = rng.choice(CUISINES, n_r)

        def mk(c=iter(cuisine)):
            cu = next(c)
            return f"{rng.choice(_RESTO_A)} {rng.choice(_RESTO_B[cu])}"
        r = pd.DataFrame({
            "name": _unique_names(rng, n_r, mk),
            "home_zone": rng.choice(zones["zone_id"], n_r, p=zone_p),
            "rating": np.clip(rng.normal(3.95, 0.35, n_r), 2.8, 4.9).round(1),
            "cost_for_two": np.clip(rng.lognormal(np.log(550), 0.45, n_r), 150, 3000).round(-1),
            "cuisine": cuisine,
        })
        r["name_source"] = "synthetic"
        r["is_chain"] = rng.random(n_r) < a["chain_share"]
    r["advertiser_type"] = "restaurant"
    r["category"] = r["cuisine"]

    # ---- brands ------------------------------------------------------------
    kb = _load_kaggle_brands(_first(ext, ["bigbasket.csv", "BigBasket Products.csv"]), n_b, rng, cfg["instamart_categories"])
    cats = pd.DataFrame(cfg["instamart_categories"])
    bcat = rng.choice(cats["category"], n_b, p=(cats["weight"] / cats["weight"].sum()).to_numpy())
    b = pd.DataFrame({
        "name": _unique_names(rng, n_b, lambda: f"{rng.choice(_BRAND_A)}{rng.choice(_BRAND_B)}"),
        "home_zone": None,
        "rating": np.clip(rng.normal(4.1, 0.25, n_b), 3.3, 4.9).round(1),
        "cost_for_two": np.clip(rng.lognormal(np.log(420), 0.35, n_b), 120, 1500).round(-1),  # avg basket value
        "cuisine": None,
        "category": bcat,
    })
    b["name_source"] = "synthetic"
    if kb is not None:
        b = kb
        b["name_source"] = "kaggle_bigbasket"
    b["advertiser_type"] = "brand"
    b["is_chain"] = False

    adv = pd.concat([r, b], ignore_index=True)
    n = len(adv)
    adv.insert(0, "advertiser_id", [f"ADV{i:05d}" for i in range(1, n + 1)])
    adv["segment"] = np.where(adv["advertiser_type"] == "brand", "brand",
                              np.where(adv["is_chain"], "chain", "independent"))

    # Budgets: heavy-tailed (concentration). Monthly INR.
    bs = a["budget_scale"]
    seg_mu = {"independent": np.log(3000), "chain": np.log(25000), "brand": np.log(45000)}
    seg_sd = {"independent": 0.6, "chain": 1.05, "brand": 1.45}
    adv["monthly_budget"] = [float(np.round(rng.lognormal(seg_mu[s], seg_sd[s]) * bs, -2)) for s in adv["segment"]]
    # Target CPC bids (INR). Banner bids are CPM and set on campaigns.
    base_bid = np.where(adv["segment"] == "independent", 12.0, np.where(adv["segment"] == "chain", 16.0, 18.0))
    adv["target_cpc"] = np.round(base_bid * rng.lognormal(0, 0.28, n), 2)
    adv["patience"] = np.round(rng.beta(4, 2, n), 3)
    adv["true_quality"] = np.round(np.exp(rng.normal(0, 0.18, n)) * (0.75 + 0.12 * (adv["rating"] - 3.5)), 4)

    # Joining: some active from day one, the rest join over the 26 weeks
    active0 = rng.random(n) < a["initial_active_share"]
    # later joiners: steady rate, with a pre-festival spike (A7) in the two weeks before Navratri
    wks = np.arange(2, n_weeks + 1)
    w = np.ones(len(wks))
    fest = next((x for x in cfg.get("anomalies", []) if x["id"] == "A7"), None)
    if fest:
        for fw in (fest["week"] - 1, fest["week"]):
            w[wks == fw] *= fest["new_adv_multiplier"]
    join_week = np.where(active0, 1, rng.choice(wks, n, p=w / w.sum())) if len(wks) else np.ones(n, int)
    adv["join_week"] = join_week
    adv["joined_on"] = [(start - pd.Timedelta(days=int(rng.integers(30, 400)))).date() if w == 1
                        else (start + pd.Timedelta(weeks=int(w) - 1, days=int(rng.integers(0, 7)))).date()
                        for w in join_week]
    return adv


def build_campaigns(cfg: dict, adv: pd.DataFrame, zones: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """1-3 campaigns per advertiser. Restaurants -> food_listing; brands -> instamart_search (+ banner)."""
    nb = _neighbours(zones)
    all_zones = list(zones["zone_id"])
    start = pd.Timestamp(cfg["calendar"]["start_date"])
    end = start + pd.Timedelta(weeks=cfg["calendar"]["weeks"]) - pd.Timedelta(days=1)
    banner_share = cfg["advertisers"]["banner_brand_share"]
    rows = []
    cid = 0
    for r in adv.itertuples(index=False):
        k = int(rng.integers(1, cfg["advertisers"]["max_campaigns"] + 1))
        products = []
        if r.advertiser_type == "restaurant":
            products = ["food_listing"] * k
        else:
            products = ["instamart_search"] * max(1, k - 1)
            if rng.random() < banner_share:
                products.append("home_banner")
        split = rng.dirichlet(np.ones(len(products)) * 2)
        for p, s in zip(products, split):
            cid += 1
            if p == "food_listing":
                if r.is_chain:
                    zs = list(rng.choice(all_zones, size=int(rng.integers(4, 11)), replace=False))
                else:
                    zs = [r.home_zone] + list(rng.choice(nb[r.home_zone], size=int(rng.integers(0, 3)), replace=False))
                zs = sorted(set(zs))
            else:
                zs = all_zones if rng.random() < 0.7 else sorted(rng.choice(all_zones, size=int(rng.integers(5, 12)), replace=False))
            joined = pd.Timestamp(r.joined_on)
            cstart = start if joined < start else joined + pd.Timedelta(days=int(rng.integers(0, 4)))
            if rng.random() < 0.15:  # fixed-term campaigns that end mid-window
                cend = min(end, cstart + pd.Timedelta(weeks=int(rng.integers(4, 14))))
            else:
                cend = end
            daily_budget = r.monthly_budget * s / 30.0
            if p == "home_banner":
                bid = float(np.round(rng.lognormal(np.log(165), 0.22), 0))  # CPM bid
                daily_budget = max(daily_budget, 800.0)
            else:
                bid = float(np.round(r.target_cpc * rng.lognormal(0, 0.1), 2))
            rows.append({
                "campaign_id": f"CMP{cid:06d}", "advertiser_id": r.advertiser_id, "product": p,
                "billing_type": "CPM" if p == "home_banner" else "CPC",
                "target_zones": "|".join(zs), "start_date": cstart.date(), "end_date": cend.date(),
                "daily_budget": round(float(daily_budget), 2), "bid": bid,
                "category": r.category,
            })
    return pd.DataFrame(rows)
