from pathlib import Path
from duckdb import df
import numpy as np
import pandas as pd

# PATHS

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

#RAW DATA

customers = pd.read_csv(
    RAW_DIR / "olist_customers_dataset.csv"
)

geolocation = pd.read_csv(
    RAW_DIR / "olist_geolocation_dataset.csv"
)

order_items = pd.read_csv(
    RAW_DIR / "olist_order_items_dataset.csv"
)

payments = pd.read_csv(
    RAW_DIR / "olist_order_payments_dataset.csv"
)

reviews = pd.read_csv(
    RAW_DIR / "olist_order_reviews_dataset.csv"
)

orders = pd.read_csv(
    RAW_DIR / "olist_orders_dataset.csv"
)

products = pd.read_csv(
    RAW_DIR / "olist_products_dataset.csv"
)

sellers = pd.read_csv(
    RAW_DIR / "olist_sellers_dataset.csv"
)

categories = pd.read_csv(
    RAW_DIR / "product_category_name_translation.csv"
)

print("Raw datasets loaded successfully.")

# CONVERT DATETIME COLUMNS

def convert_datetime_columns(df, columns, table_name):
 
    print(f"\nConverting datetime columns in {table_name}...")

    for col in columns:

        original = df[col].copy()

        original_non_missing = original.notna()

        df[col] = pd.to_datetime(
            original,
            format="mixed",
            errors="coerce",
            dayfirst=False
        )

        failed_mask = (
            original_non_missing
            & df[col].isna()
        )

        failed_count = failed_mask.sum()

        print(
            f"{col}: "
            f"{df[col].isna().sum():,} missing "
            f"({failed_count:,} failed during parsing)"
        )

        if failed_count > 0:
            print("Examples of failed values:")
            print(
                original.loc[failed_mask]
                .head(5)
                .tolist()
            )

            raise ValueError(
                f"{table_name}.{col}: "
                f"{failed_count} timestamp values could not be parsed."
            )

    return df

order_datetime_columns = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]

order_item_datetime_columns = [
    "shipping_limit_date",
]

review_datetime_columns = [
    "review_creation_date",
    "review_answer_timestamp",
]
orders = convert_datetime_columns(
    orders,
    order_datetime_columns,
    "orders"
)

order_items = convert_datetime_columns(
    order_items,
    order_item_datetime_columns,
    "order_items"
)

reviews = convert_datetime_columns(
    reviews,
    review_datetime_columns,
    "reviews"
)

# CHRONOLOGICAL VALIDATION

def check_time_order(
    df,
    earlier_col,
    later_col,
    check_name
):
 
    valid_mask = (
        df[earlier_col].notna()
        & df[later_col].notna()
    )

    invalid_mask = (
        valid_mask
        & (df[later_col] < df[earlier_col])
    )

    invalid_count = invalid_mask.sum()

    print(
        f"{check_name}: "
        f"{invalid_count:,} chronological reversals"
    )

    return df.loc[
        invalid_mask,
        [
            "order_id",
            earlier_col,
            later_col
        ]
    ].copy()

purchase_approval_errors = check_time_order(
    orders,
    "order_purchase_timestamp",
    "order_approved_at",
    "Purchase -> approval"
)

purchase_carrier_errors = check_time_order(
    orders,
    "order_purchase_timestamp",
    "order_delivered_carrier_date",
    "Purchase -> carrier"
)

purchase_delivery_errors = check_time_order(
    orders,
    "order_purchase_timestamp",
    "order_delivered_customer_date",
    "Purchase -> customer delivery"
)

purchase_estimate_errors = check_time_order(
    orders,
    "order_purchase_timestamp",
    "order_estimated_delivery_date",
    "Purchase -> estimated delivery"
)

approval_carrier_errors = check_time_order(
    orders,
    "order_approved_at",
    "order_delivered_carrier_date",
    "Approval -> carrier"
)

approval_delivery_errors = check_time_order(
    orders,
    "order_approved_at",
    "order_delivered_customer_date",
    "Approval -> customer delivery"
)

