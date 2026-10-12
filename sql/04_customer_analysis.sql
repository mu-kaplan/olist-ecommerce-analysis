-- 
-- OLIST E-COMMERCE ANALYSIS
-- 04 - CUSTOMER ANALYSIS
-- 
--
-- Primary customer identifier:
-- customer_unique_id
--
-- Main behavioral scope:
-- Delivered orders only.
--
-- Customer metrics below are recalculated from delivered orders
-- rather than assuming every historical order was successfully
-- completed.
-- 

-- 
-- 1. DELIVERED CUSTOMER-LEVEL PERFORMANCE
-- 

WITH customer_performance AS (

    SELECT
        customer_unique_id,

        COUNT(*) AS delivered_order_count,

        SUM(total_payment_value)
            AS lifetime_payment_value,

        AVG(total_payment_value)
            AS average_order_payment,

        MIN(order_purchase_timestamp)
            AS first_delivered_purchase,

        MAX(order_purchase_timestamp)
            AS last_delivered_purchase

    FROM fact_orders

    WHERE order_status = 'delivered'

    GROUP BY customer_unique_id
)

SELECT
    COUNT(*) AS delivered_customers,

    COUNT(*) FILTER (
        WHERE delivered_order_count = 1
    ) AS one_time_customers,

    COUNT(*) FILTER (
        WHERE delivered_order_count >= 2
    ) AS repeat_customers,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE delivered_order_count >= 2
        )
        / COUNT(*),
        2
    ) AS repeat_customer_rate_pct,

    ROUND(
        AVG(delivered_order_count),
        2
    ) AS average_orders_per_customer,

    MAX(delivered_order_count)
        AS maximum_delivered_orders,

    ROUND(
        AVG(lifetime_payment_value),
        2
    ) AS average_customer_payment_value

FROM customer_performance;

-- 
-- 2. ONE-TIME VS REPEAT CUSTOMER PERFORMANCE
-- 

WITH customer_performance AS (

    SELECT
        customer_unique_id,

        COUNT(*) AS delivered_order_count,

        SUM(total_payment_value)
            AS lifetime_payment_value,

        AVG(total_payment_value)
            AS average_order_payment

    FROM fact_orders

    WHERE order_status = 'delivered'

    GROUP BY customer_unique_id
),

customer_segments AS (

    SELECT
        customer_unique_id,
        delivered_order_count,
        lifetime_payment_value,
        average_order_payment,

        CASE
            WHEN delivered_order_count = 1
                THEN 'One-time customer'

            ELSE 'Repeat customer'
        END AS customer_segment

    FROM customer_performance
)

SELECT
    customer_segment,

    COUNT(*) AS customer_count,

    SUM(delivered_order_count)
        AS delivered_orders,

    ROUND(
        AVG(delivered_order_count),
        2
    ) AS average_orders_per_customer,

    ROUND(
        SUM(lifetime_payment_value),
        2
    ) AS total_payment_value,

    ROUND(
        AVG(lifetime_payment_value),
        2
    ) AS average_lifetime_payment_value,

    ROUND(
        AVG(average_order_payment),
        2
    ) AS average_order_payment

FROM customer_segments

GROUP BY customer_segment

ORDER BY customer_count DESC;

-- 
-- 3. CUSTOMER PAYMENT-VALUE CONCENTRATION
--

WITH customer_value AS (

    SELECT
        customer_unique_id,

        COUNT(*) AS delivered_order_count,

        SUM(total_payment_value)
            AS lifetime_payment_value

    FROM fact_orders

    WHERE order_status = 'delivered'

    GROUP BY customer_unique_id
),

ranked_customers AS (

    SELECT
        customer_unique_id,
        delivered_order_count,
        lifetime_payment_value,

        ROW_NUMBER() OVER (
            ORDER BY
                lifetime_payment_value DESC,
                customer_unique_id
        ) AS customer_rank,

        COUNT(*) OVER ()
            AS total_customers,

        SUM(lifetime_payment_value) OVER ()
            AS total_payment_value

    FROM customer_value
)

