from pathlib import Path

import duckdb


# 
# PATHS
# 

ROOT = Path(__file__).resolve().parents[1]

PROCESSED_DIR = (
    ROOT
    / "data"
    / "processed"
)

ANALYTICS_DIR = (
    ROOT
    / "data"
    / "analytics"
)

DATABASE_PATH = (
    ANALYTICS_DIR
    / "olist_ecommerce.duckdb"
)


# 
# TABLE DEFINITIONS
# 

# Processed tables preserve the cleaned source-level datasets.
processed_tables = {
    "customers_clean": (
        PROCESSED_DIR
        / "customers_clean.parquet"
    ),

    "geolocation_zip_level": (
        PROCESSED_DIR
        / "geolocation_zip_level.parquet"
    ),

    "order_items_clean": (
        PROCESSED_DIR
        / "order_items_clean.parquet"
    ),

    "orders_clean": (
        PROCESSED_DIR
        / "orders_clean.parquet"
    ),

    "payments_clean": (
        PROCESSED_DIR
        / "payments_clean.parquet"
    ),

    "payments_order_level": (
        PROCESSED_DIR
        / "payments_order_level.parquet"
    ),

    "products_clean": (
        PROCESSED_DIR
        / "products_clean.parquet"
    ),

    "reviews_clean": (
        PROCESSED_DIR
        / "reviews_clean.parquet"
    ),

    "reviews_order_level": (
        PROCESSED_DIR
        / "reviews_order_level.parquet"
    ),

    "sellers_clean": (
        PROCESSED_DIR
        / "sellers_clean.parquet"
    ),
}


# Analytics tables form the main analysis-ready model.
analytics_tables = {
    "fact_orders": (
        ANALYTICS_DIR
        / "fact_orders.parquet"
    ),

    "fact_order_items": (
        ANALYTICS_DIR
        / "fact_order_items.parquet"
    ),

    "dim_customer": (
        ANALYTICS_DIR
        / "dim_customer.parquet"
    ),

    "dim_product": (
        ANALYTICS_DIR
        / "dim_product.parquet"
    ),

    "dim_seller": (
        ANALYTICS_DIR
        / "dim_seller.parquet"
    ),

    "dim_date": (
        ANALYTICS_DIR
        / "dim_date.parquet"
    ),
}


# Combine both groups for loading and validation.
all_tables = {
    **processed_tables,
    **analytics_tables,
}


# 
# EXPECTED ROW COUNTS
# 

expected_counts = {
    # Processed tables
    "customers_clean": 99441,
    "geolocation_zip_level": 19015,
    "order_items_clean": 112650,
    "orders_clean": 99441,
    "payments_clean": 103886,
    "payments_order_level": 99440,
    "products_clean": 32951,
    "reviews_clean": 99224,
    "reviews_order_level": 98673,
    "sellers_clean": 3095,

    # Analytics tables
    "fact_orders": 99441,
    "fact_order_items": 112650,
    "dim_customer": 96096,
    "dim_product": 32951,
    "dim_seller": 3095,
    "dim_date": 800,
}


# 
# VALIDATE SOURCE FILES BEFORE BUILDING DATABASE
# 

print(
    "Checking Parquet source files..."
)

missing_files = []

for table_name, parquet_path in all_tables.items():

    if not parquet_path.exists():

        missing_files.append(
            (
                table_name,
                parquet_path,
            )
        )


if missing_files:

    print(
        "\nERROR: Missing Parquet files:"
    )

    for table_name, parquet_path in missing_files:

        print(
            f"  {table_name}: "
            f"{parquet_path}"
        )

    raise FileNotFoundError(
        "One or more required Parquet files are missing."
    )


print(
    "All required Parquet files found."
)


# 
# CONNECT TO DATABASE
# 

con = duckdb.connect(
    str(DATABASE_PATH)
)

print(
    f"\nConnected to database:\n"
    f"{DATABASE_PATH}"
)


# 
# HELPER FUNCTION
# 