carrier_delivery_errors = check_time_order(
    orders,
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "Carrier -> customer delivery"
)
review_time_errors = check_time_order(
    reviews,
    "review_creation_date",
    "review_answer_timestamp",
    "Review creation -> answer"
)

chronology_error_tables = {
    "purchase_approval": purchase_approval_errors,
    "purchase_carrier": purchase_carrier_errors,
    "purchase_delivery": purchase_delivery_errors,
    "purchase_estimate": purchase_estimate_errors,
    "approval_carrier": approval_carrier_errors,
    "approval_delivery": approval_delivery_errors,
    "carrier_delivery": carrier_delivery_errors,
    "review_timing": review_time_errors,
}

print("\n=== CHRONOLOGY ERROR EXAMPLES ===")

for name, error_df in chronology_error_tables.items():

    if len(error_df) > 0:
        print(f"\n{name}:")
        print(error_df.head())

if len(purchase_delivery_errors) > 0:
    purchase_delivery_errors["difference_hours"] = (
        purchase_delivery_errors["order_delivered_customer_date"]
        - purchase_delivery_errors["order_purchase_timestamp"]
    ).dt.total_seconds() / 3600

if len(carrier_delivery_errors) > 0:
    carrier_delivery_errors["difference_hours"] = (
        carrier_delivery_errors["order_delivered_customer_date"]
        - carrier_delivery_errors["order_delivered_carrier_date"]
    ).dt.total_seconds() / 3600

if len(approval_carrier_errors) > 0:
    approval_carrier_errors["difference_hours"] = (
        approval_carrier_errors["order_delivered_carrier_date"]
        - approval_carrier_errors["order_approved_at"]
    ).dt.total_seconds() / 3600

    order_items_with_purchase = order_items.merge(
    orders[
        [
            "order_id",
            "order_purchase_timestamp"
        ]
    ],
    on="order_id",
    how="left",
    validate="many_to_one"
)
    assert len(order_items_with_purchase) == len(order_items), (
    "Joining purchase timestamps changed the number of order-item rows."
)
    shipping_limit_errors = check_time_order(
    order_items_with_purchase,
    "order_purchase_timestamp",
    "shipping_limit_date",
    "Purchase -> shipping limit"
)
   
# INSPECT ESTIMATED DELIVERY TIME COMPONENT

estimated_times = (
    orders["order_estimated_delivery_date"]
    .dt.time
    .value_counts()
)

print("\nMost common estimated delivery times:")
print(estimated_times.head(10))

print(
    "\nUnique estimated delivery times:",
    orders["order_estimated_delivery_date"]
    .dt.time
    .nunique()
)

# CHRONOLOGY REVERSAL MAGNITUDES


def summarize_reversal_hours(
    error_df,
    earlier_col,
    later_col,
    name
):
    if error_df.empty:
        print(f"\n{name}: no reversals")
        return

    differences = (
        error_df[later_col]
        - error_df[earlier_col]
    ).dt.total_seconds() / 3600

    print(f"\n=== {name} reversal hours ===")
    print(differences.describe())

summarize_reversal_hours(
    purchase_carrier_errors,
    "order_purchase_timestamp",
    "order_delivered_carrier_date",
    "Purchase -> carrier"
)

summarize_reversal_hours(
    approval_carrier_errors,
    "order_approved_at",
    "order_delivered_carrier_date",
    "Approval -> carrier"
)

summarize_reversal_hours(
    approval_delivery_errors,
    "order_approved_at",
    "order_delivered_customer_date",
    "Approval -> delivery"
)

summarize_reversal_hours(
    carrier_delivery_errors,
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "Carrier -> delivery"
)

# CREATE ORDER TIME METRICS
orders["delivery_days"] = (
    orders["order_delivered_customer_date"]
    - orders["order_purchase_timestamp"]
).dt.total_seconds() / 86400

orders["approval_hours"] = (
    orders["order_approved_at"]
    - orders["order_purchase_timestamp"]
).dt.total_seconds() / 3600

orders["purchase_to_carrier_days"] = (
    orders["order_delivered_carrier_date"]
    - orders["order_purchase_timestamp"]
).dt.total_seconds() / 86400

