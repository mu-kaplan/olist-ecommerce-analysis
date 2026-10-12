-- 
-- OLIST E-COMMERCE ANALYSIS
-- 02 - SALES AND TIME TRENDS
-- 
--
-- Objective:
-- Evaluate temporal order and payment trends while explicitly
-- accounting for incomplete or sparsely observed periods.
--
-- Primary commercial measures use delivered orders unless
-- stated otherwise.
-- 
-- Main comparable trend window:
-- 2017-01-01 through 2018-08-31.
--
-- Earlier months are extremely sparse and include a completely
-- unobserved November 2016.
--
-- September-October 2018 contain only a handful of purchases and
-- no delivered orders, indicating incomplete end-of-period coverage.
--
-- These boundary periods are retained in the source data but
-- excluded from comparative monthly trend analysis.
-- 
-- 1. PURCHASE-DATA COVERAGE
-- 

SELECT
    MIN(order_purchase_timestamp)
        AS first_purchase_timestamp,

    MAX(order_purchase_timestamp)
        AS last_purchase_timestamp,

    COUNT(*) AS total_orders

FROM fact_orders;

-- 
-- 2. CONTINUOUS MONTHLY ORDER COVERAGE
-- 

WITH purchase_bounds AS (

    SELECT
        DATE_TRUNC(
            'month',
            MIN(order_purchase_timestamp)
        ) AS first_month,

        DATE_TRUNC(
            'month',
            MAX(order_purchase_timestamp)
        ) AS last_month

    FROM fact_orders
),

month_spine AS (

    SELECT DISTINCT
        DATE_TRUNC(
            'month',
            d.date
        ) AS purchase_month

    FROM dim_date AS d

    CROSS JOIN purchase_bounds AS b

    WHERE
        d.date >= b.first_month
        AND d.date
            < b.last_month + INTERVAL '1 month'
),

monthly_orders AS (

    SELECT
        DATE_TRUNC(
            'month',
            order_purchase_timestamp
        ) AS purchase_month,

        COUNT(*) AS total_orders,

        COUNT(*) FILTER (
            WHERE order_status = 'delivered'
        ) AS delivered_orders,

        COUNT(*) FILTER (
            WHERE order_status = 'canceled'
        ) AS canceled_orders,

        COUNT(*) FILTER (
            WHERE order_status = 'shipped'
        ) AS shipped_orders,

        COUNT(*) FILTER (
            WHERE order_status = 'unavailable'
        ) AS unavailable_orders,

        SUM(total_payment_value) FILTER (
            WHERE order_status = 'delivered'
        ) AS delivered_payment_value

    FROM fact_orders

    GROUP BY
        DATE_TRUNC(
            'month',
            order_purchase_timestamp
        )
)

SELECT
    m.purchase_month,

    COALESCE(
        o.total_orders,
        0
    ) AS total_orders,

    COALESCE(
        o.delivered_orders,
        0
    ) AS delivered_orders,

    COALESCE(
        o.canceled_orders,
        0
    ) AS canceled_orders,

    COALESCE(
        o.shipped_orders,
        0
    ) AS shipped_orders,

    COALESCE(
        o.unavailable_orders,
        0
    ) AS unavailable_orders,

    ROUND(
        100.0
        * COALESCE(o.delivered_orders, 0)
        / NULLIF(
            COALESCE(o.total_orders, 0),
            0
        ),
        2
    ) AS delivered_share_pct,

    ROUND(
        COALESCE(
            o.delivered_payment_value,
            0
        ),
        2
    ) AS delivered_payment_value

FROM month_spine AS m

LEFT JOIN monthly_orders AS o
    ON m.purchase_month
     = o.purchase_month

ORDER BY
    m.purchase_month;

-- 
-- 3. END-OF-DATASET STATUS DIAGNOSTIC
-- 

SELECT
    DATE_TRUNC(
        'month',
        order_purchase_timestamp
    ) AS purchase_month,

    order_status,

    COUNT(*) AS order_count

