-- 
-- OLIST E-COMMERCE ANALYSIS
-- 08 - GEOGRAPHIC ANALYSIS
-- 
--
-- Customer geography reflects the location associated with
-- each order.
--
-- Seller geography reflects seller location.
--
-- Commercial customer-side metrics use fact_orders.
-- Seller-side item-sales metrics use fact_order_items.
--
-- Single-seller orders are used where a unique seller origin
-- is required for order-level delivery comparisons.
-- 

-- 
-- 1. CUSTOMER DEMAND BY STATE
-- 

WITH state_demand AS (

    SELECT
        customer_state,

        COUNT(*) AS delivered_orders,

        COUNT(
            DISTINCT customer_unique_id
        ) AS unique_customers,

        SUM(
            total_payment_value
        ) AS total_payment_value,

        AVG(
            total_payment_value
        ) AS average_payment_value

    FROM fact_orders

    WHERE order_status = 'delivered'

    GROUP BY customer_state
)

SELECT
    customer_state,
    delivered_orders,
    unique_customers,

    ROUND(
        total_payment_value,
        2
    ) AS total_payment_value,

    ROUND(
        100.0
        * total_payment_value
        / SUM(total_payment_value) OVER (),
        2
    ) AS payment_value_share_pct,

    ROUND(
        average_payment_value,
        2
    ) AS average_payment_value

FROM state_demand

ORDER BY
    total_payment_value DESC;

-- 
-- 2. SELLER SUPPLY BY STATE
-- 

WITH state_supply AS (

    SELECT
        seller_state,

        COUNT(
            DISTINCT seller_id
        ) AS active_sellers,

        COUNT(
            DISTINCT order_id
        ) AS orders_served,

        SUM(price)
            AS item_sales_value

    FROM fact_order_items

    WHERE order_status = 'delivered'

    GROUP BY seller_state
)

SELECT
    seller_state,
    active_sellers,
    orders_served,

    ROUND(
        item_sales_value,
        2
    ) AS item_sales_value,

    ROUND(
        100.0
        * item_sales_value
        / SUM(item_sales_value) OVER (),
        2
    ) AS item_sales_share_pct

FROM state_supply

ORDER BY
    item_sales_value DESC;

-- 
-- 3. SAME-STATE VS INTERSTATE FULFILLMENT
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
        o.order_id,

        o.customer_state,

        s.seller_state,

        CASE
            WHEN o.customer_state = s.seller_state
                THEN 'Same state'

            ELSE 'Interstate'
        END AS fulfillment_type,

        o.delivery_days,
        o.delivery_delay_days,
        o.freight_value,
        o.review_score

    FROM fact_orders AS o

    INNER JOIN single_seller_orders AS s
        ON o.order_id = s.order_id

    WHERE
        o.delivery_delay_days IS NOT NULL
)

SELECT
    fulfillment_type,

    COUNT(*) AS order_count,

    ROUND(
        100.0
        * COUNT(*)
        / SUM(COUNT(*)) OVER (),
        2
    ) AS order_share_pct,

    ROUND(
        AVG(delivery_days),
        2
    ) AS average_delivery_days,

    ROUND(
        MEDIAN(delivery_days),
        2
    ) AS median_delivery_days,

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
    ) AS late_delivery_rate_pct,

    ROUND(
        AVG(review_score),
        2
    ) AS average_review_score

FROM classified_orders

GROUP BY fulfillment_type

ORDER BY order_count DESC;

-- 
-- 4. LARGEST INTERSTATE FULFILLMENT ROUTES
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

routes AS (

    SELECT
        s.seller_state,
        o.customer_state,

        COUNT(*) AS order_count,

        AVG(
            o.delivery_days
        ) AS average_delivery_days,

        AVG(
            o.freight_value
        ) AS average_freight_value,

        100.0
        * COUNT(*) FILTER (
            WHERE o.delivery_delay_days > 0
        )
        / COUNT(*)
            AS late_delivery_rate_pct

    FROM single_seller_orders AS s

    INNER JOIN fact_orders AS o
        ON s.order_id = o.order_id

    WHERE
        s.seller_state <> o.customer_state
        AND o.delivery_delay_days IS NOT NULL

    GROUP BY
        s.seller_state,
        o.customer_state
)

SELECT
    seller_state,
    customer_state,
    order_count,

    ROUND(
        average_delivery_days,
        2
    ) AS average_delivery_days,

    ROUND(
        average_freight_value,
        2
    ) AS average_freight_value,

    ROUND(
        late_delivery_rate_pct,
        2
    ) AS late_delivery_rate_pct

FROM routes

WHERE order_count >= 100

ORDER BY
    order_count DESC

LIMIT 20;

