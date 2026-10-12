from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]

DATABASE_PATH = (
    ROOT
    / "data"
    / "analytics"
    / "olist_ecommerce.duckdb"
)

con = duckdb.connect(
    str(DATABASE_PATH)
)

print("Connected to Olist DuckDB database.")

def run_query(title, sql):
    """
    Execute a SQL query and print the result
    as a pandas DataFrame.
    """

    print(
        f"\n{'=' * 60}\n"
        f"{title}\n"
        f"{'=' * 60}"
    )

    result = con.execute(sql).fetchdf()

    print(result)

    return result
run_query(
    "1. Basic SELECT",
    """
    SELECT
        order_id,
        order_status,
        customer_state,
        purchase_date,
        total_payment_value
    FROM fact_orders
    LIMIT 10
    """
)
run_query(
    "2. Distinct order statuses",
    """
    SELECT DISTINCT
        order_status
    FROM fact_orders
    ORDER BY order_status
    """
)
run_query(
    "3. Distinct customer state and city combinations",
    """
    SELECT DISTINCT
        customer_state,
        customer_city
    FROM fact_orders
    ORDER BY
        customer_state,
        customer_city
    LIMIT 20
    """
)
run_query(
    "4. Delivered orders",
    """
    SELECT
        order_id,
        order_status,
        purchase_date,
        total_payment_value
    FROM fact_orders
    WHERE order_status = 'delivered'
    LIMIT 10
    """
)
run_query(
    "5. Orders above 500 BRL",
    """
    SELECT
        order_id,
        purchase_date,
        customer_state,
        total_payment_value
    FROM fact_orders
    WHERE total_payment_value > 500
    ORDER BY total_payment_value DESC
    LIMIT 20
    """
)
run_query(
    "6. High-value delivered orders in SP",
    """
    SELECT
        order_id,
        customer_state,
        order_status,
        total_payment_value
    FROM fact_orders
    WHERE
        order_status = 'delivered'
        AND customer_state = 'SP'
        AND total_payment_value > 500
    ORDER BY total_payment_value DESC
    LIMIT 20
    """
)
run_query(
    "7. Orders from SP or RJ",
    """
    SELECT
        order_id,
        customer_state,
        total_payment_value
    FROM fact_orders
    WHERE
        customer_state = 'SP'
        OR customer_state = 'RJ'
    LIMIT 20
    """
)

run_query(
    "8. Orders from selected states",
    """
    SELECT
        order_id,
        customer_state,
        total_payment_value
    FROM fact_orders
    WHERE customer_state IN (
        'SP',
        'RJ',
        'MG'
    )
    LIMIT 20
    """
)
run_query(
    "9. Orders outside selected states",
    """
    SELECT
        order_id,
        customer_state,
        total_payment_value
    FROM fact_orders
    WHERE customer_state NOT IN (
        'SP',
        'RJ',
        'MG'
    )
    LIMIT 20
    """
)
run_query(
    "10. Orders between 100 and 200 BRL",
    """
    SELECT
        order_id,
        total_payment_value
    FROM fact_orders
    WHERE total_payment_value
        BETWEEN 100 AND 200
    ORDER BY total_payment_value DESC
    LIMIT 20
    """
)
run_query(
    "11. Orders purchased during January 2018",
    """
    SELECT
        order_id,
        purchase_date,
        total_payment_value
    FROM fact_orders
    WHERE purchase_date
        BETWEEN DATE '2018-01-01'
            AND DATE '2018-01-31'
    ORDER BY purchase_date
    LIMIT 20
    """
)
run_query(
    "12. January 2018 using half-open dates",
    """
    SELECT
        order_id,
        purchase_date,
        total_payment_value
    FROM fact_orders
    WHERE
        purchase_date >= DATE '2018-01-01'
        AND purchase_date < DATE '2018-02-01'
    ORDER BY purchase_date
    LIMIT 20
    """
)
run_query(
    "13. Orders with missing payment value",
    """
    SELECT
        order_id,
        order_status,
        purchase_date,
        total_payment_value
    FROM fact_orders
    WHERE total_payment_value IS NULL
    """
)
run_query(
    "14. Orders with review scores",
    """
    SELECT
        order_id,
        review_score
    FROM fact_orders
    WHERE review_score IS NOT NULL
    LIMIT 10
    """
)
run_query(
    "15. Payment difference calculation",
    """
    SELECT
        order_id,
        item_plus_freight_value,
        total_payment_value,

        total_payment_value
            - item_plus_freight_value
            AS payment_difference

    FROM fact_orders

    WHERE
        total_payment_value IS NOT NULL
        AND item_plus_freight_value IS NOT NULL

    ORDER BY
        ABS(
            total_payment_value
            - item_plus_freight_value
        ) DESC

    LIMIT 20
    """
)
run_query(
    "16. Orders with highest freight share",
    """
    SELECT
        order_id,
        item_sales_value,
        freight_value,
        item_plus_freight_value,

        100.0 * freight_value
            / NULLIF(
                item_plus_freight_value,
                0
            )
            AS freight_percentage

    FROM fact_orders

    WHERE
        item_plus_freight_value IS NOT NULL

    ORDER BY freight_percentage DESC

    LIMIT 20
    """
)
run_query(
    "17. Column aliases",
    """
    SELECT
        order_id AS order_number,
        customer_state AS state,
        total_payment_value AS payment_value_brl
    FROM fact_orders
    LIMIT 10
    """
)