SELECT
    total_customers,

    CEIL(
        MAX(total_customers) * 0.01
    ) AS top_1_pct_customer_count,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN customer_rank
                     <= CEIL(total_customers * 0.01)
                    THEN lifetime_payment_value
                ELSE 0
            END
        )
        / MAX(total_payment_value),
        2
    ) AS top_1_pct_payment_share,

    CEIL(
        MAX(total_customers) * 0.05
    ) AS top_5_pct_customer_count,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN customer_rank
                     <= CEIL(total_customers * 0.05)
                    THEN lifetime_payment_value
                ELSE 0
            END
        )
        / MAX(total_payment_value),
        2
    ) AS top_5_pct_payment_share,

    CEIL(
        MAX(total_customers) * 0.10
    ) AS top_10_pct_customer_count,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN customer_rank
                     <= CEIL(total_customers * 0.10)
                    THEN lifetime_payment_value
                ELSE 0
            END
        )
        / MAX(total_payment_value),
        2
    ) AS top_10_pct_payment_share

FROM ranked_customers

GROUP BY total_customers;

-- 
-- 4. HIGHEST-VALUE OBSERVED CUSTOMERS
-- 

WITH customer_value AS (

    SELECT
        customer_unique_id,

        COUNT(*) AS delivered_order_count,

        SUM(total_payment_value)
            AS lifetime_payment_value,

        AVG(total_payment_value)
            AS average_order_payment,

        MIN(order_purchase_timestamp)
            AS first_purchase,

        MAX(order_purchase_timestamp)
            AS last_purchase

    FROM fact_orders

    WHERE order_status = 'delivered'

    GROUP BY customer_unique_id
)

SELECT
    customer_unique_id,
    delivered_order_count,

    ROUND(
        lifetime_payment_value,
        2
    ) AS lifetime_payment_value,

    ROUND(
        average_order_payment,
        2
    ) AS average_order_payment,

    first_purchase,
    last_purchase

FROM customer_value

ORDER BY
    lifetime_payment_value DESC

LIMIT 20;

-- 
-- 5. CUSTOMER ORDER-FREQUENCY DISTRIBUTION
-- 

WITH customer_frequency AS (

    SELECT
        customer_unique_id,

        COUNT(*) AS delivered_order_count,

        SUM(total_payment_value)
            AS lifetime_payment_value

    FROM fact_orders

    WHERE order_status = 'delivered'

    GROUP BY customer_unique_id
)

SELECT
    delivered_order_count,

    COUNT(*) AS customer_count,

    ROUND(
        100.0
        * COUNT(*)
        / SUM(COUNT(*)) OVER (),
        2
    ) AS customer_share_pct,

    ROUND(
        SUM(lifetime_payment_value),
        2
    ) AS total_payment_value,

    ROUND(
        100.0
        * SUM(lifetime_payment_value)
        / SUM(SUM(lifetime_payment_value)) OVER (),
        2
    ) AS payment_share_pct

FROM customer_frequency

GROUP BY delivered_order_count

ORDER BY delivered_order_count;

-- 
-- 6. TIME BETWEEN DELIVERED PURCHASES
-- 

WITH ordered_purchases AS (

    SELECT
        customer_unique_id,
        order_id,
        order_purchase_timestamp,

        LEAD(
            order_purchase_timestamp
        ) OVER (
            PARTITION BY customer_unique_id
            ORDER BY
                order_purchase_timestamp,
                order_id
        ) AS next_purchase_timestamp

    FROM fact_orders

    WHERE order_status = 'delivered'
),

repeat_intervals AS (

    SELECT
        customer_unique_id,

        DATE_DIFF(
            'day',
            order_purchase_timestamp,
            next_purchase_timestamp
        ) AS days_to_next_purchase

    FROM ordered_purchases

    WHERE next_purchase_timestamp IS NOT NULL
)

SELECT
    COUNT(*) AS repeat_purchase_intervals,

    ROUND(
        AVG(days_to_next_purchase),
        2
    ) AS average_days_to_next_purchase,

    MEDIAN(
        days_to_next_purchase
    ) AS median_days_to_next_purchase,

    MIN(
        days_to_next_purchase
    ) AS minimum_days_to_next_purchase,

    MAX(
        days_to_next_purchase
    ) AS maximum_days_to_next_purchase

FROM repeat_intervals;

-- 
-- 7. MONTHLY CUSTOMER COHORT RETENTION
--

