from pathlib import Path

import numpy as np
import pandas as pd

# PATHS
ROOT = Path(__file__).resolve().parents[1]

PROCESSED_DIR = ROOT / "data" / "processed"
ANALYTICS_DIR = ROOT / "data" / "analytics"

ANALYTICS_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# LOAD PROCESSED DATA
orders = pd.read_parquet(
    PROCESSED_DIR / "orders_clean.parquet"
)

customers = pd.read_parquet(
    PROCESSED_DIR / "customers_clean.parquet"
)

order_items = pd.read_parquet(
    PROCESSED_DIR / "order_items_clean.parquet"
)

payments_order = pd.read_parquet(
    PROCESSED_DIR / "payments_order_level.parquet"
)

reviews_order = pd.read_parquet(
    PROCESSED_DIR / "reviews_order_level.parquet"
)
products = pd.read_parquet(
    PROCESSED_DIR / "products_clean.parquet"
)

sellers = pd.read_parquet(
    PROCESSED_DIR / "sellers_clean.parquet"
)

geolocation_zip = pd.read_parquet(
    PROCESSED_DIR / "geolocation_zip_level.parquet"
)

print("Processed datasets loaded successfully.")

# INPUT GRAIN VALIDATION

assert orders["order_id"].is_unique

assert customers["customer_id"].is_unique

assert payments_order["order_id"].is_unique

assert reviews_order["order_id"].is_unique

assert (
    order_items[
        ["order_id", "order_item_id"]
    ]
    .duplicated()
    .sum()
    == 0
)
assert products["product_id"].is_unique

assert sellers["seller_id"].is_unique

assert (
    geolocation_zip[
        "geolocation_zip_code_prefix"
    ].is_unique
)

print("Input grain validation passed.")

# BUILD ORDER-ITEM SUMMARY

order_item_summary = (
    order_items
    .groupby(
        "order_id",
        as_index=False
    )
    .agg(
        item_count=(
            "order_item_id",
            "count"
        ),
        unique_product_count=(
            "product_id",
            "nunique"
        ),
        unique_seller_count=(
            "seller_id",
            "nunique"
        ),
        item_sales_value=(
            "price",
            "sum"
        ),
        freight_value=(
            "freight_value",
            "sum"
        ),
    )
)
order_item_summary[
    "item_plus_freight_value"
] = (
    order_item_summary["item_sales_value"]
    + order_item_summary["freight_value"]
)
order_item_summary[
    "is_multi_seller_order"
] = (
    order_item_summary[
        "unique_seller_count"
    ] > 1
)
assert order_item_summary[
    "order_id"
].is_unique, (
    "Order-item summary contains duplicate order IDs."
)
raw_item_sales = (
    order_items["price"].sum()
)
summary_item_sales = (
    order_item_summary[
        "item_sales_value"
    ].sum()
)
assert np.isclose(
    raw_item_sales,
    summary_item_sales
), "Item aggregation changed total item sales."
assert np.isclose(
    order_items["freight_value"].sum(),
    order_item_summary["freight_value"].sum()
), "Item aggregation changed total freight."

# BUILD FACT_ORDERS

fact_orders = orders.copy()
fact_orders = fact_orders.merge(
    customers[
        [
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
        ]
    ],
    on="customer_id",
    how="left",
    validate="one_to_one",
)
assert len(fact_orders) == len(orders), (
    "Customer join changed the order row count."
)
assert fact_orders[
    "customer_unique_id"
].notna().all(), (
    "Some orders failed to match a customer."
)
fact_orders = fact_orders.merge(
    order_item_summary,
    on="order_id",
    how="left",
    validate="one_to_one",
)
assert len(fact_orders) == len(orders), (
    "Order-item summary join changed order row count."
)
fact_orders = fact_orders.merge(
    payments_order,
    on="order_id",
    how="left",
    validate="one_to_one",
)
assert len(fact_orders) == len(orders), (
    "Payment join changed order row count."
)
fact_orders = fact_orders.merge(
    reviews_order[
        [
            "order_id",
            "review_score",
            "has_review_comment",
            "review_comment_length",
        ]
    ],
    on="order_id",
    how="left",
    validate="one_to_one",
)
assert len(fact_orders) == len(orders), (
    "Review join changed order row count."
)
assert fact_orders["order_id"].is_unique, (
    "fact_orders contains duplicate order IDs."
)