orders.loc[
    orders["purchase_to_carrier_days"] < 0,
    "purchase_to_carrier_days"
] = np.nan

orders["approval_to_carrier_days"] = (
    orders["order_delivered_carrier_date"]
    - orders["order_approved_at"]
).dt.total_seconds() / 86400

orders.loc[
    orders["approval_to_carrier_days"] < 0,
    "approval_to_carrier_days"
] = np.nan

orders["carrier_to_customer_days"] = (
    orders["order_delivered_customer_date"]
    - orders["order_delivered_carrier_date"]
).dt.total_seconds() / 86400

orders.loc[
    orders["carrier_to_customer_days"] < 0,
    "carrier_to_customer_days"
] = np.nan

orders["promised_delivery_days"] = (
    orders["order_estimated_delivery_date"]
    - orders["order_purchase_timestamp"]
).dt.total_seconds() / 86400

actual_delivery_date = (
    orders["order_delivered_customer_date"]
    .dt.normalize()
)

estimated_delivery_date = (
    orders["order_estimated_delivery_date"]
    .dt.normalize()
)

orders["delivery_delay_days"] = (
    actual_delivery_date
    - estimated_delivery_date
).dt.days

orders["is_late"] = pd.NA
delivery_date_available = (
    orders["order_delivered_customer_date"].notna()
    & orders["order_estimated_delivery_date"].notna()
)
orders.loc[
    delivery_date_available,
    "is_late"
] = (
    orders.loc[
        delivery_date_available,
        "delivery_delay_days"
    ] > 0
)
orders["is_late"] = orders["is_late"].astype("boolean")

# VALIDATE ORDER TIME METRICS

assert (
    orders["delivery_days"]
    .dropna()
    .ge(0)
    .all()
), "Negative delivery_days detected."

assert (
    orders["approval_hours"]
    .dropna()
    .ge(0)
    .all()
), "Negative approval_hours detected."

assert (
    orders["purchase_to_carrier_days"]
    .dropna()
    .ge(0)
    .all()
), "Negative purchase_to_carrier_days detected."

assert (
    orders["approval_to_carrier_days"]
    .dropna()
    .ge(0)
    .all()
), "Negative approval_to_carrier_days detected."

assert (
    orders["carrier_to_customer_days"]
    .dropna()
    .ge(0)
    .all()
), "Negative carrier_to_customer_days detected."

assert (
    orders["promised_delivery_days"]
    .dropna()
    .ge(0)
    .all()
), "Negative promised_delivery_days detected."

print("\nOrder time metric validation passed.")

time_metric_columns = [
    "approval_hours",
    "purchase_to_carrier_days",
    "approval_to_carrier_days",
    "carrier_to_customer_days",
    "delivery_days",
    "promised_delivery_days",
    "delivery_delay_days",
]

print("\n=== ORDER TIME METRIC SUMMARY ===")
print(
    orders[time_metric_columns]
    .describe()
    .T
)

print("\nLate-delivery classification:")

print(
    orders["is_late"]
    .value_counts(dropna=False)
)

print("\nLate-delivery percentage among classifiable orders:")

print(
    orders["is_late"]
    .dropna()
    .mean() * 100
)

# BUILD ORDER-LEVEL REVIEW TABLE

reviews_sorted = reviews.sort_values(
    by=[
        "order_id",
        "review_answer_timestamp",
        "review_creation_date",
        "review_id",
    ]
)

reviews_order_level = (
    reviews_sorted
    .drop_duplicates(
        subset="order_id",
        keep="last"
    )
    .copy()
)

assert reviews_order_level["order_id"].is_unique, (
    "Order-level review table contains duplicate order IDs."
)

print("\n=== REVIEW CLEANING SUMMARY ===")

print(
    "Original review rows:",
    f"{len(reviews):,}"
)

print(
    "Unique reviewed orders:",
    f"{reviews['order_id'].nunique():,}"
)

print(
    "Order-level review rows:",
    f"{len(reviews_order_level):,}"
)