FROM fact_orders

WHERE
    order_purchase_timestamp
        >= TIMESTAMP '2018-07-01'

GROUP BY
    DATE_TRUNC(
        'month',
        order_purchase_timestamp
    ),
    order_status

ORDER BY
    purchase_month,
    order_count DESC;

-- 
-- 4. COMPARABLE MONTHLY PERFORMANCE
-- 

SELECT
    DATE_TRUNC(
        'month',
        order_purchase_timestamp
    ) AS purchase_month,

    COUNT(*) AS delivered_orders,

    COUNT(DISTINCT customer_unique_id)
        AS unique_customers,

    ROUND(
        SUM(total_payment_value),
        2
    ) AS total_payment_value,

    ROUND(
        AVG(total_payment_value),
        2
    ) AS average_payment_value,

    ROUND(
        SUM(item_sales_value),
        2
    ) AS item_sales_value,

    ROUND(
        SUM(freight_value),
        2
    ) AS freight_value

FROM fact_orders

WHERE
    order_status = 'delivered'

    AND order_purchase_timestamp
        >= TIMESTAMP '2017-01-01'

    AND order_purchase_timestamp
        < TIMESTAMP '2018-09-01'

GROUP BY
    DATE_TRUNC(
        'month',
        order_purchase_timestamp
    )

ORDER BY
    purchase_month;

-- 
-- 5. MONTH-OVER-MONTH PERFORMANCE
-- 
WITH monthly_performance AS (

    SELECT
        DATE_TRUNC(
            'month',
            order_purchase_timestamp
        ) AS purchase_month,

        COUNT(*) AS delivered_orders,

        SUM(total_payment_value)
            AS total_payment_value

    FROM fact_orders

    WHERE
        order_status = 'delivered'

        AND order_purchase_timestamp
            >= TIMESTAMP '2017-01-01'

        AND order_purchase_timestamp
            < TIMESTAMP '2018-09-01'

    GROUP BY
        DATE_TRUNC(
            'month',
            order_purchase_timestamp
        )
),

with_previous_month AS (

    SELECT
        purchase_month,
        delivered_orders,
        total_payment_value,

        LAG(delivered_orders) OVER (
            ORDER BY purchase_month
        ) AS previous_month_orders,

        LAG(total_payment_value) OVER (
            ORDER BY purchase_month
        ) AS previous_month_payment

    FROM monthly_performance
)

SELECT
    purchase_month,

    delivered_orders,

    previous_month_orders,

    ROUND(
        100.0
        * (
            delivered_orders
            - previous_month_orders
        )
        / NULLIF(
            previous_month_orders,
            0
        ),
        2
    ) AS order_growth_mom_pct,

    ROUND(
        total_payment_value,
        2
    ) AS total_payment_value,

    ROUND(
        previous_month_payment,
        2
    ) AS previous_month_payment,

    ROUND(
        100.0
        * (
            total_payment_value
            - previous_month_payment
        )
        / NULLIF(
            previous_month_payment,
            0
        ),
        2
    ) AS payment_growth_mom_pct

FROM with_previous_month

ORDER BY purchase_month;

-- 
-- 6. YEAR-OVER-YEAR PERFORMANCE
-- 

WITH monthly_performance AS (

    SELECT
        DATE_TRUNC(
            'month',
            order_purchase_timestamp
        ) AS purchase_month,

        COUNT(*) AS delivered_orders,

        SUM(total_payment_value)
            AS total_payment_value

    FROM fact_orders

    WHERE
        order_status = 'delivered'

        AND order_purchase_timestamp
            >= TIMESTAMP '2017-01-01'

        AND order_purchase_timestamp
            < TIMESTAMP '2018-09-01'

    GROUP BY
        DATE_TRUNC(
            'month',
            order_purchase_timestamp
        )
),