assert len(fact_orders) == 99441, (
    "fact_orders does not contain the expected number of orders."
)
fact_orders["purchase_date"] = (
    fact_orders[
        "order_purchase_timestamp"
    ].dt.normalize()
)
fact_orders["purchase_year"] = (
    fact_orders[
        "order_purchase_timestamp"
    ].dt.year
)
fact_orders["purchase_month"] = (
    fact_orders[
        "order_purchase_timestamp"
    ].dt.month
)
fact_orders["purchase_month_name"] = (
    fact_orders[
        "order_purchase_timestamp"
    ].dt.month_name()
)
fact_orders["purchase_day_of_week"] = (
    fact_orders[
        "order_purchase_timestamp"
    ].dt.day_name()
)
fact_orders["purchase_hour"] = (
    fact_orders[
        "order_purchase_timestamp"
    ].dt.hour
)
fact_orders["purchase_year_month"] = (
    fact_orders[
        "order_purchase_timestamp"
    ].dt.to_period("M").astype(str)
)
fact_orders["is_delivered"] = (
    fact_orders["order_status"]
    == "delivered"
)
fact_orders["is_canceled"] = (
    fact_orders["order_status"]
    == "canceled"
)
print(
    "\n=== ORDERS WITHOUT ITEM SUMMARY BY STATUS ==="
)

print(
    fact_orders.loc[
        fact_orders[
            "item_count"
        ].isna(),
        "order_status"
    ]
    .value_counts()
)
print(
    "\nOrders without payment summary:",
    f"{fact_orders['total_payment_value'].isna().sum():,}"
)

print(
    "Orders without review:",
    f"{fact_orders['review_score'].isna().sum():,}"
)
reconciliation_mask = (
    fact_orders[
        "item_plus_freight_value"
    ].notna()
    & fact_orders[
        "total_payment_value"
    ].notna()
)
fact_orders.loc[
    reconciliation_mask,
    "payment_minus_item_freight"
] = (
    fact_orders.loc[
        reconciliation_mask,
        "total_payment_value"
    ]
    - fact_orders.loc[
        reconciliation_mask,
        "item_plus_freight_value"
    ]
)
print(
    "\n=== PAYMENT VS ITEM+FREIGHT RECONCILIATION ==="
)

print(
    fact_orders[
        "payment_minus_item_freight"
    ].describe()
)
print(
    "\n=== FACT_ORDERS SUMMARY ==="
)

print(
    "Rows:",
    f"{len(fact_orders):,}"
)

print(
    "Columns:",
    len(fact_orders.columns)
)

print(
    "Unique order IDs:",
    f"{fact_orders['order_id'].nunique():,}"
)

print(
    "Unique customers:",
    f"{fact_orders['customer_unique_id'].nunique():,}"
)

# EXPORT FACT_ORDERS

fact_orders_path = (
    ANALYTICS_DIR / "fact_orders.parquet"
)

fact_orders.to_parquet(
    fact_orders_path,
    index=False
)

print(
    f"\nfact_orders exported -> "
    f"{fact_orders_path}"
)
fact_orders_check = pd.read_parquet(
    fact_orders_path
)

assert len(fact_orders_check) == len(fact_orders)

assert fact_orders_check[
    "order_id"
].is_unique

print(
    "fact_orders export validation passed."
)


# BUILD FACT_ORDER_ITEMS

fact_order_items = order_items.copy()
fact_order_items["item_total_value"] = (
    fact_order_items["price"]
    + fact_order_items["freight_value"]
)
fact_order_items = fact_order_items.merge(
    products[
        [
            "product_id",
            "product_category_name",
            "product_category_name_english",
            "product_name_length",
            "product_description_length",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
            "product_volume_cm3",
            "has_product_metadata",
            "has_complete_dimensions",
        ]
    ],
    on="product_id",
    how="left",
    validate="many_to_one",
)
assert len(fact_order_items) == len(order_items), (
    "Product join changed the order-item row count."
)
assert (
    fact_order_items[
        "product_category_name_english"
    ]
    .notna()
    .all()
), "Some order items lack cleaned product categories."
fact_order_items = fact_order_items.merge(
    sellers[
        [
            "seller_id",
            "seller_zip_code_prefix",
            "seller_city",
            "seller_state",
        ]
    ],
    on="seller_id",
    how="left",
    validate="many_to_one",
)
assert len(fact_order_items) == len(order_items), (
    "Seller join changed the order-item row count."
)
order_context = fact_orders[
    [
        "order_id",
        "customer_id",
        "customer_unique_id",
        "order_status",
        "order_purchase_timestamp",
        "purchase_date",
        "purchase_year",
        "purchase_month",
        "purchase_month_name",
        "purchase_year_month",
        "purchase_day_of_week",
        "purchase_hour",
        "customer_zip_code_prefix",
        "customer_city",
        "customer_state",
        "is_delivered",
        "is_canceled",
    ]
].copy()
fact_order_items = fact_order_items.merge(
    order_context,
    on="order_id",
    how="left",
    validate="many_to_one",
)
assert len(fact_order_items) == len(order_items), (
    "Order context join changed the order-item row count."
)
assert fact_order_items[
    "customer_unique_id"
].notna().all(), (
    "Some order items failed to match order/customer context."
)