run_query(
    "18.15 highest-payment delivered orders purchased in 2018," \
    " but only for customers in SP, RJ, or MG.",
    """
    SELECT
        order_id,
        customer_state,
        purchase_date,
        total_payment_value
    FROM fact_orders
    WHERE
        order_status = 'delivered'
        AND customer_state IN ('SP', 'RJ', 'MG')
        AND purchase_date BETWEEN DATE '2018-01-01' AND DATE '2018-12-31'   
    ORDER BY total_payment_value DESC
    LIMIT 15
    """
)
    

print(
    "\nDatabase connection closed."
)

run_query(
    "19. Total number of orders",
    """
    SELECT
        COUNT(*) AS order_count
    FROM fact_orders
    """
)

run_query(
    "20. COUNT star vs COUNT payment",
    """
    SELECT
        COUNT(*) AS all_orders,
        COUNT(total_payment_value) AS orders_with_payment
    FROM fact_orders
    """
)
run_query(
    "21. Orders and unique customers",
    """
    SELECT
        COUNT(*) AS order_count,
        COUNT(DISTINCT customer_unique_id)
            AS unique_customer_count
    FROM fact_orders
    """
)
run_query(
    "22. Total customer payment value",
    """
    SELECT
        SUM(total_payment_value)
            AS total_payment_value
    FROM fact_orders
    """
)
run_query(
    "23. Executive payment summary",
    """
    SELECT
        COUNT(*) AS order_count,

        COUNT(DISTINCT customer_unique_id)
            AS unique_customers,

        SUM(total_payment_value)
            AS total_payment_value,

        AVG(total_payment_value)
            AS average_payment_value,

        MIN(total_payment_value)
            AS minimum_payment_value,

        MAX(total_payment_value)
            AS maximum_payment_value

    FROM fact_orders
    """
)
run_query(
    "24. Order count by status",
    """
    SELECT
        order_status,
        COUNT(*) AS order_count
    FROM fact_orders
    GROUP BY order_status
    ORDER BY order_count DESC
    """
)
run_query(
    "25. Orders by customer state",
    """
    SELECT
        customer_state,
        COUNT(*) AS order_count
    FROM fact_orders
    GROUP BY customer_state
    ORDER BY order_count DESC
    """
)
run_query(
    "26. Payment performance by state",
    """
    SELECT
        customer_state,

        COUNT(*) AS order_count,

        COUNT(DISTINCT customer_unique_id)
            AS unique_customers,

        SUM(total_payment_value)
            AS total_payment_value,

        AVG(total_payment_value)
            AS average_payment_value

    FROM fact_orders

    GROUP BY customer_state

    ORDER BY total_payment_value DESC
    """
)
run_query(
    "27. Delivered-order performance by state",
    """
    SELECT
        customer_state,

        COUNT(*) AS delivered_orders,

        SUM(total_payment_value)
            AS total_payment_value,

        AVG(total_payment_value)
            AS average_payment_value

    FROM fact_orders

    WHERE order_status = 'delivered'

    GROUP BY customer_state

    ORDER BY total_payment_value DESC
    """
)
run_query(
    "28. States with at least 1,000 delivered orders",
    """
    SELECT
        customer_state,
        COUNT(*) AS delivered_orders,
        AVG(total_payment_value)
            AS average_payment_value

    FROM fact_orders

    WHERE order_status = 'delivered'

    GROUP BY customer_state

    HAVING COUNT(*) >= 1000

    ORDER BY delivered_orders DESC
    """
)
run_query(
    "29. Monthly order volume",
    """
    SELECT
        purchase_year_month,
        COUNT(*) AS order_count
    FROM fact_orders
    GROUP BY purchase_year_month
    ORDER BY purchase_year_month
    """
)
run_query(
    "30. Monthly payment summary",
    """
    SELECT
        purchase_year_month,

        COUNT(*) AS order_count,

        SUM(total_payment_value)
            AS total_payment_value,

        AVG(total_payment_value)
            AS average_payment_value

    FROM fact_orders

    GROUP BY purchase_year_month

    ORDER BY purchase_year_month
    """
)
run_query(
    "31. Monthly orders by status",
    """
    SELECT
        purchase_year_month,
        order_status,
        COUNT(*) AS order_count

    FROM fact_orders

    GROUP BY
        purchase_year_month,
        order_status

    ORDER BY
        purchase_year_month,
        order_count DESC
    """
)
run_query(
    "32. Cancellation rate by state",
    """
    SELECT
        customer_state,

        COUNT(*) AS total_orders,

        SUM(
            CASE
                WHEN order_status = 'canceled'
                THEN 1
                ELSE 0
            END
        ) AS canceled_orders,

        100.0
        * SUM(
            CASE
                WHEN order_status = 'canceled'
                THEN 1
                ELSE 0
            END
        )
        / COUNT(*)
        AS cancellation_rate_pct

    FROM fact_orders

    GROUP BY customer_state

    ORDER BY cancellation_rate_pct DESC
    """
)
run_query(
    "33. Cancellation rate using FILTER",
    """
    SELECT
        customer_state,

        COUNT(*) AS total_orders,

        COUNT(*) FILTER (
            WHERE order_status = 'canceled'
        ) AS canceled_orders,

        100.0
        * COUNT(*) FILTER (
            WHERE order_status = 'canceled'
        )
        / COUNT(*)
        AS cancellation_rate_pct

    FROM fact_orders

    GROUP BY customer_state

    ORDER BY cancellation_rate_pct DESC
    """
)
run_query(
    "34. Top categories by item sales",
    """
    SELECT
        product_category_name_english
            AS category,

        COUNT(*) AS item_rows,

        COUNT(DISTINCT order_id)
            AS order_count,

        SUM(price)
            AS item_sales_value,

        SUM(freight_value)
            AS freight_value

    FROM fact_order_items

    GROUP BY product_category_name_english

    ORDER BY item_sales_value DESC

    LIMIT 15
    """
)
run_query(
    "35. Category price profile",
    """
    SELECT
        product_category_name_english
            AS category,

        COUNT(*) AS item_rows,

        AVG(price)
            AS average_item_price,

        MIN(price)
            AS minimum_item_price,

        MAX(price)
            AS maximum_item_price,

        SUM(price)
            AS item_sales_value

    FROM fact_order_items

    GROUP BY product_category_name_english

    HAVING COUNT(*) >= 100

    ORDER BY average_item_price DESC

    LIMIT 20
    """
)
run_query(
    "36. Single-seller vs multi-seller orders",
    """
    SELECT
        is_multi_seller_order,

        COUNT(*) AS order_count,

        AVG(total_payment_value)
            AS average_payment_value,

        AVG(delivery_days)
            AS average_delivery_days

    FROM fact_orders

    WHERE item_count IS NOT NULL

    GROUP BY is_multi_seller_order

    ORDER BY is_multi_seller_order
    """
)
run_query(
    "37. Delivery statistics by status",
    """
    SELECT
        order_status,

        COUNT(*) AS order_count,

        COUNT(delivery_days)
            AS orders_with_delivery_duration,

        AVG(delivery_days)
            AS average_delivery_days

    FROM fact_orders

    GROUP BY order_status

    ORDER BY order_count DESC
    """
)
run_query(
    "38. test",
    """
 SELECT
        customer_state,
        COUNT(*) AS order_count,
        COUNT(DISTINCT customer_unique_id)
                    AS unique_customers,
        
                SUM(total_payment_value)
                    AS total_payment_value,
        
                AVG(total_payment_value)
                    AS average_payment_value
        
    FROM fact_orders
    where order_status = 'delivered'
    AND purchase_date >= DATE '2018-01-01'
    AND purchase_date < DATE '2019-01-01'   
    GROUP BY customer_state
    having count(*) >= 500
    ORDER BY total_payment_value DESC
    limit 20
    """
)
run_query(
    "39. Join order items to product dimension",
    """
    SELECT
        oi.order_id,
        oi.order_item_id,
        oi.product_id,
        p.product_category_name_english AS category,
        oi.price,
        oi.freight_value

    FROM fact_order_items AS oi

    INNER JOIN dim_product AS p
        ON oi.product_id = p.product_id

    LIMIT 20
    """
)
run_query(
    "40. Check item-product join row count",
    """
    SELECT
        COUNT(*) AS joined_rows
    FROM fact_order_items AS oi

    INNER JOIN dim_product AS p
        ON oi.product_id = p.product_id
    """
)

