-- 
-- OLIST E-COMMERCE ANALYSIS
-- 05 - DELIVERY AND OPERATIONS
-- 
--
-- Primary grain:
-- One row per order.
--
-- Main scope:
-- Delivered orders with classifiable delivery timing.
--
-- delivery_days:
-- Purchase timestamp to customer delivery.
--
-- delivery_delay_days:
-- Actual delivery date minus promised delivery date.
-- Negative = early, zero = promised date, positive = late.
-- 

-- 
-- 1. DELIVERY PERFORMANCE BY CUSTOMER STATE
-- 

SELECT
    customer_state,

    COUNT(*) AS delivered_orders,

    ROUND(
        AVG(delivery_days),
        2
    ) AS average_delivery_days,

    ROUND(
        MEDIAN(delivery_days),
        2
    ) AS median_delivery_days,

    COUNT(*) FILTER (
        WHERE delivery_delay_days > 0
    ) AS late_orders,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE delivery_delay_days > 0
        )
        / COUNT(*),
        2
    ) AS late_delivery_rate_pct,

    ROUND(
        AVG(delivery_delay_days),
        2
    ) AS average_days_vs_promise,

    ROUND(
        AVG(purchase_to_carrier_days),
        2
    ) AS average_purchase_to_carrier_days,

    ROUND(
        AVG(carrier_to_customer_days),
        2
    ) AS average_carrier_to_customer_days,

    ROUND(
        AVG(freight_value),
        2
    ) AS average_freight_value

FROM fact_orders

WHERE
    order_status = 'delivered'
    AND delivery_delay_days IS NOT NULL

GROUP BY
    customer_state

HAVING COUNT(*) >= 500

ORDER BY
    late_delivery_rate_pct DESC;

-- 
-- 2. DELIVERY-STAGE DECOMPOSITION BY STATE
-- 

SELECT
    customer_state,

    COUNT(*) AS orders_with_complete_stages,

    ROUND(
        AVG(delivery_days),
        2
    ) AS average_delivery_days,

    ROUND(
        AVG(purchase_to_carrier_days),
        2
    ) AS average_purchase_to_carrier_days,

    ROUND(
        AVG(carrier_to_customer_days),
        2
    ) AS average_carrier_to_customer_days,

    ROUND(
        100.0
        * AVG(carrier_to_customer_days)
        / AVG(delivery_days),
        2
    ) AS carrier_stage_share_pct,

    ROUND(
        100.0
        * AVG(purchase_to_carrier_days)
        / AVG(delivery_days),
        2
    ) AS pre_carrier_stage_share_pct

FROM fact_orders

WHERE
    order_status = 'delivered'

    AND delivery_days IS NOT NULL
    AND purchase_to_carrier_days IS NOT NULL
    AND carrier_to_customer_days IS NOT NULL

GROUP BY customer_state

HAVING COUNT(*) >= 500

ORDER BY carrier_stage_share_pct DESC;

-- 
-- 3. DELIVERY STAGES: LATE VS NOT LATE
-- 

WITH classified_orders AS (

    SELECT
        order_id,

        CASE
            WHEN delivery_delay_days > 0
                THEN 'Late'

            ELSE 'Not late'
        END AS delivery_status,

        delivery_days,
        purchase_to_carrier_days,
        carrier_to_customer_days,
        freight_value,
        review_score

    FROM fact_orders

    WHERE
        order_status = 'delivered'

        AND delivery_delay_days IS NOT NULL
)

SELECT
    delivery_status,

    COUNT(*) AS order_count,

    ROUND(
        AVG(delivery_days),
        2
    ) AS average_delivery_days,

    ROUND(
        AVG(purchase_to_carrier_days),
        2
    ) AS average_purchase_to_carrier_days,

    ROUND(
        AVG(carrier_to_customer_days),
        2
    ) AS average_carrier_to_customer_days,

    ROUND(
        AVG(freight_value),
        2
    ) AS average_freight_value,

    ROUND(
        AVG(review_score),
        2
    ) AS average_review_score

FROM classified_orders

GROUP BY delivery_status

ORDER BY delivery_status;

-- 
-- 4. LATE-DELIVERY SEVERITY
-- 