print(
    "Extra review records resolved:",
    f"{len(reviews) - len(reviews_order_level):,}"
)

reviewed_order_ids = set(
    reviews_order_level["order_id"]
)

all_order_ids = set(
    orders["order_id"]
)

orders_without_review = (
    all_order_ids
    - reviewed_order_ids
)

print(
    "Orders without a review:",
    f"{len(orders_without_review):,}"
)

print(
    "Review coverage:",
    f"{len(reviewed_order_ids) / len(all_order_ids) * 100:.2f}%"
)

assert (
    reviews_order_level["review_score"]
    .between(1, 5)
    .all()
), "Review scores outside the expected 1–5 range detected."

print(
    "\nOrder-level review score distribution:"
)

print(
    reviews_order_level["review_score"]
    .value_counts()
    .sort_index()
)

reviews_order_level["has_review_comment"] = (
    reviews_order_level["review_comment_message"]
    .notna()
)

reviews_order_level["review_comment_length"] = (
    reviews_order_level["review_comment_message"]
    .fillna("")
    .str.len()
)

orders_with_reviews_test = orders.merge(
    reviews_order_level[
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

assert len(orders_with_reviews_test) == len(orders), (
    "Review join changed the number of order rows."
)

print(
    "\nOrders with no order-level review score:",
    f"{orders_with_reviews_test['review_score'].isna().sum():,}"
)


# CLEAN PRODUCT DATA

products_clean = products.copy()

products_clean = products_clean.rename(
    columns={
        "product_name_lenght": "product_name_length",
        "product_description_lenght": "product_description_length",
    }
)

assert categories["product_category_name"].is_unique, (
    "Category translation table contains duplicate source categories."
)

products_clean = products_clean.merge(
    categories,
    on="product_category_name",
    how="left",
    validate="many_to_one",
)

assert len(products_clean) == len(products), (
    "Category translation join changed the number of product rows."
)

manual_category_translations = {
    "pc_gamer": "gaming_pc",
    "portateis_cozinha_e_preparadores_de_alimentos":
        "portable_kitchen_and_food_preparation",
}

missing_translation_mask = (
    products_clean["product_category_name"].notna()
    & products_clean["product_category_name_english"].isna()
)

products_clean.loc[
    missing_translation_mask,
    "product_category_name_english"
] = (
    products_clean.loc[
        missing_translation_mask,
        "product_category_name"
    ]
    .map(manual_category_translations)
)

known_category_missing_translation = products_clean.loc[
    products_clean["product_category_name"].notna()
    & products_clean["product_category_name_english"].isna()
]

print(
    "\nKnown categories still missing English translation:",
    len(known_category_missing_translation)
)

products_clean["product_category_name_english"] = (
    products_clean["product_category_name_english"]
    .fillna("unknown")
)

products_clean["has_product_metadata"] = (
    products_clean["product_category_name"].notna()
    & products_clean["product_name_length"].notna()
    & products_clean["product_description_length"].notna()
    & products_clean["product_photos_qty"].notna()
)

print(
    "\nProduct metadata completeness:"
)

print(
    products_clean["has_product_metadata"]
    .value_counts(dropna=False)
)

dimension_columns = [
    "product_weight_g",
    "product_length_cm",
    "product_height_cm",
    "product_width_cm",
]

products_clean["has_complete_dimensions"] = (
    products_clean[dimension_columns]
    .notna()
    .all(axis=1)
)

products_clean["product_volume_cm3"] = (
    products_clean["product_length_cm"]
    * products_clean["product_height_cm"]
    * products_clean["product_width_cm"]
)

physical_columns = [
    "product_weight_g",
    "product_length_cm",
    "product_height_cm",
    "product_width_cm",
]

print("\n=== PRODUCT PHYSICAL VALUE CHECKS ===")

for col in physical_columns:

    print(
        f"{col}: "
        f"negative={(products_clean[col] < 0).sum():,}, "
        f"zero={(products_clean[col] == 0).sum():,}"
    )

assert products_clean["product_id"].is_unique, (
    "Clean product table contains duplicate product IDs."
)

assert len(products_clean) == len(products), (
    "Products were lost or duplicated during cleaning."
)

print("\n=== PRODUCT CLEANING SUMMARY ===")

print(
    "Products:",
    f"{len(products_clean):,}"
)

print(
    "Unknown-category products:",
    f"{(
        products_clean['product_category_name_english']
        == 'unknown'
    ).sum():,}"
)

