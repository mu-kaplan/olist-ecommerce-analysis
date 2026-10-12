from pathlib import Path
import duckdb
import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", None)

ROOT = Path(__file__).resolve().parents[1]

DATABASE_PATH = (
    ROOT
    / "data"
    / "analytics"
    / "olist_ecommerce.duckdb"
)

SQL_PATH = (
    ROOT
    / "sql"
    / "09_statistical_validation.sql"
)

con = duckdb.connect(
    str(DATABASE_PATH)
)

sql_text = SQL_PATH.read_text(
    encoding="utf-8"
)


queries = [
    query.strip()
    for query in sql_text.split(";")
    if query.strip()
]


for i, query in enumerate(
    queries,
    start=1
):

    print(
        f"\n{'=' * 70}"
    )

    print(
        f"QUERY {i}"
    )

    print(
        f"{'=' * 70}"
    )

    result = con.execute(
        query
    ).fetchdf()

    print(result)


con.close()