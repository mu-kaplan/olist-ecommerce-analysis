-- 
-- OLIST E-COMMERCE ANALYSIS
-- 09 - STATISTICAL AND ROBUSTNESS CHECKS
-- 
--
-- Purpose:
-- Quantify several relationships identified during exploratory
-- analysis and check whether headline findings remain visible
-- across large order-level populations.
--
-- These are observational associations and should not be
-- interpreted as causal effects.
-- 

-- 
-- 1. ORDER-LEVEL CORRELATIONS WITH REVIEW SCORE
-- 

SELECT
    COUNT(*) AS orders_analyzed,

    ROUND(
        CORR(
            delivery_days,
            review_score
        ),
        3
    ) AS corr_delivery_days_review,

    ROUND(
        CORR(
            delivery_delay_days,
            review_score
        ),
        3
    ) AS corr_delay_vs_review,

    ROUND(
        CORR(
            freight_value,
            review_score
        ),
        3
    ) AS corr_freight_vs_review,

    ROUND(
        CORR(
            total_payment_value,
            review_score
        ),
        3
    ) AS corr_payment_vs_review,

    ROUND(
        CORR(
            item_count,
            review_score
        ),
        3
    ) AS corr_item_count_vs_review

FROM fact_orders

WHERE
    order_status = 'delivered'
    AND review_score IS NOT NULL
    AND delivery_days IS NOT NULL
    AND delivery_delay_days IS NOT NULL;

-- 
-- 2. REVIEW SCORE ACROSS DELIVERY-DELAY DECILES
-- 

WITH reviewed_orders AS (

    SELECT
        delivery_delay_days,
        review_score,

        NTILE(10) OVER (
            ORDER BY delivery_delay_days
        ) AS delay_decile

    FROM fact_orders

    WHERE
        order_status = 'delivered'
        AND review_score IS NOT NULL
        AND delivery_delay_days IS NOT NULL
),

decile_summary AS (

    SELECT
        delay_decile,

        COUNT(*) AS order_count,

        AVG(delivery_delay_days)
            AS average_delay_days,

        AVG(review_score)
            AS average_review_score,

        100.0
        * COUNT(*) FILTER (
            WHERE review_score <= 2
        )
        / COUNT(*)
            AS negative_review_rate_pct

    FROM reviewed_orders

    GROUP BY delay_decile
)

SELECT
    delay_decile,
    order_count,

    ROUND(
        average_delay_days,
        2
    ) AS average_delay_days,

    ROUND(
        average_review_score,
        2
    ) AS average_review_score,

    ROUND(
        negative_review_rate_pct,
        2
    ) AS negative_review_rate_pct

FROM decile_summary

ORDER BY delay_decile;

-- 
-- 3. SAME-STATE VS INTERSTATE DELIVERY WITHIN STATES
-- 

WITH single_seller_orders AS (

    SELECT DISTINCT
        oi.order_id,
        oi.seller_state

    FROM fact_order_items AS oi

    INNER JOIN fact_orders AS o
        ON oi.order_id = o.order_id

    WHERE
        o.order_status = 'delivered'
        AND o.unique_seller_count = 1
),

classified_orders AS (

    SELECT
        o.customer_state,

        CASE
            WHEN o.customer_state = s.seller_state
                THEN 'Same state'

            ELSE 'Interstate'
        END AS fulfillment_type,

        o.delivery_days,
        o.delivery_delay_days,
        o.freight_value

    FROM fact_orders AS o

    INNER JOIN single_seller_orders AS s
        ON o.order_id = s.order_id

    WHERE
        o.delivery_delay_days IS NOT NULL
)

SELECT
    customer_state,
    fulfillment_type,

    COUNT(*) AS order_count,

    ROUND(
        AVG(delivery_days),
        2
    ) AS average_delivery_days,

    ROUND(
        AVG(freight_value),
        2
    ) AS average_freight_value,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE delivery_delay_days > 0
        )
        / COUNT(*),
        2
    ) AS late_delivery_rate_pct

FROM classified_orders

WHERE customer_state IN (
    'SP',
    'RJ',
    'MG',
    'RS',
    'PR',
    'SC'
)

GROUP BY
    customer_state,
    fulfillment_type

HAVING COUNT(*) >= 100

ORDER BY
    customer_state,
    fulfillment_type;

-- 
-- 4. FREIGHT VS DELIVERY DURATION
-- 

SELECT
    COUNT(*) AS orders_analyzed,

    ROUND(
        CORR(
            freight_value,
            delivery_days
        ),
        3
    ) AS corr_freight_vs_delivery_days,

    ROUND(
        CORR(
            freight_value,
            carrier_to_customer_days
        ),
        3
    ) AS corr_freight_vs_carrier_days,

    ROUND(
        CORR(
            freight_value,
            delivery_delay_days
        ),
        3
    ) AS corr_freight_vs_delay

FROM fact_orders

WHERE
    order_status = 'delivered'
    AND delivery_days IS NOT NULL
    AND carrier_to_customer_days IS NOT NULL
    AND delivery_delay_days IS NOT NULL;