print(
    "Products with incomplete dimensions:",
    f"{(
        ~products_clean['has_complete_dimensions']
    ).sum():,}"
)

print(
    "English categories:",
    products_clean[
        "product_category_name_english"
    ].nunique()
)

unknown_product_ids = set(
    products_clean.loc[
        products_clean[
            "product_category_name_english"
        ] == "unknown",
        "product_id"
    ]
)

unknown_category_items = order_items.loc[
    order_items["product_id"]
    .isin(unknown_product_ids)
]

print(
    "Order-item rows with unknown category:",
    f"{len(unknown_category_items):,}"
)

print(
    "Orders containing unknown-category products:",
    f"{unknown_category_items['order_id'].nunique():,}"
)

order_items_products_test = order_items.merge(
    products_clean[
        [
            "product_id",
            "product_category_name_english",
            "product_weight_g",
            "product_volume_cm3",
            "has_product_metadata",
            "has_complete_dimensions",
        ]
    ],
    on="product_id",
    how="left",
    validate="many_to_one",
)

assert len(order_items_products_test) == len(order_items), (
    "Product join changed the number of order-item rows."
)

assert (
    order_items_products_test[
        "product_category_name_english"
    ]
    .notna()
    .all()
), "Some order items still lack a cleaned category."


# CLEAN PAYMENT DATA


payments_clean = payments.copy()

payments_clean["payment_type_clean"] = (
    payments_clean["payment_type"]
    .replace({
        "not_defined": "unknown"
    })
)
payments_clean["payment_installments_clean"] = (
    payments_clean["payment_installments"]
    .astype("Float64")
)
payments_clean.loc[
    payments_clean["payment_installments_clean"] <= 0,
    "payment_installments_clean"
] = pd.NA
assert (
    payments_clean["payment_value"] >= 0
).all(), "Negative payment values detected."
print("\n=== PAYMENT CLEANING CHECKS ===")

print(
    "Zero-value payment records:",
    f"{(payments_clean['payment_value'] == 0).sum():,}"
)

print(
    "Invalid installment values converted to missing:",
    f"{payments_clean['payment_installments_clean'].isna().sum():,}"
)

print(
    "Unknown payment types:",
    f"{(payments_clean['payment_type_clean'] == 'unknown').sum():,}"
)
payment_basic_summary = (
    payments_clean
    .groupby(
        "order_id",
        as_index=False
    )
    .agg(
        total_payment_value=(
            "payment_value",
            "sum"
        ),
        payment_record_count=(
            "payment_sequential",
            "count"
        ),
        payment_type_count=(
            "payment_type_clean",
            "nunique"
        ),
        max_installments=(
            "payment_installments_clean",
            "max"
        ),
    )
)
payment_basic_summary["uses_multiple_payment_types"] = (
    payment_basic_summary["payment_type_count"] > 1
)
payment_type_values = (
    payments_clean
    .groupby(
        [
            "order_id",
            "payment_type_clean"
        ],
        as_index=False
    )
    ["payment_value"]
    .sum()
)
payment_type_values = payment_type_values.sort_values(
    by=[
        "order_id",
        "payment_value",
        "payment_type_clean",
    ]
)
primary_payment = (
    payment_type_values
    .drop_duplicates(
        subset="order_id",
        keep="last"
    )
    .rename(
        columns={
            "payment_type_clean":
                "primary_payment_type",
            "payment_value":
                "primary_payment_value",
        }
    )
)
payments_order_level = payment_basic_summary.merge(
    primary_payment[
        [
            "order_id",
            "primary_payment_type",
            "primary_payment_value",
        ]
    ],
    on="order_id",
    how="left",
    validate="one_to_one",
)
assert payments_order_level["order_id"].is_unique, (
    "Order-level payment table contains duplicate order IDs."
)
raw_payment_total = (
    payments_clean["payment_value"].sum()
)
aggregated_payment_total = (
    payments_order_level[
        "total_payment_value"
    ].sum()
)
assert np.isclose(
    raw_payment_total,
    aggregated_payment_total
), "Payment aggregation changed the total payment value."
orders_with_payment = set(
    payments_order_level["order_id"]
)