run_query(
    "41. Items with product and seller information",
    """
    SELECT
        oi.order_id,
        oi.order_item_id,

        p.product_category_name_english
            AS category,

        s.seller_city,
        s.seller_state,

        oi.price,
        oi.freight_value

    FROM fact_order_items AS oi

    INNER JOIN dim_product AS p
        ON oi.product_id = p.product_id

    INNER JOIN dim_seller AS s
        ON oi.seller_id = s.seller_id

    LIMIT 20
    """
)
run_query(
    "42. Item sales by seller state",
    """
    SELECT
        s.seller_state,

        COUNT(*) AS item_rows,

        COUNT(DISTINCT oi.order_id)
            AS order_count,

        COUNT(DISTINCT oi.seller_id)
            AS seller_count,

        SUM(oi.price)
            AS item_sales_value

    FROM fact_order_items AS oi

    INNER JOIN dim_seller AS s
        ON oi.seller_id = s.seller_id

    GROUP BY s.seller_state

    ORDER BY item_sales_value DESC
    """
)
run_query(
    "43. Left join orders to customer dimension",
    """
    SELECT
        o.order_id,
        o.customer_unique_id,
        c.latest_customer_state,
        c.lifetime_order_count

    FROM fact_orders AS o

    LEFT JOIN dim_customer AS c
        ON o.customer_unique_id
         = c.customer_unique_id

    LIMIT 20
    """
)
run_query(
    "44. Validate order-customer left join",
    """
    SELECT
        COUNT(*) AS joined_rows,

        COUNT(DISTINCT o.order_id)
            AS unique_orders

    FROM fact_orders AS o

    LEFT JOIN dim_customer AS c
        ON o.customer_unique_id
         = c.customer_unique_id
    """
)
run_query(
    "45. Fact-to-fact join row multiplication",
    """
    SELECT
        COUNT(*) AS joined_rows,

        COUNT(DISTINCT o.order_id)
            AS unique_orders

    FROM fact_orders AS o

    INNER JOIN fact_order_items AS oi
        ON o.order_id = oi.order_id
    """
)
run_query(
    "46. WRONG payment sum after item join",
    """
    SELECT
        SUM(o.total_payment_value)
            AS incorrect_payment_total

    FROM fact_orders AS o

    INNER JOIN fact_order_items AS oi
        ON o.order_id = oi.order_id
    """
)
run_query(
    "47. Correct payment sum from order grain",
    """
    SELECT
        SUM(total_payment_value)
            AS correct_payment_total

    FROM fact_orders
    """
)
run_query(
    "48. Safe aggregation before join",
    """
    SELECT
        o.order_id,
        o.total_payment_value,
        i.item_count,
        i.item_sales_value

    FROM fact_orders AS o

    LEFT JOIN (
        SELECT
            order_id,

            COUNT(*) AS item_count,

            SUM(price)
                AS item_sales_value

        FROM fact_order_items

        GROUP BY order_id
    ) AS i

        ON o.order_id = i.order_id
    order by item_count desc
    LIMIT 20
    """
)
run_query(
    "49. Validate aggregated item join",
    """
    SELECT
        COUNT(*) AS joined_rows,
        COUNT(DISTINCT o.order_id)
            AS unique_orders

    FROM fact_orders AS o

    LEFT JOIN (
        SELECT
            order_id,
            COUNT(*) AS item_count
        FROM fact_order_items
        GROUP BY order_id
    ) AS i

        ON o.order_id = i.order_id
    """
)
run_query(
    "50. Monthly delivered order summary via dim_date",
    """
    SELECT
        d.year,
        d.month_number,
        d.month_name,

        COUNT(*) AS delivered_orders,

        SUM(o.total_payment_value)
            AS total_payment_value

    FROM fact_orders AS o

    INNER JOIN dim_date AS d
        ON o.purchase_date = d.date

    WHERE o.order_status = 'delivered'

    GROUP BY
        d.year,
        d.month_number,
        d.month_name

    ORDER BY
        d.year,
        d.month_number
    """
)
run_query(
    "51. Orders by customer repeat status",
    """
    SELECT
        c.is_repeat_customer,

        COUNT(*) AS order_count,

        COUNT(DISTINCT o.customer_unique_id)
            AS customer_count,

        SUM(o.total_payment_value)
            AS total_payment_value,

        AVG(o.total_payment_value)
            AS average_payment_value

    FROM fact_orders AS o

    INNER JOIN dim_customer AS c
        ON o.customer_unique_id
         = c.customer_unique_id

    GROUP BY c.is_repeat_customer

    ORDER BY c.is_repeat_customer
    """
)
run_query(
    "52. Item sales by order status",
    """
    SELECT
        o.order_status,

        COUNT(*) AS item_rows,

        SUM(oi.price)
            AS item_sales_value

    FROM fact_order_items AS oi

    INNER JOIN fact_orders AS o
        ON oi.order_id = o.order_id

    GROUP BY o.order_status

    ORDER BY item_sales_value DESC
    """
)
run_query(
    "53. Product category sales for SP sellers",
    """
    SELECT
        p.product_category_name_english AS category,

        COUNT(*) AS item_rows,

        COUNT(DISTINCT oi.order_id)
            AS order_count,

        COUNT(DISTINCT oi.seller_id)
            AS seller_count,

        SUM(oi.price)
            AS item_sales_value,

        AVG(oi.price)
            AS average_item_price

    FROM fact_order_items AS oi

    INNER JOIN dim_product AS p
        ON oi.product_id = p.product_id

    INNER JOIN dim_seller AS s
        ON oi.seller_id = s.seller_id

    WHERE s.seller_state = 'SP'

    GROUP BY
        p.product_category_name_english

    HAVING COUNT(*) >= 500

    ORDER BY
        item_sales_value DESC
    """
)
run_query(
    "54. Aggregate items before joining using a CTE",
    """
    WITH item_summary AS (

        SELECT
            order_id,

            COUNT(*) AS item_count,

            SUM(price)
                AS item_sales_value,

            SUM(freight_value)
                AS freight_value

        FROM fact_order_items

        GROUP BY order_id
    )

    SELECT
        o.order_id,
        o.order_status,
        o.total_payment_value,

        i.item_count,
        i.item_sales_value,
        i.freight_value

    FROM fact_orders AS o

    LEFT JOIN item_summary AS i
        ON o.order_id = i.order_id

    LIMIT 20
    """
)
run_query(
    "55. Check whether CTE became a table",
    """
    SHOW TABLES
    """
)
run_query(
    "56. Multiple CTEs",
    """
    WITH item_summary AS (

        SELECT
            order_id,
            COUNT(*) AS item_count,
            SUM(price) AS item_sales_value,
            SUM(freight_value) AS freight_value

        FROM fact_order_items

        GROUP BY order_id
    ),

    delivered_orders AS (

        SELECT
            order_id,
            customer_state,
            purchase_date,
            total_payment_value,
            review_score

        FROM fact_orders

        WHERE order_status = 'delivered'
    )

    SELECT
        d.order_id,
        d.customer_state,
        d.purchase_date,

        i.item_count,
        i.item_sales_value,
        i.freight_value,

        d.total_payment_value,
        d.review_score

    FROM delivered_orders AS d

    LEFT JOIN item_summary AS i
        ON d.order_id = i.order_id

    LIMIT 20
    """
)
run_query(
    "57. State performance among repeat customers",
    """
    WITH repeat_customers AS (

        SELECT
            customer_unique_id

        FROM fact_orders

        GROUP BY customer_unique_id

        HAVING COUNT(*) > 1
    )

    SELECT
        o.customer_state,

        COUNT(*) AS order_count,

        COUNT(DISTINCT o.customer_unique_id)
            AS repeat_customer_count,

        SUM(o.total_payment_value)
            AS total_payment_value,

        AVG(o.total_payment_value)
            AS average_payment_value

    FROM fact_orders AS o

    INNER JOIN repeat_customers AS r
        ON o.customer_unique_id
         = r.customer_unique_id

    GROUP BY o.customer_state

    ORDER BY total_payment_value DESC
    """
)
run_query(
    "58. Categories above average category sales",
    """
    WITH category_sales AS (

        SELECT
            product_category_name_english
                AS category,

            SUM(price)
                AS item_sales_value

        FROM fact_order_items

        GROUP BY
            product_category_name_english
    )

    SELECT
        category,
        item_sales_value

    FROM category_sales

    WHERE item_sales_value > (
        SELECT AVG(item_sales_value)
        FROM category_sales
    )

    ORDER BY item_sales_value DESC
    """
)
run_query(
    "59. Delivered orders above average delivered payment",
    """
    WITH delivered_orders AS (

        SELECT
            order_id,
            customer_state,
            purchase_date,
            total_payment_value

        FROM fact_orders

        WHERE
            order_status = 'delivered'
            AND total_payment_value IS NOT NULL
    ),

    average_payment AS (

        SELECT
            AVG(total_payment_value)
                AS avg_payment

        FROM delivered_orders
    )

    SELECT
        d.order_id,
        d.customer_state,
        d.purchase_date,
        d.total_payment_value,
        a.avg_payment,

        d.total_payment_value
            - a.avg_payment
            AS amount_above_average

    FROM delivered_orders AS d

    CROSS JOIN average_payment AS a

    WHERE
        d.total_payment_value
            > a.avg_payment

    ORDER BY
        d.total_payment_value DESC

    LIMIT 20
    """
)
run_query(
    "60. Repeat customer lifetime value by latest state",
    """
    WITH repeat_customer_summary AS (

        SELECT
            customer_unique_id,

            COUNT(*) AS lifetime_order_count,

            SUM(total_payment_value)
                AS lifetime_payment_value

        FROM fact_orders

        GROUP BY customer_unique_id

        HAVING COUNT(*) >= 2
    )

    SELECT
        c.latest_customer_state
            AS customer_state,

        COUNT(*) AS repeat_customer_count,

        SUM(r.lifetime_order_count)
            AS total_order_count,

        SUM(r.lifetime_payment_value)
            AS total_lifetime_payment_value

    FROM repeat_customer_summary AS r

    INNER JOIN dim_customer AS c
        ON r.customer_unique_id
         = c.customer_unique_id

    GROUP BY
        c.latest_customer_state

    ORDER BY
        total_lifetime_payment_value DESC
    """
)