SELECT
    CASE
        WHEN delivery_delay_days BETWEEN 1 AND 3
            THEN '1-3 days late'

        WHEN delivery_delay_days BETWEEN 4 AND 7
            THEN '4-7 days late'

        WHEN delivery_delay_days BETWEEN 8 AND 14
            THEN '8-14 days late'

        ELSE '15+ days late'
    END AS lateness_bucket,

    COUNT(*) AS order_count,

    ROUND(
        100.0
        * COUNT(*)
        / SUM(COUNT(*)) OVER (),
        2
    ) AS share_of_late_orders_pct,

    ROUND(
        AVG(delivery_delay_days),
        2
    ) AS average_days_late,

    ROUND(
        AVG(review_score),
        2
    ) AS average_review_score

FROM fact_orders

WHERE
    order_status = 'delivered'
    AND delivery_delay_days > 0

GROUP BY lateness_bucket

ORDER BY
    MIN(delivery_delay_days);

-- 
-- 5. REVIEW OUTCOMES BY DELIVERY PERFORMANCE
-- 

WITH delivery_groups AS (

    SELECT
        order_id,
        review_score,

        CASE
            WHEN delivery_delay_days < 0
                THEN 'Early'

            WHEN delivery_delay_days = 0
                THEN 'On promised date'

            WHEN delivery_delay_days BETWEEN 1 AND 3
                THEN '1-3 days late'

            WHEN delivery_delay_days BETWEEN 4 AND 7
                THEN '4-7 days late'

            WHEN delivery_delay_days BETWEEN 8 AND 14
                THEN '8-14 days late'

            ELSE '15+ days late'
        END AS delivery_performance,

        CASE
            WHEN delivery_delay_days < 0
                THEN 1

            WHEN delivery_delay_days = 0
                THEN 2

            WHEN delivery_delay_days BETWEEN 1 AND 3
                THEN 3

            WHEN delivery_delay_days BETWEEN 4 AND 7
                THEN 4

            WHEN delivery_delay_days BETWEEN 8 AND 14
                THEN 5

            ELSE 6
        END AS performance_order

    FROM fact_orders

    WHERE
        order_status = 'delivered'
        AND delivery_delay_days IS NOT NULL
        AND review_score IS NOT NULL
)

SELECT
    delivery_performance,

    COUNT(*) AS reviewed_orders,

    ROUND(
        AVG(review_score),
        2
    ) AS average_review_score,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE review_score >= 4
        )
        / COUNT(*),
        2
    ) AS positive_review_rate_pct,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE review_score = 3
        )
        / COUNT(*),
        2
    ) AS neutral_review_rate_pct,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE review_score <= 2
        )
        / COUNT(*),
        2
    ) AS negative_review_rate_pct

FROM delivery_groups

GROUP BY
    delivery_performance,
    performance_order

ORDER BY
    performance_order;

-- 
-- 6. NEGATIVE REVIEW RATE: LATE VS NOT LATE
-- 

WITH reviewed_orders AS (

    SELECT
        CASE
            WHEN delivery_delay_days > 0
                THEN 'Late'

            ELSE 'Not late'
        END AS delivery_status,

        review_score

    FROM fact_orders

    WHERE
        order_status = 'delivered'
        AND delivery_delay_days IS NOT NULL
        AND review_score IS NOT NULL
)

SELECT
    delivery_status,

    COUNT(*) AS reviewed_orders,

    COUNT(*) FILTER (
        WHERE review_score <= 2
    ) AS negative_reviews,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE review_score <= 2
        )
        / COUNT(*),
        2
    ) AS negative_review_rate_pct,

    COUNT(*) FILTER (
        WHERE review_score >= 4
    ) AS positive_reviews,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE review_score >= 4
        )
        / COUNT(*),
        2
    ) AS positive_review_rate_pct

FROM reviewed_orders

GROUP BY delivery_status

ORDER BY delivery_status;

-- 
-- 7. SINGLE-SELLER VS MULTI-SELLER ORDER PERFORMANCE
-- 

SELECT
    CASE
        WHEN is_multi_seller_order = TRUE
            THEN 'Multi-seller'

        ELSE 'Single-seller'
    END AS seller_structure,

    COUNT(*) AS order_count,

    ROUND(
        AVG(item_count),
        2
    ) AS average_item_count,

    ROUND(
        AVG(total_payment_value),
        2
    ) AS average_payment_value,

    ROUND(
        AVG(freight_value),
        2
    ) AS average_freight_value,

    ROUND(
        AVG(delivery_days),
        2
    ) AS average_delivery_days,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE delivery_delay_days > 0
        )
        / COUNT(*),
        2
    ) AS late_delivery_rate_pct,

    ROUND(
        AVG(review_score),
        2
    ) AS average_review_score

FROM fact_orders