orders_without_payment = (
    set(orders["order_id"])
    - orders_with_payment
)

print(
    "\nOrders without a payment record:",
    f"{len(orders_without_payment):,}"
)
orders_payment_test = orders.merge(
    payments_order_level,
    on="order_id",
    how="left",
    validate="one_to_one",
)
assert len(orders_payment_test) == len(orders), (
    "Payment join changed the number of order rows."
)
print(
    "\nOrders without payment by status:"
)

print(
    orders_payment_test.loc[
        orders_payment_test[
            "total_payment_value"
        ].isna(),
        "order_status"
    ]
    .value_counts()
)
print("\n=== ORDER-LEVEL PAYMENT SUMMARY ===")

print(
    "Raw payment rows:",
    f"{len(payments_clean):,}"
)

print(
    "Orders with payment records:",
    f"{len(payments_order_level):,}"
)

print(
    "Orders with multiple payment records:",
    f"{(
        payments_order_level[
            'payment_record_count'
        ] > 1
    ).sum():,}"
)

print(
    "Orders using multiple payment types:",
    f"{payments_order_level[
        'uses_multiple_payment_types'
    ].sum():,}"
)
print(
    "\nPrimary payment type distribution:"
)

print(
    payments_order_level[
        "primary_payment_type"
    ]
    .value_counts()
)
payments_order_level[
    "primary_payment_share"
] = np.where(
    payments_order_level[
        "total_payment_value"
    ] > 0,

    payments_order_level[
        "primary_payment_value"
    ]
    / payments_order_level[
        "total_payment_value"
    ],

    np.nan
)
print(
    "\nOrder payment-value summary:"
)

print(
    payments_order_level[
        "total_payment_value"
    ].describe()
)


# CLEAN GEOLOCATION DATA

geolocation_clean = geolocation.copy()
geolocation_clean = (
    geolocation_clean
    .drop_duplicates()
    .copy()
)

print("\n=== GEOLOCATION CLEANING ===")

print(
    "Raw geolocation rows:",
    f"{len(geolocation):,}"
)

print(
    "Rows after removing exact duplicates:",
    f"{len(geolocation_clean):,}"
)

print(
    "Exact duplicates removed:",
    f"{len(geolocation) - len(geolocation_clean):,}"
)
def deterministic_mode(series):
    """
    Return the most frequent non-missing value.

    If multiple values tie for most frequent,
    return the alphabetically first value to keep
    pipeline results deterministic.
    """

    non_missing = series.dropna()

    if non_missing.empty:
        return pd.NA

    counts = non_missing.value_counts()

    max_count = counts.max()

    tied_values = (
        counts[
            counts == max_count
        ]
        .index
        .astype(str)
        .sort_values()
    )

    return tied_values[0]
geolocation_zip_level = (
    geolocation_clean
    .groupby(
        "geolocation_zip_code_prefix",
        as_index=False
    )
    .agg(
        latitude=(
            "geolocation_lat",
            "median"
        ),
        longitude=(
            "geolocation_lng",
            "median"
        ),
        city=(
            "geolocation_city",
            deterministic_mode
        ),
        state=(
            "geolocation_state",
            deterministic_mode
        ),
        geolocation_observation_count=(
            "geolocation_lat",
            "size"
        ),
    )
)
assert (
    geolocation_zip_level[
        "geolocation_zip_code_prefix"
    ].is_unique
), "ZIP-level geolocation table contains duplicate ZIP prefixes."
assert (
    geolocation_zip_level[
        "latitude"
    ].between(-90, 90).all()
), "Invalid latitude detected."
assert (
    geolocation_zip_level[
        "longitude"
    ].between(-180, 180).all()
), "Invalid longitude detected."
print(
    "Unique ZIP prefixes:",
    f"{geolocation_zip_level['geolocation_zip_code_prefix'].nunique():,}"
)