WITH delivered_orders AS (

    SELECT
        customer_unique_id,

        DATE_TRUNC(
            'month',
            order_purchase_timestamp
        ) AS purchase_month

    FROM fact_orders

    WHERE
        order_status = 'delivered'

        AND order_purchase_timestamp
            >= TIMESTAMP '2017-01-01'

        AND order_purchase_timestamp
            < TIMESTAMP '2018-09-01'
),

first_purchase AS (

    SELECT
        customer_unique_id,

        MIN(purchase_month)
            AS cohort_month

    FROM delivered_orders

    GROUP BY customer_unique_id
),

cohort_activity AS (

    SELECT DISTINCT
        d.customer_unique_id,

        f.cohort_month,

        d.purchase_month,

        DATE_DIFF(
            'month',
            f.cohort_month,
            d.purchase_month
        ) AS cohort_month_number

    FROM delivered_orders AS d

    INNER JOIN first_purchase AS f
        ON d.customer_unique_id
         = f.customer_unique_id
),

cohort_size AS (

    SELECT
        cohort_month,

        COUNT(DISTINCT customer_unique_id)
            AS cohort_customers

    FROM first_purchase

    GROUP BY cohort_month
),

retention AS (

    SELECT
        cohort_month,
        cohort_month_number,

        COUNT(DISTINCT customer_unique_id)
            AS active_customers

    FROM cohort_activity

    GROUP BY
        cohort_month,
        cohort_month_number
)

SELECT
    r.cohort_month,
    r.cohort_month_number,
    c.cohort_customers,
    r.active_customers,

    ROUND(
        100.0
        * r.active_customers
        / c.cohort_customers,
        2
    ) AS retention_rate_pct

FROM retention AS r

INNER JOIN cohort_size AS c
    ON r.cohort_month
     = c.cohort_month

ORDER BY
    r.cohort_month,
    r.cohort_month_number;

--
-- 8. FIRST SIX MONTHS OF COHORT RETENTION WITH UNOBSERVABLE MONTHS SHOWN AS NULL
--   


WITH delivered_orders AS (

    SELECT
        customer_unique_id,

        DATE_TRUNC(
            'month',
            order_purchase_timestamp
        ) AS purchase_month

    FROM fact_orders

    WHERE
        order_status = 'delivered'

        AND order_purchase_timestamp
            >= TIMESTAMP '2017-01-01'

        AND order_purchase_timestamp
            < TIMESTAMP '2018-09-01'
),

first_purchase AS (

    SELECT
        customer_unique_id,

        MIN(purchase_month)
            AS cohort_month

    FROM delivered_orders

    GROUP BY customer_unique_id
),

cohort_activity AS (

    SELECT DISTINCT
        d.customer_unique_id,
        f.cohort_month,

        DATE_DIFF(
            'month',
            f.cohort_month,
            d.purchase_month
        ) AS cohort_month_number

    FROM delivered_orders AS d

    INNER JOIN first_purchase AS f
        ON d.customer_unique_id
         = f.customer_unique_id
),

cohort_size AS (

    SELECT
        cohort_month,

        COUNT(*) AS cohort_customers

    FROM first_purchase

    GROUP BY cohort_month
)