run_query(
    "61. Number each customer's orders",
    """
    SELECT
        customer_unique_id,
        order_id,
        order_purchase_timestamp,
        total_payment_value,

        ROW_NUMBER() OVER (
            PARTITION BY customer_unique_id
            ORDER BY
                order_purchase_timestamp,
                order_id
        ) AS customer_order_number

    FROM fact_orders

    ORDER BY
        customer_unique_id,
        customer_order_number

    LIMIT 30
    """
)

run_query(
    "62. Repeat purchase orders",
    """
    WITH numbered_orders AS (

        SELECT
            customer_unique_id,
            order_id,
            order_purchase_timestamp,
            total_payment_value,

            ROW_NUMBER() OVER (
                PARTITION BY customer_unique_id
                ORDER BY
                    order_purchase_timestamp,
                    order_id
            ) AS customer_order_number

        FROM fact_orders
    )

    SELECT
        customer_unique_id,
        order_id,
        order_purchase_timestamp,
        customer_order_number,
        total_payment_value

    FROM numbered_orders

    WHERE customer_order_number > 1

    ORDER BY
        customer_unique_id,
        customer_order_number

    LIMIT 30
    """
)

run_query(
    "63. Rank orders by payment within each state",
    """
    SELECT
        customer_state,
        order_id,
        total_payment_value,

        RANK() OVER (
            PARTITION BY customer_state
            ORDER BY total_payment_value DESC
        ) AS payment_rank_in_state

    FROM fact_orders

    WHERE total_payment_value IS NOT NULL

    ORDER BY
        customer_state,
        payment_rank_in_state

    LIMIT 40
    """
)