assert fact_order_items[
    "seller_state"
].notna().all(), (
    "Some order items failed to match seller data."
)
assert (
    fact_order_items[
        ["order_id", "order_item_id"]
    ]
    .duplicated()
    .sum()
    == 0
), (
    "fact_order_items contains duplicate "
    "order-item keys."
)
assert np.isclose(
    fact_order_items["price"].sum(),
    order_items["price"].sum()
), "fact_order_items changed total item sales."
assert np.isclose(
    fact_order_items["freight_value"].sum(),
    order_items["freight_value"].sum()
), "fact_order_items changed total freight."
assert np.isclose(
    fact_order_items["item_total_value"].sum(),
    (
        order_items["price"]
        + order_items["freight_value"]
    ).sum()
), "fact_order_items changed total item+freight value."
item_fact_reconciliation = (
    fact_order_items
    .groupby(
        "order_id",
        as_index=False
    )
    .agg(
        item_count_check=(
            "order_item_id",
            "count"
        ),
        item_sales_check=(
            "price",
            "sum"
        ),
        freight_check=(
            "freight_value",
            "sum"
        ),
    )
)
order_reconciliation = (
    fact_orders[
        [
            "order_id",
            "item_count",
            "item_sales_value",
            "freight_value",
        ]
    ]
    .merge(
        item_fact_reconciliation,
        on="order_id",
        how="inner",
        validate="one_to_one",
    )
)
assert (
    order_reconciliation["item_count"]
    == order_reconciliation["item_count_check"]
).all(), (
    "Item counts do not reconcile between fact tables."
)
assert np.allclose(
    order_reconciliation["item_sales_value"],
    order_reconciliation["item_sales_check"],
), (
    "Item sales do not reconcile between fact tables."
)
assert np.allclose(
    order_reconciliation["freight_value"],
    order_reconciliation["freight_check"],
), (
    "Freight does not reconcile between fact tables."
)
print(
    "\n=== TOP PRODUCT CATEGORIES BY ITEM ROWS ==="
)

print(
    fact_order_items[
        "product_category_name_english"
    ]
    .value_counts()
    .head(10)
)
print(
    "\n=== TOP SELLERS BY ITEM ROWS ==="
)

print(
    fact_order_items[
        "seller_id"
    ]
    .value_counts()
    .head(10)
)
print(
    "\n=== FACT_ORDER_ITEMS SUMMARY ==="
)

print(
    "Rows:",
    f"{len(fact_order_items):,}"
)

print(
    "Columns:",
    len(fact_order_items.columns)
)

print(
    "Unique orders:",
    f"{fact_order_items['order_id'].nunique():,}"
)

print(
    "Unique products:",
    f"{fact_order_items['product_id'].nunique():,}"
)

print(
    "Unique sellers:",
    f"{fact_order_items['seller_id'].nunique():,}"
)

print(
    "Total item sales:",
    f"{fact_order_items['price'].sum():,.2f}"
)

print(
    "Total freight:",
    f"{fact_order_items['freight_value'].sum():,.2f}"
)

# EXPORT FACT_ORDER_ITEMS

fact_order_items_path = (
    ANALYTICS_DIR
    / "fact_order_items.parquet"
)

fact_order_items.to_parquet(
    fact_order_items_path,
    index=False
)

print(
    f"\nfact_order_items exported -> "
    f"{fact_order_items_path}"
)
fact_order_items_check = pd.read_parquet(
    fact_order_items_path
)

assert (
    len(fact_order_items_check)
    == len(fact_order_items)
)

assert (
    fact_order_items_check[
        ["order_id", "order_item_id"]
    ]
    .duplicated()
    .sum()
    == 0
)

print(
    "fact_order_items export validation passed."
)

# BUILD DIM_PRODUCT