print(
    "ZIP-level lookup rows:",
    f"{len(geolocation_zip_level):,}"
)

print(
    "\nGeolocation observations per ZIP summary:"
)

print(
    geolocation_zip_level[
        "geolocation_observation_count"
    ].describe()
)
customer_geo_test = customers.merge(
    geolocation_zip_level,
    left_on="customer_zip_code_prefix",
    right_on="geolocation_zip_code_prefix",
    how="left",
    validate="many_to_one",
)
assert len(customer_geo_test) == len(customers), (
    "Geolocation join changed the number of customer rows."
)
customers_without_geolocation = (
    customer_geo_test["latitude"]
    .isna()
    .sum()
)

customer_geo_coverage = (
    1
    - customers_without_geolocation
      / len(customer_geo_test)
) * 100

print(
    "\nCustomers without geolocation:",
    f"{customers_without_geolocation:,}"
)

print(
    "Customer geolocation coverage:",
    f"{customer_geo_coverage:.2f}%"
)
seller_geo_test = sellers.merge(
    geolocation_zip_level,
    left_on="seller_zip_code_prefix",
    right_on="geolocation_zip_code_prefix",
    how="left",
    validate="many_to_one",
)
assert len(seller_geo_test) == len(sellers), (
    "Geolocation join changed the number of seller rows."
)
sellers_without_geolocation = (
    seller_geo_test["latitude"]
    .isna()
    .sum()
)

seller_geo_coverage = (
    1
    - sellers_without_geolocation
      / len(seller_geo_test)
) * 100

print(
    "\nSellers without geolocation:",
    f"{sellers_without_geolocation:,}"
)

print(
    "Seller geolocation coverage:",
    f"{seller_geo_coverage:.2f}%"
)

# FINAL CLEAN BASE TABLES
customers_clean = customers.copy()
sellers_clean = sellers.copy()
order_items_clean = order_items.copy()
reviews_clean = reviews.copy()
zero_weight_mask = (
    products_clean["product_weight_g"] == 0
)

print(
    "\nZero product weights converted to missing:",
    f"{zero_weight_mask.sum():,}"
)

products_clean.loc[
    zero_weight_mask,
    "product_weight_g"
] = np.nan
dimension_columns = [
    "product_weight_g",
    "product_length_cm",
    "product_height_cm",
    "product_width_cm",
]

products_clean["has_complete_dimensions"] = (
    products_clean[dimension_columns]
    .notna()
    .all(axis=1)
)


# FINAL DATA QUALITY VALIDATION


print("\n=== FINAL DATA QUALITY VALIDATION ===")
assert orders["order_id"].is_unique, (
    "orders: order_id is not unique."
)

assert customers_clean["customer_id"].is_unique, (
    "customers: customer_id is not unique."
)

assert sellers_clean["seller_id"].is_unique, (
    "sellers: seller_id is not unique."
)

assert products_clean["product_id"].is_unique, (
    "products: product_id is not unique."
)

assert reviews_order_level["order_id"].is_unique, (
    "reviews_order_level: order_id is not unique."
)

assert payments_order_level["order_id"].is_unique, (
    "payments_order_level: order_id is not unique."
)

assert geolocation_zip_level[
    "geolocation_zip_code_prefix"
].is_unique, (
    "geolocation_zip_level: ZIP prefix is not unique."
)
assert (
    order_items_clean[
        ["order_id", "order_item_id"]
    ]
    .duplicated()
    .sum()
    == 0
), "Duplicate order-item composite keys detected."
assert (
    ~orders["customer_id"]
    .isin(customers_clean["customer_id"])
).sum() == 0, (
    "Orders contain invalid customer IDs."
)
assert (
    ~order_items_clean["order_id"]
    .isin(orders["order_id"])
).sum() == 0, (
    "Order items contain invalid order IDs."
)
assert (
    ~order_items_clean["product_id"]
    .isin(products_clean["product_id"])
).sum() == 0, (
    "Order items contain invalid product IDs."
)
assert (
    ~order_items_clean["seller_id"]
    .isin(sellers_clean["seller_id"])
).sum() == 0, (
    "Order items contain invalid seller IDs."
)
assert (
    ~reviews_order_level["order_id"]
    .isin(orders["order_id"])
).sum() == 0, (
    "Reviews contain invalid order IDs."
)
assert (
    ~payments_order_level["order_id"]
    .isin(orders["order_id"])
).sum() == 0, (
    "Payments contain invalid order IDs."
)
assert (
    order_items_clean["price"] >= 0
).all(), "Negative item prices detected."