run_query(
    "64. Top 3 payment orders in every state",
    """
    WITH ranked_orders AS (

        SELECT
            customer_state,
            order_id,
            purchase_date,
            total_payment_value,

            ROW_NUMBER() OVER (
                PARTITION BY customer_state
                ORDER BY
                    total_payment_value DESC,
                    order_id
            ) AS state_payment_rank

        FROM fact_orders

        WHERE total_payment_value IS NOT NULL
    )

    SELECT
        customer_state,
        order_id,
        purchase_date,
        total_payment_value,
        state_payment_rank

    FROM ranked_orders

    WHERE state_payment_rank <= 3

    ORDER BY
        customer_state,
        state_payment_rank
    """
)

run_query(
    "65. Monthly payment with previous month",
    """
    WITH monthly_summary AS (

        SELECT
            purchase_year_month,

            SUM(total_payment_value)
                AS monthly_payment_value

        FROM fact_orders

        GROUP BY purchase_year_month
    )

    SELECT
        purchase_year_month,
        monthly_payment_value,

        LAG(monthly_payment_value) OVER (
            ORDER BY purchase_year_month
        ) AS previous_month_payment

    FROM monthly_summary

    ORDER BY purchase_year_month
    """
)

run_query(
    "66. Month-over-month payment growth",
    """
    WITH monthly_summary AS (

        SELECT
            purchase_year_month,

            SUM(total_payment_value)
                AS monthly_payment_value

        FROM fact_orders

        GROUP BY purchase_year_month
    ),

    monthly_with_previous AS (

        SELECT
            purchase_year_month,
            monthly_payment_value,

            LAG(monthly_payment_value) OVER (
                ORDER BY purchase_year_month
            ) AS previous_month_payment

        FROM monthly_summary
    )

    SELECT
        purchase_year_month,
        monthly_payment_value,
        previous_month_payment,

        monthly_payment_value
            - previous_month_payment
            AS payment_change,

        100.0
        * (
            monthly_payment_value
            - previous_month_payment
        )
        / NULLIF(
            previous_month_payment,
            0
        )
        AS payment_change_pct

    FROM monthly_with_previous

    ORDER BY purchase_year_month
    """
)