def load_parquet_table(
    connection,
    table_name,
    parquet_path,
):

    connection.execute(
        f"""
        CREATE OR REPLACE TABLE {table_name} AS

        SELECT *
        FROM read_parquet(?)
        """,
        [str(parquet_path)]
    )

    row_count = connection.execute(
        f"""
        SELECT COUNT(*)
        FROM {table_name}
        """
    ).fetchone()[0]

    print(
        f"Loaded {table_name:24} "
        f"{row_count:>10,} rows"
    )


# 
# LOAD PROCESSED TABLES
# 

print(
    "\n"
    + "=" * 70
)

print(
    "LOADING PROCESSED TABLES"
)

print(
    "=" * 70
)

for table_name, parquet_path in processed_tables.items():

    load_parquet_table(
        con,
        table_name,
        parquet_path,
    )


# 
# LOAD ANALYTICS TABLES
# 

print(
    "\n"
    + "=" * 70
)

print(
    "LOADING ANALYTICS TABLES"
)

print(
    "=" * 70
)

for table_name, parquet_path in analytics_tables.items():

    load_parquet_table(
        con,
        table_name,
        parquet_path,
    )


# 
# INSPECT DATABASE
# 

tables = con.execute(
    """
    SHOW TABLES
    """
).fetchdf()

print(
    "\n"
    + "=" * 70
)

print(
    "DATABASE TABLES"
)

print(
    "=" * 70
)

print(
    tables
)


# 
# SQL ROW COUNTS
# 

print(
    "\n"
    + "=" * 70
)

print(
    "PROCESSED TABLE ROW COUNTS"
)

print(
    "=" * 70
)

for table_name in processed_tables:

    row_count = con.execute(
        f"""
        SELECT COUNT(*)
        FROM {table_name}
        """
    ).fetchone()[0]

    print(
        f"{table_name:24} "
        f"{row_count:>10,}"
    )


print(
    "\n"
    + "=" * 70
)

print(
    "ANALYTICS TABLE ROW COUNTS"
)

print(
    "=" * 70
)

for table_name in analytics_tables:

    row_count = con.execute(
        f"""
        SELECT COUNT(*)
        FROM {table_name}
        """
    ).fetchone()[0]

    print(
        f"{table_name:24} "
        f"{row_count:>10,}"
    )


# 
# SAMPLE ANALYTICS QUERY
# 

sample_orders = con.execute(
    """
    SELECT
        order_id,
        customer_unique_id,
        order_status,
        purchase_date,
        total_payment_value

    FROM fact_orders

    LIMIT 5
    """
).fetchdf()

print(
    "\n"
    + "=" * 70
)

print(
    "SAMPLE ORDERS"
)

print(
    "=" * 70
)

print(
    sample_orders
)


# 
# ORDER STATUS SUMMARY
# 

status_summary = con.execute(
    """
    SELECT
        order_status,

        COUNT(*) AS order_count

    FROM fact_orders

    GROUP BY order_status

    ORDER BY order_count DESC
    """
).fetchdf()

print(
    "\n"
    + "=" * 70
)

print(
    "ORDERS BY STATUS"
)

print(
    "=" * 70
)

print(
    status_summary
)


# 
# VALIDATE EXPECTED ROW COUNTS
# 

print(
    "\n"
    + "=" * 70
)

print(
    "VALIDATING TABLE ROW COUNTS"
)

print(
    "=" * 70
)

for table_name, expected_count in expected_counts.items():

    actual_count = con.execute(
        f"""
        SELECT COUNT(*)
        FROM {table_name}
        """
    ).fetchone()[0]

    assert actual_count == expected_count, (
        f"{table_name}: expected "
        f"{expected_count:,} rows but found "
        f"{actual_count:,}."
    )

    print(
        f"{table_name:24} "
        f"OK "
        f"({actual_count:,} rows)"
    )


# 
# IMPORTANT MODEL VALIDATIONS
# 

print(
    "\n"
    + "=" * 70
)

print(
    "VALIDATING ANALYTICAL TABLE GRAINS"
)

print(
    "=" * 70
)


# fact_orders:
# one row per order
fact_orders_validation = con.execute(
    """
    SELECT
        COUNT(*) AS row_count,
        COUNT(DISTINCT order_id)
            AS unique_orders

    FROM fact_orders
    """
).fetchone()