assert (
    order_items_clean["freight_value"] >= 0
).all(), "Negative freight values detected."

assert (
    payments_clean["payment_value"] >= 0
).all(), "Negative payment values detected."
assert (
    reviews_order_level["review_score"]
    .between(1, 5)
    .all()
), "Invalid review scores detected."
non_negative_time_metrics = [
    "approval_hours",
    "purchase_to_carrier_days",
    "approval_to_carrier_days",
    "carrier_to_customer_days",
    "delivery_days",
    "promised_delivery_days",
]

for col in non_negative_time_metrics:

    assert (
        orders[col]
        .dropna()
        .ge(0)
        .all()
    ), f"Negative values detected in {col}."

expected_row_counts = {
    "orders": 99441,
    "customers": 99441,
    "order_items": 112650,
    "payments": 103886,
    "reviews": 99224,
    "products": 32951,
    "sellers": 3095,
}
actual_row_counts = {
    "orders": len(orders),
    "customers": len(customers_clean),
    "order_items": len(order_items_clean),
    "payments": len(payments_clean),
    "reviews": len(reviews_clean),
    "products": len(products_clean),
    "sellers": len(sellers_clean),
}
for table_name, expected_count in expected_row_counts.items():

    actual_count = actual_row_counts[table_name]

    assert actual_count == expected_count, (
        f"{table_name}: expected "
        f"{expected_count:,} rows but found "
        f"{actual_count:,}."
    )

print(
    "All final data quality checks passed."
)


# EXPORT CLEANED DATA


processed_tables = {
    "orders_clean": orders,
    "customers_clean": customers_clean,
    "sellers_clean": sellers_clean,
    "products_clean": products_clean,
    "order_items_clean": order_items_clean,
    "payments_clean": payments_clean,
    "payments_order_level": payments_order_level,
    "reviews_clean": reviews_clean,
    "reviews_order_level": reviews_order_level,
    "geolocation_zip_level": geolocation_zip_level,
}
print("\n=== EXPORTING PROCESSED DATA ===")

for table_name, df in processed_tables.items():

    output_path = (
        PROCESSED_DIR
        / f"{table_name}.parquet"
    )

    df.to_parquet(
        output_path,
        index=False
    )

    print(
        f"{table_name:25} "
        f"{len(df):>10,} rows "
        f"-> {output_path.name}"
    )


# VERIFY EXPORTED FILES


print("\n=== VERIFYING EXPORTED FILES ===")

for table_name, original_df in processed_tables.items():

    output_path = (
        PROCESSED_DIR
        / f"{table_name}.parquet"
    )

    reloaded_df = pd.read_parquet(
        output_path
    )

    assert len(reloaded_df) == len(original_df), (
        f"{table_name}: row count changed after export."
    )

    assert list(reloaded_df.columns) == list(original_df.columns), (
        f"{table_name}: columns changed after export."
    )

    print(
        f"{table_name:25} OK"
    )
reloaded_orders = pd.read_parquet(
    PROCESSED_DIR / "orders_clean.parquet"
)

assert pd.api.types.is_datetime64_any_dtype(
    reloaded_orders["order_purchase_timestamp"]
), (
    "Datetime type was not preserved in Parquet output."
)

print(
    "\nDatetime preservation check passed."
)
print(
    "\n============================================"
)

print(
    "CLEANING PIPELINE COMPLETED SUCCESSFULLY"
)

print(
    "============================================"
)