dim_product = products[
    [
        "product_id",
        "product_category_name",
        "product_category_name_english",
        "product_name_length",
        "product_description_length",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
        "product_volume_cm3",
        "has_product_metadata",
        "has_complete_dimensions",
    ]
].copy()
assert dim_product["product_id"].is_unique, (
    "dim_product contains duplicate product IDs."
)

assert len(dim_product) == 32951, (
    "dim_product does not contain the expected number of products."
)

assert (
    dim_product["product_category_name_english"]
    .notna()
    .all()
), "dim_product contains missing analytical categories."
dim_product["has_known_category"] = (
    dim_product[
        "product_category_name_english"
    ] != "unknown"
)

# BUILD DIM_SELLER


dim_seller = sellers[
    [
        "seller_id",
        "seller_zip_code_prefix",
        "seller_city",
        "seller_state",
    ]
].copy()
dim_seller = dim_seller.merge(
    geolocation_zip[
        [
            "geolocation_zip_code_prefix",
            "latitude",
            "longitude",
            "geolocation_observation_count",
        ]
    ],
    left_on="seller_zip_code_prefix",
    right_on="geolocation_zip_code_prefix",
    how="left",
    validate="many_to_one",
)
dim_seller = dim_seller.drop(
    columns="geolocation_zip_code_prefix"
)
dim_seller = dim_seller.rename(
    columns={
        "latitude": "seller_latitude",
        "longitude": "seller_longitude",
        "geolocation_observation_count":
            "seller_geo_observation_count",
    }
)
dim_seller["has_seller_geolocation"] = (
    dim_seller["seller_latitude"].notna()
    & dim_seller["seller_longitude"].notna()
)
assert dim_seller["seller_id"].is_unique, (
    "dim_seller contains duplicate seller IDs."
)

assert len(dim_seller) == 3095, (
    "dim_seller does not contain the expected number of sellers."
)
print(
    "\nSeller dimension geolocation coverage:"
)

print(
    dim_seller[
        "has_seller_geolocation"
    ].value_counts(dropna=False)
)

# BUILD DIM_CUSTOMER

customer_history = fact_orders[
    [
        "customer_id",
        "customer_unique_id",
        "customer_zip_code_prefix",
        "customer_city",
        "customer_state",
        "order_id",
        "order_purchase_timestamp",
    ]
].copy()
customer_lifecycle = (
    customer_history
    .groupby(
        "customer_unique_id",
        as_index=False
    )
    .agg(
        first_purchase_timestamp=(
            "order_purchase_timestamp",
            "min"
        ),
        last_purchase_timestamp=(
            "order_purchase_timestamp",
            "max"
        ),
        lifetime_order_count=(
            "order_id",
            "nunique"
        ),
    )
)
latest_customer_record = (
    customer_history
    .sort_values(
        by=[
            "customer_unique_id",
            "order_purchase_timestamp",
            "customer_id",
        ]
    )
    .drop_duplicates(
        subset="customer_unique_id",
        keep="last"
    )
    .copy()
)
latest_customer_record = (
    latest_customer_record.rename(
        columns={
            "customer_id":
                "latest_customer_id",
            "customer_zip_code_prefix":
                "latest_customer_zip_code_prefix",
            "customer_city":
                "latest_customer_city",
            "customer_state":
                "latest_customer_state",
        }
    )
)
latest_customer_record = (
    latest_customer_record[
        [
            "customer_unique_id",
            "latest_customer_id",
            "latest_customer_zip_code_prefix",
            "latest_customer_city",
            "latest_customer_state",
        ]
    ]
)
dim_customer = customer_lifecycle.merge(
    latest_customer_record,
    on="customer_unique_id",
    how="left",
    validate="one_to_one",
)
dim_customer["is_repeat_customer"] = (
    dim_customer["lifetime_order_count"] > 1
)
dim_customer["observed_customer_tenure_days"] = (
    dim_customer["last_purchase_timestamp"]
    - dim_customer["first_purchase_timestamp"]
).dt.total_seconds() / 86400
dim_customer = dim_customer.merge(
    geolocation_zip[
        [
            "geolocation_zip_code_prefix",
            "latitude",
            "longitude",
            "geolocation_observation_count",
        ]
    ],
    left_on="latest_customer_zip_code_prefix",
    right_on="geolocation_zip_code_prefix",
    how="left",
    validate="many_to_one",
)
dim_customer = dim_customer.drop(
    columns="geolocation_zip_code_prefix"
)
dim_customer = dim_customer.rename(
    columns={
        "latitude":
            "latest_customer_latitude",
        "longitude":
            "latest_customer_longitude",
        "geolocation_observation_count":
            "latest_customer_geo_observation_count",
    }
)
dim_customer[
    "has_latest_customer_geolocation"
] = (
    dim_customer[
        "latest_customer_latitude"
    ].notna()
    & dim_customer[
        "latest_customer_longitude"
    ].notna()
)
assert (
    dim_customer["customer_unique_id"]
    .is_unique
), "dim_customer contains duplicate customers."