run_query(
    "67. Cumulative payment value",
    """
    WITH monthly_summary AS (

        SELECT
            purchase_year_month,

            SUM(total_payment_value)
                AS monthly_payment_value

        FROM fact_orders

        GROUP BY purchase_year_month
    )

    SELECT
        purchase_year_month,
        monthly_payment_value,

        SUM(monthly_payment_value) OVER (
            ORDER BY purchase_year_month

            ROWS BETWEEN
                UNBOUNDED PRECEDING
                AND CURRENT ROW
        ) AS cumulative_payment_value

    FROM monthly_summary

    ORDER BY purchase_year_month
    """
)

run_query(
    "68. State share of total payment value",
    """
    WITH state_summary AS (

        SELECT
            customer_state,

            SUM(total_payment_value)
                AS state_payment_value

        FROM fact_orders

        GROUP BY customer_state
    )

    SELECT
        customer_state,
        state_payment_value,

        SUM(state_payment_value) OVER ()
            AS overall_payment_value,

        100.0
        * state_payment_value
        / SUM(state_payment_value) OVER ()
            AS share_of_total_pct

    FROM state_summary

    ORDER BY state_payment_value DESC
    """
)

run_query(
    "Check fact_order_items columns",
    """
    DESCRIBE fact_order_items
    """
)