assert (
    fact_orders_validation[0]
    == fact_orders_validation[1]
), (
    "fact_orders grain validation failed: "
    "order_id is not unique."
)

print(
    "fact_orders: one row per order - OK"
)


# fact_order_items:
# one row per order item
fact_items_validation = con.execute(
    """
    SELECT
        COUNT(*) AS row_count,

        COUNT(
            DISTINCT (
                order_id,
                order_item_id
            )
        ) AS unique_order_items

    FROM fact_order_items
    """
).fetchone()

assert (
    fact_items_validation[0]
    == fact_items_validation[1]
), (
    "fact_order_items grain validation failed: "
    "(order_id, order_item_id) is not unique."
)

print(
    "fact_order_items: "
    "one row per order item - OK"
)


# dim_customer:
# one row per customer_unique_id
dim_customer_validation = con.execute(
    """
    SELECT
        COUNT(*) AS row_count,

        COUNT(
            DISTINCT customer_unique_id
        ) AS unique_customers

    FROM dim_customer
    """
).fetchone()

assert (
    dim_customer_validation[0]
    == dim_customer_validation[1]
), (
    "dim_customer grain validation failed: "
    "customer_unique_id is not unique."
)

print(
    "dim_customer: "
    "one row per unique customer - OK"
)


# dim_product:
# one row per product
dim_product_validation = con.execute(
    """
    SELECT
        COUNT(*) AS row_count,

        COUNT(
            DISTINCT product_id
        ) AS unique_products

    FROM dim_product
    """
).fetchone()

assert (
    dim_product_validation[0]
    == dim_product_validation[1]
), (
    "dim_product grain validation failed: "
    "product_id is not unique."
)

print(
    "dim_product: "
    "one row per product - OK"
)


# dim_seller:
# one row per seller
dim_seller_validation = con.execute(
    """
    SELECT
        COUNT(*) AS row_count,

        COUNT(
            DISTINCT seller_id
        ) AS unique_sellers

    FROM dim_seller
    """
).fetchone()

assert (
    dim_seller_validation[0]
    == dim_seller_validation[1]
), (
    "dim_seller grain validation failed: "
    "seller_id is not unique."
)

print(
    "dim_seller: "
    "one row per seller - OK"
)


# payments_order_level:
# one row per order
payments_validation = con.execute(
    """
    SELECT
        COUNT(*) AS row_count,

        COUNT(
            DISTINCT order_id
        ) AS unique_orders

    FROM payments_order_level
    """
).fetchone()

assert (
    payments_validation[0]
    == payments_validation[1]
), (
    "payments_order_level grain validation failed: "
    "order_id is not unique."
)

print(
    "payments_order_level: "
    "one row per paid order - OK"
)


# reviews_order_level:
# one row per reviewed order
reviews_validation = con.execute(
    """
    SELECT
        COUNT(*) AS row_count,

        COUNT(
            DISTINCT order_id
        ) AS unique_orders

    FROM reviews_order_level
    """
).fetchone()

assert (
    reviews_validation[0]
    == reviews_validation[1]
), (
    "reviews_order_level grain validation failed: "
    "order_id is not unique."
)

print(
    "reviews_order_level: "
    "one row per reviewed order - OK"
)


# geolocation_zip_level:
# one row per ZIP prefix
geo_validation = con.execute(
    """
    SELECT
        COUNT(*) AS row_count,

        COUNT(
            DISTINCT geolocation_zip_code_prefix
        ) AS unique_zip_prefixes

    FROM geolocation_zip_level
    """
).fetchone()

assert (
    geo_validation[0]
    == geo_validation[1]
), (
    "geolocation_zip_level grain validation failed: "
    "ZIP prefix is not unique."
)

print(
    "geolocation_zip_level: "
    "one row per ZIP prefix - OK"
)


# 
# FINAL MESSAGE
# 
print(
    "\n"
    + "=" * 70
)

print(
    "DUCKDB BUILD AND VALIDATION PASSED"
)

print(
    "=" * 70
)

print(
    f"\nDatabase created at:\n"
    f"{DATABASE_PATH}"
)


# 
# CLOSE CONNECTION
# 

con.close()

print(
    "\nDatabase connection closed."
)