assert len(dim_customer) == 96096, (
    "dim_customer does not contain "
    "the expected number of unique customers."
)
assert (
    dim_customer[
        "lifetime_order_count"
    ] >= 1
).all(), "Customer with zero observed orders detected."
assert (
    dim_customer[
        "observed_customer_tenure_days"
    ] >= 0
).all(), "Negative customer tenure detected."
assert (
    dim_customer[
        "lifetime_order_count"
    ].sum()
    == len(fact_orders)
), (
    "Customer lifetime order counts "
    "do not reconcile with fact_orders."
)
print(
    "\n=== DIM_CUSTOMER SUMMARY ==="
)

print(
    "Unique customers:",
    f"{len(dim_customer):,}"
)

print(
    "One-time customers:",
    f"{(
        ~dim_customer[
            'is_repeat_customer'
        ]
    ).sum():,}"
)

print(
    "Repeat customers:",
    f"{dim_customer[
        'is_repeat_customer'
    ].sum():,}"
)

print(
    "Maximum observed orders by one customer:",
    dim_customer[
        "lifetime_order_count"
    ].max()
)

print(
    "Customers without latest geolocation:",
    f"{(
        ~dim_customer[
            'has_latest_customer_geolocation'
        ]
    ).sum():,}"
)
print(
    "\n=== DIMENSION TABLE SUMMARY ==="
)

print(
    f"dim_product  : {len(dim_product):,} rows"
)

print(
    f"dim_seller   : {len(dim_seller):,} rows"
)

print(
    f"dim_customer : {len(dim_customer):,} rows"
)
# EXPORT DIMENSION TABLES


dimension_tables = {
    "dim_product": dim_product,
    "dim_seller": dim_seller,
    "dim_customer": dim_customer,
}

for table_name, df in dimension_tables.items():

    output_path = (
        ANALYTICS_DIR
        / f"{table_name}.parquet"
    )

    df.to_parquet(
        output_path,
        index=False
    )

    print(
        f"{table_name} exported -> "
        f"{output_path}"
    )
print(
    "\n=== VERIFYING DIMENSION EXPORTS ==="
)

dimension_keys = {
    "dim_product": "product_id",
    "dim_seller": "seller_id",
    "dim_customer": "customer_unique_id",
}

for table_name, key_column in dimension_keys.items():

    output_path = (
        ANALYTICS_DIR
        / f"{table_name}.parquet"
    )

    check_df = pd.read_parquet(
        output_path
    )

    assert check_df[
        key_column
    ].is_unique, (
        f"{table_name}: key is not unique "
        f"after export."
    )

    print(
        f"{table_name:15} OK"
    )

# BUILD DIM_DATE

order_date_columns = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]
calendar_start = min(
    orders[col].min()
    for col in order_date_columns
    if orders[col].notna().any()
).normalize()

calendar_end = max(
    orders[col].max()
    for col in order_date_columns
    if orders[col].notna().any()
).normalize()
print(
    "\nCalendar start:",
    calendar_start
)

print(
    "Calendar end:",
    calendar_end
)
date_range = pd.date_range(
    start=calendar_start,
    end=calendar_end,
    freq="D"
)
dim_date = pd.DataFrame({
    "date": date_range
})
dim_date["date_key"] = (
    dim_date["date"]
    .dt.strftime("%Y%m%d")
    .astype(int)
)
dim_date["year"] = (
    dim_date["date"].dt.year
)
dim_date["quarter"] = (
    dim_date["date"].dt.quarter
)
dim_date["quarter_name"] = (
    "Q"
    + dim_date["quarter"].astype(str)
)
dim_date["month_number"] = (
    dim_date["date"].dt.month
)
dim_date["month_name"] = (
    dim_date["date"].dt.month_name()
)
dim_date["month_name_short"] = (
    dim_date["date"].dt.strftime("%b")
)
dim_date["year_month"] = (
    dim_date["date"]
    .dt.to_period("M")
    .astype(str)
)
dim_date["year_month_key"] = (
    dim_date["year"] * 100
    + dim_date["month_number"]
)
dim_date["day_of_month"] = (
    dim_date["date"].dt.day
)
dim_date["day_of_week_number"] = (
    dim_date["date"].dt.dayofweek + 1
)
dim_date["day_name"] = (
    dim_date["date"].dt.day_name()
)
dim_date["is_weekend"] = (
    dim_date["day_of_week_number"] >= 6
)
iso_calendar = (
    dim_date["date"]
    .dt.isocalendar()
)
dim_date["iso_year"] = (
    iso_calendar["year"]
    .astype(int)
)