run_query(
    "69. Top 3 product categories by item sales within each seller state",
    """
    WITH category_sales AS (

        SELECT
            s.seller_state,

            p.product_category_name_english
                AS category,

            SUM(oi.price)
                AS item_sales_value

        FROM fact_order_items AS oi

        INNER JOIN dim_seller AS s
            ON oi.seller_id = s.seller_id

        INNER JOIN dim_product AS p
            ON oi.product_id = p.product_id

        GROUP BY
            s.seller_state,
            p.product_category_name_english
    ),

    ranked_categories AS (

        SELECT
            seller_state,
            category,
            item_sales_value,

            ROW_NUMBER() OVER (
                PARTITION BY seller_state

                ORDER BY
                    item_sales_value DESC,
                    category
            ) AS category_rank

        FROM category_sales
    )

    SELECT
        seller_state,
        category,
        item_sales_value,
        category_rank

    FROM ranked_categories

    WHERE category_rank <= 3

    ORDER BY
        seller_state,
        category_rank
    """
)

run_query(
    "69. Top 3 product categories by item sales within each seller state",
    """
    WITH category_sales AS (

        SELECT
            seller_state,

            product_category_name_english
                AS category,

            SUM(price)
                AS item_sales_value

        FROM fact_order_items

        GROUP BY
            seller_state,
            product_category_name_english
    ),

    ranked_categories AS (

        SELECT
            seller_state,
            category,
            item_sales_value,

            ROW_NUMBER() OVER (
                PARTITION BY seller_state

                ORDER BY
                    item_sales_value DESC,
                    category
            ) AS category_rank

        FROM category_sales
    )

    SELECT
        seller_state,
        category,
        item_sales_value,
        category_rank

    FROM ranked_categories

    WHERE category_rank <= 3

    ORDER BY
        seller_state,
        category_rank
    """
)

run_query(
    "70. Order payment segments",
    """
    SELECT
        order_id,
        total_payment_value,

        CASE
            WHEN total_payment_value < 50
                THEN 'Low'

            WHEN total_payment_value < 150
                THEN 'Medium'

            WHEN total_payment_value < 500
                THEN 'High'

            ELSE 'Very High'
        END AS payment_segment

    FROM fact_orders

    WHERE total_payment_value IS NOT NULL

    ORDER BY total_payment_value DESC

    LIMIT 30
    """
)

run_query(
    "71. Payment segment summary",
    """
    WITH segmented_orders AS (

        SELECT
            order_id,
            total_payment_value,

            CASE
                WHEN total_payment_value < 50
                    THEN 'Low'

                WHEN total_payment_value < 150
                    THEN 'Medium'

                WHEN total_payment_value < 500
                    THEN 'High'

                ELSE 'Very High'
            END AS payment_segment

        FROM fact_orders

        WHERE total_payment_value IS NOT NULL
    )

    SELECT
        payment_segment,

        COUNT(*) AS order_count,

        AVG(total_payment_value)
            AS average_payment_value,

        SUM(total_payment_value)
            AS total_payment_value

    FROM segmented_orders

    GROUP BY payment_segment

    ORDER BY total_payment_value DESC
    """
)

run_query(
    "72. Delivery classification",
    """
    SELECT
        order_id,
        delivery_delay_days,

        CASE
            WHEN delivery_delay_days IS NULL
                THEN 'Unknown'

            WHEN delivery_delay_days > 0
                THEN 'Late'

            WHEN delivery_delay_days = 0
                THEN 'On promised date'

            ELSE 'Early'
        END AS delivery_performance

    FROM fact_orders

    LIMIT 30
    """
)

run_query(
    "73. Payment type with missing label",
    """
    SELECT
        order_id,
        primary_payment_type,

        COALESCE(
            primary_payment_type,
            'missing_payment'
        ) AS payment_type_display

    FROM fact_orders

    WHERE primary_payment_type IS NULL

    LIMIT 20
    """
)

run_query(
    "74. Extract date components",
    """
    SELECT
        order_id,
        order_purchase_timestamp,

        EXTRACT(
            YEAR
            FROM order_purchase_timestamp
        ) AS purchase_year,

        EXTRACT(
            MONTH
            FROM order_purchase_timestamp
        ) AS purchase_month,

        EXTRACT(
            HOUR
            FROM order_purchase_timestamp
        ) AS purchase_hour

    FROM fact_orders

    LIMIT 20
    """
)

run_query(
    "75. Monthly order summary using DATE_TRUNC",
    """
    SELECT
        DATE_TRUNC(
            'month',
            order_purchase_timestamp
        ) AS purchase_month,

        COUNT(*) AS order_count,

        SUM(total_payment_value)
            AS total_payment_value

    FROM fact_orders

    GROUP BY
        DATE_TRUNC(
            'month',
            order_purchase_timestamp
        )

    ORDER BY purchase_month
    """
)