with_previous_year AS (

    SELECT
        purchase_month,
        delivered_orders,
        total_payment_value,

        LAG(
            delivered_orders,
            12
        ) OVER (
            ORDER BY purchase_month
        ) AS previous_year_orders,

        LAG(
            total_payment_value,
            12
        ) OVER (
            ORDER BY purchase_month
        ) AS previous_year_payment

    FROM monthly_performance
)

SELECT
    purchase_month,

    delivered_orders,
    previous_year_orders,

    ROUND(
        100.0
        * (
            delivered_orders
            - previous_year_orders
        )
        / NULLIF(
            previous_year_orders,
            0
        ),
        2
    ) AS order_growth_yoy_pct,

    ROUND(
        total_payment_value,
        2
    ) AS total_payment_value,

    ROUND(
        previous_year_payment,
        2
    ) AS previous_year_payment,

    ROUND(
        100.0
        * (
            total_payment_value
            - previous_year_payment
        )
        / NULLIF(
            previous_year_payment,
            0
        ),
        2
    ) AS payment_growth_yoy_pct

FROM with_previous_year

WHERE previous_year_orders IS NOT NULL

ORDER BY purchase_month;

-- 
-- 7. AVERAGE PAYMENT VALUE TREND
-- 

WITH monthly_performance AS (

    SELECT
        DATE_TRUNC(
            'month',
            order_purchase_timestamp
        ) AS purchase_month,

        COUNT(*) AS delivered_orders,

        SUM(total_payment_value)
            AS total_payment_value,

        AVG(total_payment_value)
            AS average_payment_value

    FROM fact_orders

    WHERE
        order_status = 'delivered'

        AND order_purchase_timestamp
            >= TIMESTAMP '2017-01-01'

        AND order_purchase_timestamp
            < TIMESTAMP '2018-09-01'

    GROUP BY
        DATE_TRUNC(
            'month',
            order_purchase_timestamp
        )
),

with_previous_year AS (

    SELECT
        purchase_month,
        delivered_orders,
        total_payment_value,
        average_payment_value,

        LAG(
            average_payment_value,
            12
        ) OVER (
            ORDER BY purchase_month
        ) AS previous_year_average_payment

    FROM monthly_performance
)

SELECT
    purchase_month,
    delivered_orders,

    ROUND(
        total_payment_value,
        2
    ) AS total_payment_value,

    ROUND(
        average_payment_value,
        2
    ) AS average_payment_value,

    ROUND(
        previous_year_average_payment,
        2
    ) AS previous_year_average_payment,

    ROUND(
        100.0
        * (
            average_payment_value
            - previous_year_average_payment
        )
        / NULLIF(
            previous_year_average_payment,
            0
        ),
        2
    ) AS average_payment_growth_yoy_pct

FROM with_previous_year

ORDER BY purchase_month;

-- 
-- 8. THREE-MONTH ROLLING ORDER TREND
-- 

WITH monthly_performance AS (

    SELECT
        DATE_TRUNC(
            'month',
            order_purchase_timestamp
        ) AS purchase_month,

        COUNT(*) AS delivered_orders,

        SUM(total_payment_value)
            AS total_payment_value

    FROM fact_orders

    WHERE
        order_status = 'delivered'

        AND order_purchase_timestamp
            >= TIMESTAMP '2017-01-01'

        AND order_purchase_timestamp
            < TIMESTAMP '2018-09-01'

    GROUP BY
        DATE_TRUNC(
            'month',
            order_purchase_timestamp
        )
)

SELECT
    purchase_month,

    delivered_orders,

    ROUND(
        AVG(delivered_orders) OVER (
            ORDER BY purchase_month

            ROWS BETWEEN
                2 PRECEDING
                AND CURRENT ROW
        ),
        2
    ) AS three_month_avg_orders,

    ROUND(
        total_payment_value,
        2
    ) AS total_payment_value,

    ROUND(
        AVG(total_payment_value) OVER (
            ORDER BY purchase_month

            ROWS BETWEEN
                2 PRECEDING
                AND CURRENT ROW
        ),
        2
    ) AS three_month_avg_payment

FROM monthly_performance

ORDER BY purchase_month;