dim_date["iso_week"] = (
    iso_calendar["week"]
    .astype(int)
)
dim_date["year_week"] = (
    dim_date["iso_year"].astype(str)
    + "-W"
    + dim_date["iso_week"]
      .astype(str)
      .str.zfill(2)
)
dim_date["day_of_year"] = (
    dim_date["date"].dt.dayofyear
)
dim_date["month_start_date"] = (
    dim_date["date"]
    .dt.to_period("M")
    .dt.to_timestamp()
)
dim_date["quarter_start_date"] = (
    dim_date["date"]
    .dt.to_period("Q")
    .dt.start_time
)
assert dim_date["date"].is_unique, (
    "dim_date contains duplicate dates."
)
assert dim_date["date_key"].is_unique, (
    "dim_date contains duplicate date keys."
)
expected_date_count = (
    calendar_end - calendar_start
).days + 1
assert len(dim_date) == expected_date_count, (
    "dim_date does not contain every calendar day."
)
purchase_dates = (
    fact_orders["purchase_date"]
    .dropna()
    .drop_duplicates()
)
assert purchase_dates.isin(
    dim_date["date"]
).all(), (
    "Some fact_orders purchase dates "
    "are missing from dim_date."
)
assert (
    fact_order_items["purchase_date"]
    .dropna()
    .isin(dim_date["date"])
    .all()
), (
    "Some fact_order_items purchase dates "
    "are missing from dim_date."
)
print(
    "\n=== DIM_DATE SUMMARY ==="
)

print(
    "Calendar start:",
    dim_date["date"].min()
)

print(
    "Calendar end:",
    dim_date["date"].max()
)

print(
    "Calendar days:",
    f"{len(dim_date):,}"
)

print(
    "Calendar years:",
    sorted(
        dim_date["year"]
        .unique()
        .tolist()
    )
)
dim_date_path = (
    ANALYTICS_DIR
    / "dim_date.parquet"
)

dim_date.to_parquet(
    dim_date_path,
    index=False
)

print(
    f"\ndim_date exported -> "
    f"{dim_date_path}"
)
dim_date_check = pd.read_parquet(
    dim_date_path
)

assert dim_date_check["date"].is_unique

assert len(dim_date_check) == len(dim_date)

print(
    "dim_date export validation passed."
)

# FINAL ANALYTICS MODEL VALIDATION


assert (
    fact_orders["customer_unique_id"]
    .isin(dim_customer["customer_unique_id"])
    .all()
), (
    "fact_orders contains customers "
    "missing from dim_customer."
)
assert (
    fact_order_items["product_id"]
    .isin(dim_product["product_id"])
    .all()
), (
    "fact_order_items contains products "
    "missing from dim_product."
)
assert (
    fact_order_items["seller_id"]
    .isin(dim_seller["seller_id"])
    .all()
), (
    "fact_order_items contains sellers "
    "missing from dim_seller."
)
assert (
    fact_orders["purchase_date"]
    .isin(dim_date["date"])
    .all()
)

assert (
    fact_order_items["purchase_date"]
    .isin(dim_date["date"])
    .all()
)
print(
    "\n============================================"
)

print(
    "ANALYTICS MODEL VALIDATION PASSED"
)

print(
    "============================================"
)

print(
    "\nModel tables:"
)

print(
    f"fact_orders       {len(fact_orders):>10,} rows"
)

print(
    f"fact_order_items  {len(fact_order_items):>10,} rows"
)

print(
    f"dim_customer      {len(dim_customer):>10,} rows"
)

print(
    f"dim_product       {len(dim_product):>10,} rows"
)

print(
    f"dim_seller        {len(dim_seller):>10,} rows"
)

print(
    f"dim_date          {len(dim_date):>10,} rows"
)