WHERE
    order_status = 'delivered'
    AND delivery_delay_days IS NOT NULL
    AND item_count IS NOT NULL

GROUP BY
    is_multi_seller_order

ORDER BY
    is_multi_seller_order;

-- 
-- 8. SELLER STRUCTURE AMONG MULTI-ITEM ORDERS
-- 

SELECT
    CASE
        WHEN is_multi_seller_order = TRUE
            THEN 'Multi-seller'

        ELSE 'Single-seller'
    END AS seller_structure,

    COUNT(*) AS order_count,

    ROUND(
        AVG(item_count),
        2
    ) AS average_item_count,

    ROUND(
        AVG(unique_seller_count),
        2
    ) AS average_seller_count,

    ROUND(
        AVG(freight_value),
        2
    ) AS average_freight_value,

    ROUND(
        AVG(
            freight_value
            / NULLIF(item_count, 0)
        ),
        2
    ) AS average_freight_per_item,

    ROUND(
        AVG(delivery_days),
        2
    ) AS average_delivery_days,

    ROUND(
        AVG(carrier_to_customer_days),
        2
    ) AS average_carrier_to_customer_days,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE delivery_delay_days > 0
        )
        / COUNT(*),
        2
    ) AS late_delivery_rate_pct,

    ROUND(
        AVG(review_score),
        2
    ) AS average_review_score

FROM fact_orders

WHERE
    order_status = 'delivered'
    AND delivery_delay_days IS NOT NULL
    AND item_count >= 2

GROUP BY
    is_multi_seller_order

ORDER BY
    is_multi_seller_order;

-- 
-- 9. PERFORMANCE BY NUMBER OF SELLERS IN THE ORDER
-- 

SELECT
    unique_seller_count,

    COUNT(*) AS order_count,

    ROUND(
        AVG(item_count),
        2
    ) AS average_item_count,

    ROUND(
        AVG(freight_value),
        2
    ) AS average_freight_value,

    ROUND(
        AVG(delivery_days),
        2
    ) AS average_delivery_days,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE delivery_delay_days > 0
        )
        / COUNT(*),
        2
    ) AS late_delivery_rate_pct,

    ROUND(
        AVG(review_score),
        2
    ) AS average_review_score

FROM fact_orders

WHERE
    order_status = 'delivered'
    AND delivery_delay_days IS NOT NULL
    AND unique_seller_count IS NOT NULL

GROUP BY
    unique_seller_count

ORDER BY
    unique_seller_count;

-- 
-- 10. SELLER STRUCTURE AND REVIEWS AMONG NON-LATE
--     MULTI-ITEM ORDERS
-- 

SELECT
    CASE
        WHEN is_multi_seller_order = TRUE
            THEN 'Multi-seller'

        ELSE 'Single-seller'
    END AS seller_structure,

    COUNT(*) AS reviewed_orders,

    ROUND(
        AVG(review_score),
        2
    ) AS average_review_score,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE review_score <= 2
        )
        / COUNT(*),
        2
    ) AS negative_review_rate_pct,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE review_score >= 4
        )
        / COUNT(*),
        2
    ) AS positive_review_rate_pct,

    ROUND(
        AVG(delivery_days),
        2
    ) AS average_delivery_days,

    ROUND(
        AVG(freight_value),
        2
    ) AS average_freight_value

FROM fact_orders

WHERE
    order_status = 'delivered'

    AND item_count >= 2

    AND delivery_delay_days <= 0

    AND review_score IS NOT NULL

GROUP BY
    is_multi_seller_order

ORDER BY
    is_multi_seller_order;

-- 
-- 11. MULTI-ITEM REVIEW PERFORMANCE BY STATE
-- 

SELECT
    customer_state,

    CASE
        WHEN is_multi_seller_order = TRUE
            THEN 'Multi-seller'

        ELSE 'Single-seller'
    END AS seller_structure,

    COUNT(*) AS reviewed_orders,

    ROUND(
        AVG(review_score),
        2
    ) AS average_review_score,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE review_score <= 2
        )
        / COUNT(*),
        2
    ) AS negative_review_rate_pct

FROM fact_orders

WHERE
    order_status = 'delivered'

    AND item_count >= 2

    AND review_score IS NOT NULL

    AND customer_state IN (
        'SP',
        'RJ',
        'MG',
        'RS',
        'PR',
        'SC'
    )

GROUP BY
    customer_state,
    is_multi_seller_order

HAVING COUNT(*) >= 30

ORDER BY
    customer_state,
    is_multi_seller_order;