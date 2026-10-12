-- 
-- OLIST E-COMMERCE ANALYSIS
-- 01 - EXECUTIVE OVERVIEW
-- 
--
-- Primary commercial scope:
-- Delivered orders only.
--
-- total_payment_value represents recorded customer payment
-- value and should not be interpreted as profit.
--
-- fact_orders grain:
-- One row per order.
-- 

-- 
-- 1. ORDER STATUS OVERVIEW
-- 

SELECT
    order_status,
    COUNT(*) AS order_count,

    ROUND(
        100.0 * COUNT(*) / SUM(COUNT(*)) OVER (),
        2
    ) AS share_of_orders_pct

FROM fact_orders

GROUP BY order_status

ORDER BY order_count DESC;

-- 
-- 2. CORE DELIVERED-ORDER KPIs
-- 

SELECT
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
        AVG(item_sales_value),
        2
    ) AS average_item_sales_value,

    ROUND(
        AVG(freight_value),
        2
    ) AS average_freight_value,

    ROUND(
        AVG(delivery_days),
        2
    ) AS average_delivery_days,

    ROUND(
        AVG(review_score),
        2
    ) AS average_review_score

FROM fact_orders

WHERE order_status = 'delivered';

-- 
-- 3. DELIVERY PERFORMANCE
-- 

SELECT
    COUNT(*) AS classifiable_deliveries,

    COUNT(*) FILTER (
        WHERE delivery_delay_days < 0
    ) AS early_deliveries,

    COUNT(*) FILTER (
        WHERE delivery_delay_days = 0
    ) AS on_promised_date_deliveries,

    COUNT(*) FILTER (
        WHERE delivery_delay_days > 0
    ) AS late_deliveries,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE delivery_delay_days > 0
        )
        / COUNT(*),
        2
    ) AS late_delivery_rate_pct,

    ROUND(
        AVG(delivery_days),
        2
    ) AS average_delivery_days,

    ROUND(
        AVG(delivery_delay_days),
        2
    ) AS average_days_vs_promise

FROM fact_orders

WHERE
    order_status = 'delivered'
    AND delivery_delay_days IS NOT NULL;

-- 
-- 4. CUSTOMER REVIEW OVERVIEW
-- 

SELECT
    COUNT(review_score)
        AS reviewed_delivered_orders,

    ROUND(
        AVG(review_score),
        2
    ) AS average_review_score,

    COUNT(*) FILTER (
        WHERE review_score >= 4
    ) AS positive_reviews,

    COUNT(*) FILTER (
        WHERE review_score <= 2
    ) AS negative_reviews,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE review_score >= 4
        )
        / COUNT(review_score),
        2
    ) AS positive_review_rate_pct,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE review_score <= 2
        )
        / COUNT(review_score),
        2
    ) AS negative_review_rate_pct

FROM fact_orders

WHERE
    order_status = 'delivered'
    AND review_score IS NOT NULL;


-- 
-- 5. CUSTOMER REPEAT BEHAVIOR
-- 

SELECT
    COUNT(*) AS total_customers,

    COUNT(*) FILTER (
        WHERE is_repeat_customer = TRUE
    ) AS repeat_customers,

    COUNT(*) FILTER (
        WHERE is_repeat_customer = FALSE
    ) AS one_time_customers,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE is_repeat_customer = TRUE
        )
        / COUNT(*),
        2
    ) AS repeat_customer_rate_pct,

    MAX(lifetime_order_count)
        AS maximum_orders_by_customer

FROM dim_customer;

-- 
-- 6. TOP CUSTOMER STATES BY DELIVERED PAYMENT VALUE
-- 

SELECT
    customer_state,

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
    ) AS average_payment_value

FROM fact_orders

WHERE order_status = 'delivered'

GROUP BY customer_state

ORDER BY total_payment_value DESC

LIMIT 10;

-- 
-- 7. TOP PRODUCT CATEGORIES BY ITEM SALES
-- 

SELECT
    product_category_name_english
        AS category,

    COUNT(*) AS item_rows,

    COUNT(DISTINCT order_id)
        AS order_count,

    ROUND(
        SUM(price),
        2
    ) AS item_sales_value,

    ROUND(
        AVG(price),
        2
    ) AS average_item_price

FROM fact_order_items

WHERE order_status = 'delivered'

GROUP BY product_category_name_english

ORDER BY item_sales_value DESC

LIMIT 10;

-- 
-- 8. MONTHLY DELIVERED-ORDER TREND
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
    ) AS average_payment_value

FROM fact_orders

WHERE order_status = 'delivered'

GROUP BY
    DATE_TRUNC(
        'month',
        order_purchase_timestamp
    )

ORDER BY purchase_month;