run_query(
    "76. Clean category labels in SQL",
    """
    SELECT DISTINCT
        product_category_name_english
            AS original_category,

        REPLACE(
            product_category_name_english,
            '_',
            ' '
        ) AS readable_category

    FROM fact_order_items

    ORDER BY original_category

    LIMIT 30
    """
)

run_query(
    "77. String function examples",
    """
    SELECT DISTINCT
        product_category_name_english
            AS category,

        UPPER(
            product_category_name_english
        ) AS category_upper,

        LOWER(
            product_category_name_english
        ) AS category_lower,

        LENGTH(
            product_category_name_english
        ) AS category_name_length

    FROM fact_order_items

    ORDER BY category

    LIMIT 20
    """
)

run_query(
    "78. Order size categories",
    """
    SELECT
        order_id,
        item_count,

        CASE
            WHEN item_count IS NULL
                THEN 'No item data'

            WHEN item_count = 1
                THEN 'Single item'

            WHEN item_count BETWEEN 2 AND 3
                THEN '2-3 items'

            ELSE '4+ items'
        END AS order_size

    FROM fact_orders

    ORDER BY item_count DESC

    LIMIT 30
    """
)

run_query(
    "79. Order size performance",
    """
    WITH order_sizes AS (

        SELECT
            order_id,
            total_payment_value,
            delivery_days,

            CASE
                WHEN item_count IS NULL
                    THEN 'No item data'

                WHEN item_count = 1
                    THEN 'Single item'

                WHEN item_count BETWEEN 2 AND 3
                    THEN '2-3 items'

                ELSE '4+ items'
            END AS order_size

        FROM fact_orders
    )

    SELECT
        order_size,

        COUNT(*) AS order_count,

        AVG(total_payment_value)
            AS average_payment_value,

        AVG(delivery_days)
            AS average_delivery_days

    FROM order_sizes

    GROUP BY order_size

    ORDER BY order_count DESC
    """
)

run_query(
    "80. Delivered orders classification",
    """
    WITH eligible_states AS (

        SELECT
            customer_state

        FROM fact_orders

        WHERE order_status = 'delivered'

        GROUP BY customer_state

        HAVING COUNT(*) >= 500
    ),

    delivered_orders AS (

        SELECT
            customer_state,
            order_id,
            total_payment_value,
            delivery_days,
            delivery_delay_days,

            CASE
                WHEN delivery_delay_days < 0
                    THEN 'Early'

                WHEN delivery_delay_days = 0
                    THEN 'On Time'

                WHEN delivery_delay_days > 0
                    THEN 'Late'
            END AS delivery_performance

        FROM fact_orders

        WHERE
            order_status = 'delivered'
            AND delivery_delay_days IS NOT NULL
    )

    SELECT
        d.customer_state,
        d.delivery_performance,

        COUNT(*) AS order_count,

        AVG(d.delivery_days)
            AS average_delivery_days,

        AVG(d.total_payment_value)
            AS average_payment_value

    FROM delivered_orders AS d

    INNER JOIN eligible_states AS e
        ON d.customer_state = e.customer_state

    GROUP BY
        d.customer_state,
        d.delivery_performance

    ORDER BY
        d.customer_state,
        d.delivery_performance
    """
)

run_query(
    "81. Combined customer and seller participants",
    """
    SELECT
        customer_unique_id
            AS participant_id,

        latest_customer_state
            AS state,

        'customer'
            AS participant_type

    FROM dim_customer


    UNION ALL


    SELECT
        seller_id
            AS participant_id,

        seller_state
            AS state,

        'seller'
            AS participant_type

    FROM dim_seller

    LIMIT 30
    """
)

run_query(
    "82. Customer and seller counts by state",
    """
    WITH participants AS (

        SELECT
            customer_unique_id
                AS participant_id,

            latest_customer_state
                AS state,

            'customer'
                AS participant_type

        FROM dim_customer


        UNION ALL


        SELECT
            seller_id
                AS participant_id,

            seller_state
                AS state,

            'seller'
                AS participant_type

        FROM dim_seller
    )

    SELECT
        state,

        COUNT(*) FILTER (
            WHERE participant_type = 'customer'
        ) AS customer_count,

        COUNT(*) FILTER (
            WHERE participant_type = 'seller'
        ) AS seller_count,

        COUNT(*) AS total_participants

    FROM participants

    GROUP BY state

    ORDER BY total_participants DESC
    """
)

run_query(
    "83. Validate UNION ALL participant counts",
    """
    WITH participants AS (

        SELECT
            customer_unique_id
                AS participant_id,

            'customer'
                AS participant_type

        FROM dim_customer

        UNION ALL

        SELECT
            seller_id
                AS participant_id,

            'seller'
                AS participant_type

        FROM dim_seller
    )

    SELECT
        COUNT(*) AS total_participants,

        COUNT(*) FILTER (
            WHERE participant_type = 'customer'
        ) AS customers,

        COUNT(*) FILTER (
            WHERE participant_type = 'seller'
        ) AS sellers

    FROM participants
    """
)