SELECT
    a.cohort_month,
    s.cohort_customers,

    CASE
        WHEN DATE_DIFF(
            'month',
            a.cohort_month,
            DATE '2018-08-01'
        ) >= 1

        THEN ROUND(
            100.0
            * COUNT(DISTINCT CASE
                WHEN cohort_month_number = 1
                THEN customer_unique_id
            END)
            / s.cohort_customers,
            2
        )
    END AS month_1_retention_pct,

    CASE
        WHEN DATE_DIFF(
            'month',
            a.cohort_month,
            DATE '2018-08-01'
        ) >= 2

        THEN ROUND(
            100.0
            * COUNT(DISTINCT CASE
                WHEN cohort_month_number = 2
                THEN customer_unique_id
            END)
            / s.cohort_customers,
            2
        )
    END AS month_2_retention_pct,

    CASE
        WHEN DATE_DIFF(
            'month',
            a.cohort_month,
            DATE '2018-08-01'
        ) >= 3

        THEN ROUND(
            100.0
            * COUNT(DISTINCT CASE
                WHEN cohort_month_number = 3
                THEN customer_unique_id
            END)
            / s.cohort_customers,
            2
        )
    END AS month_3_retention_pct,

    CASE
        WHEN DATE_DIFF(
            'month',
            a.cohort_month,
            DATE '2018-08-01'
        ) >= 4

        THEN ROUND(
            100.0
            * COUNT(DISTINCT CASE
                WHEN cohort_month_number = 4
                THEN customer_unique_id
            END)
            / s.cohort_customers,
            2
        )
    END AS month_4_retention_pct,

    CASE
        WHEN DATE_DIFF(
            'month',
            a.cohort_month,
            DATE '2018-08-01'
        ) >= 5

        THEN ROUND(
            100.0
            * COUNT(DISTINCT CASE
                WHEN cohort_month_number = 5
                THEN customer_unique_id
            END)
            / s.cohort_customers,
            2
        )
    END AS month_5_retention_pct,

    CASE
        WHEN DATE_DIFF(
            'month',
            a.cohort_month,
            DATE '2018-08-01'
        ) >= 6

        THEN ROUND(
            100.0
            * COUNT(DISTINCT CASE
                WHEN cohort_month_number = 6
                THEN customer_unique_id
            END)
            / s.cohort_customers,
            2
        )
    END AS month_6_retention_pct

FROM cohort_activity AS a

INNER JOIN cohort_size AS s
    ON a.cohort_month
     = s.cohort_month

GROUP BY
    a.cohort_month,
    s.cohort_customers

ORDER BY
    a.cohort_month;

--
-- 9. OVERALL COHORT RETENTION BY MONTH NUMBER
--

WITH delivered_orders AS (

    SELECT
        customer_unique_id,

        DATE_TRUNC(
            'month',
            order_purchase_timestamp
        ) AS purchase_month

    FROM fact_orders

    WHERE
        order_status = 'delivered'

        AND order_purchase_timestamp
            >= TIMESTAMP '2017-01-01'

        AND order_purchase_timestamp
            < TIMESTAMP '2018-09-01'
),

first_purchase AS (

    SELECT
        customer_unique_id,

        MIN(purchase_month)
            AS cohort_month

    FROM delivered_orders

    GROUP BY customer_unique_id
),

cohort_activity AS (

    SELECT DISTINCT
        d.customer_unique_id,
        f.cohort_month,

        DATE_DIFF(
            'month',
            f.cohort_month,
            d.purchase_month
        ) AS cohort_month_number

    FROM delivered_orders AS d

    INNER JOIN first_purchase AS f
        ON d.customer_unique_id
         = f.customer_unique_id
),

cohort_size AS (

    SELECT
        cohort_month,

        COUNT(*) AS cohort_customers

    FROM first_purchase

    GROUP BY cohort_month
),

activity_by_month AS (

    SELECT
        cohort_month,
        cohort_month_number,

        COUNT(DISTINCT customer_unique_id)
            AS active_customers

    FROM cohort_activity

    WHERE cohort_month_number BETWEEN 1 AND 6

    GROUP BY
        cohort_month,
        cohort_month_number
),

month_numbers AS (

    SELECT *
    FROM (
        VALUES
            (1),
            (2),
            (3),
            (4),
            (5),
            (6)
    ) AS t(cohort_month_number)
),

eligible_cohort_months AS (

    SELECT
        c.cohort_month,
        c.cohort_customers,
        m.cohort_month_number

    FROM cohort_size AS c

    CROSS JOIN month_numbers AS m

    WHERE
        DATE_DIFF(
            'month',
            c.cohort_month,
            DATE '2018-08-01'
        ) >= m.cohort_month_number
)

SELECT
    e.cohort_month_number,

    SUM(
        COALESCE(a.active_customers, 0)
    ) AS active_customers,

    SUM(
        e.cohort_customers
    ) AS eligible_cohort_customers,

    ROUND(
        100.0
        * SUM(
            COALESCE(a.active_customers, 0)
        )
        / SUM(e.cohort_customers),
        2
    ) AS weighted_retention_pct

FROM eligible_cohort_months AS e

LEFT JOIN activity_by_month AS a
    ON e.cohort_month = a.cohort_month
    AND e.cohort_month_number
        = a.cohort_month_number

GROUP BY
    e.cohort_month_number

ORDER BY
    e.cohort_month_number;

