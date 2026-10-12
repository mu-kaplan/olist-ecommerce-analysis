-- 
-- OLIST E-COMMERCE ANALYSIS
-- 06 - SELLER ANALYSIS
-- 
--
-- Commercial seller metrics use fact_order_items because sales
-- value belongs to item grain.
--
-- Review and delivery metrics require additional care because
-- those outcomes belong to the order, not individual item rows.
-- 

-- 
-- 1. SELLER COMMERCIAL PERFORMANCE
-- 

WITH seller_performance AS (

    SELECT
        seller_id,
        seller_state,

        COUNT(*) AS item_count,

        COUNT(DISTINCT order_id)
            AS order_count,

        COUNT(DISTINCT product_id)
            AS unique_products,

        SUM(price)
            AS item_sales_value,

        SUM(freight_value)
            AS freight_value,

        AVG(price)
            AS average_item_price

    FROM fact_order_items

    WHERE order_status = 'delivered'

    GROUP BY
        seller_id,
        seller_state
)

SELECT
    seller_id,
    seller_state,
    item_count,
    order_count,
    unique_products,

    ROUND(
        item_sales_value,
        2
    ) AS item_sales_value,

    ROUND(
        freight_value,
        2
    ) AS freight_value,

    ROUND(
        average_item_price,
        2
    ) AS average_item_price

FROM seller_performance

ORDER BY item_sales_value DESC

LIMIT 20;

-- 
-- 2. SELLER SALES CONCENTRATION
-- 

WITH seller_sales AS (

    SELECT
        seller_id,

        SUM(price)
            AS item_sales_value

    FROM fact_order_items

    WHERE order_status = 'delivered'

    GROUP BY seller_id
),

ranked_sellers AS (

    SELECT
        seller_id,
        item_sales_value,

        ROW_NUMBER() OVER (
            ORDER BY
                item_sales_value DESC,
                seller_id
        ) AS seller_rank,

        COUNT(*) OVER ()
            AS total_sellers,

        SUM(item_sales_value) OVER ()
            AS total_item_sales

    FROM seller_sales
)

SELECT
    MAX(total_sellers)
        AS active_sellers,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN seller_rank <= 10
                    THEN item_sales_value
                ELSE 0
            END
        )
        / MAX(total_item_sales),
        2
    ) AS top_10_seller_share_pct,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN seller_rank <= 50
                    THEN item_sales_value
                ELSE 0
            END
        )
        / MAX(total_item_sales),
        2
    ) AS top_50_seller_share_pct,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN seller_rank <= 100
                    THEN item_sales_value
                ELSE 0
            END
        )
        / MAX(total_item_sales),
        2
    ) AS top_100_seller_share_pct

FROM ranked_sellers;

-- 
-- 3. SELLERS REQUIRED TO REACH 80% OF ITEM SALES
-- 

WITH seller_sales AS (

    SELECT
        seller_id,

        SUM(price)
            AS item_sales_value

    FROM fact_order_items

    WHERE order_status = 'delivered'

    GROUP BY seller_id
),

ranked_sellers AS (

    SELECT
        seller_id,
        item_sales_value,

        ROW_NUMBER() OVER (
            ORDER BY
                item_sales_value DESC,
                seller_id
        ) AS seller_rank,

        SUM(item_sales_value) OVER ()
            AS total_item_sales

    FROM seller_sales
),

cumulative_sales AS (

    SELECT
        seller_id,
        seller_rank,
        item_sales_value,

        100.0
        * SUM(item_sales_value) OVER (
            ORDER BY seller_rank

            ROWS BETWEEN
                UNBOUNDED PRECEDING
                AND CURRENT ROW
        )
        / total_item_sales
            AS cumulative_sales_share_pct

    FROM ranked_sellers
)

SELECT
    seller_rank
        AS sellers_needed,

    seller_id
        AS threshold_seller,

    ROUND(
        cumulative_sales_share_pct,
        2
    ) AS cumulative_sales_share_pct

FROM cumulative_sales

WHERE cumulative_sales_share_pct >= 80

ORDER BY seller_rank

LIMIT 1;

-- 
-- 4. SELLER OPERATIONAL PERFORMANCE
--    SINGLE-SELLER ORDERS ONLY
-- 

WITH seller_orders AS (

    SELECT DISTINCT
        oi.order_id,
        oi.seller_id,
        oi.seller_state

    FROM fact_order_items AS oi

    INNER JOIN fact_orders AS o
        ON oi.order_id = o.order_id

    WHERE
        o.order_status = 'delivered'
        AND o.unique_seller_count = 1
),

seller_performance AS (

    SELECT
        s.seller_id,
        s.seller_state,

        COUNT(*) AS delivered_orders,

        AVG(o.delivery_days)
            AS average_delivery_days,

        AVG(o.delivery_delay_days)
            AS average_days_vs_promise,

        AVG(o.review_score)
            AS average_review_score,

        COUNT(*) FILTER (
            WHERE o.delivery_delay_days > 0
        ) AS late_orders,

        COUNT(*) FILTER (
            WHERE o.review_score <= 2
        ) AS negative_reviews

    FROM seller_orders AS s

    INNER JOIN fact_orders AS o
        ON s.order_id = o.order_id

    GROUP BY
        s.seller_id,
        s.seller_state
)

SELECT
    seller_id,
    seller_state,
    delivered_orders,

    ROUND(
        average_delivery_days,
        2
    ) AS average_delivery_days,

    ROUND(
        average_days_vs_promise,
        2
    ) AS average_days_vs_promise,

    ROUND(
        100.0
        * late_orders
        / delivered_orders,
        2
    ) AS late_delivery_rate_pct,

    ROUND(
        average_review_score,
        2
    ) AS average_review_score,

    ROUND(
        100.0
        * negative_reviews
        / delivered_orders,
        2
    ) AS negative_review_rate_pct

FROM seller_performance

WHERE delivered_orders >= 50

ORDER BY
    negative_review_rate_pct DESC;

-- 
-- 5. OPERATIONAL QUALITY AMONG LARGE SELLERS
-- 

WITH seller_orders AS (

    SELECT DISTINCT
        oi.order_id,
        oi.seller_id,
        oi.seller_state

    FROM fact_order_items AS oi

    INNER JOIN fact_orders AS o
        ON oi.order_id = o.order_id

    WHERE
        o.order_status = 'delivered'
        AND o.unique_seller_count = 1
),

seller_performance AS (

    SELECT
        s.seller_id,
        s.seller_state,

        COUNT(*) AS delivered_orders,

        AVG(o.delivery_days)
            AS average_delivery_days,

        COUNT(*) FILTER (
            WHERE o.delivery_delay_days > 0
        ) AS late_orders,

        AVG(o.review_score)
            AS average_review_score,

        COUNT(*) FILTER (
            WHERE o.review_score <= 2
        ) AS negative_reviews

    FROM seller_orders AS s

    INNER JOIN fact_orders AS o
        ON s.order_id = o.order_id

    WHERE
        o.delivery_delay_days IS NOT NULL
        AND o.review_score IS NOT NULL

    GROUP BY
        s.seller_id,
        s.seller_state
)

SELECT
    seller_id,
    seller_state,
    delivered_orders,

    ROUND(
        average_delivery_days,
        2
    ) AS average_delivery_days,

    ROUND(
        100.0
        * late_orders
        / delivered_orders,
        2
    ) AS late_delivery_rate_pct,

    ROUND(
        average_review_score,
        2
    ) AS average_review_score,

    ROUND(
        100.0
        * negative_reviews
        / delivered_orders,
        2
    ) AS negative_review_rate_pct

FROM seller_performance

WHERE delivered_orders >= 200

ORDER BY
    negative_review_rate_pct DESC;

-- 
-- 6. SELLER LATE RATE VS NEGATIVE REVIEW RATE
-- 

WITH seller_orders AS (

    SELECT DISTINCT
        oi.order_id,
        oi.seller_id

    FROM fact_order_items AS oi

    INNER JOIN fact_orders AS o
        ON oi.order_id = o.order_id

    WHERE
        o.order_status = 'delivered'
        AND o.unique_seller_count = 1
),

seller_performance AS (

    SELECT
        s.seller_id,

        COUNT(*) AS delivered_orders,

        100.0
        * COUNT(*) FILTER (
            WHERE o.delivery_delay_days > 0
        )
        / COUNT(*)
            AS late_delivery_rate_pct,

        100.0
        * COUNT(*) FILTER (
            WHERE o.review_score <= 2
        )
        / COUNT(*)
            AS negative_review_rate_pct,

        AVG(o.review_score)
            AS average_review_score

    FROM seller_orders AS s

    INNER JOIN fact_orders AS o
        ON s.order_id = o.order_id

    WHERE
        o.delivery_delay_days IS NOT NULL
        AND o.review_score IS NOT NULL

    GROUP BY
        s.seller_id
)

SELECT
    COUNT(*) AS sellers_analyzed,

    ROUND(
        CORR(
            late_delivery_rate_pct,
            negative_review_rate_pct
        ),
        3
    ) AS correlation_late_vs_negative_reviews,

    ROUND(
        CORR(
            late_delivery_rate_pct,
            average_review_score
        ),
        3
    ) AS correlation_late_vs_review_score

FROM seller_performance

WHERE delivered_orders >= 50;

--
-- 7. LARGE-SELLER COMMERCIAL + OPERATIONAL SCORECARD
-- 

WITH seller_sales AS (

    SELECT
        seller_id,
        seller_state,

        COUNT(DISTINCT order_id)
            AS delivered_order_count,

        SUM(price)
            AS item_sales_value

    FROM fact_order_items

    WHERE order_status = 'delivered'

    GROUP BY
        seller_id,
        seller_state
),

single_seller_orders AS (

    SELECT DISTINCT
        oi.order_id,
        oi.seller_id

    FROM fact_order_items AS oi

    INNER JOIN fact_orders AS o
        ON oi.order_id = o.order_id

    WHERE
        o.order_status = 'delivered'
        AND o.unique_seller_count = 1
        AND o.delivery_delay_days IS NOT NULL
        AND o.review_score IS NOT NULL
),

seller_quality AS (

    SELECT
        s.seller_id,

        COUNT(*) AS quality_order_count,

        AVG(o.delivery_days)
            AS average_delivery_days,

        100.0
        * COUNT(*) FILTER (
            WHERE o.delivery_delay_days > 0
        )
        / COUNT(*)
            AS late_delivery_rate_pct,

        AVG(o.review_score)
            AS average_review_score,

        100.0
        * COUNT(*) FILTER (
            WHERE o.review_score <= 2
        )
        / COUNT(*)
            AS negative_review_rate_pct

    FROM single_seller_orders AS s

    INNER JOIN fact_orders AS o
        ON s.order_id = o.order_id

    GROUP BY
        s.seller_id
)

SELECT
    s.seller_id,
    s.seller_state,

    s.delivered_order_count,

    ROUND(
        s.item_sales_value,
        2
    ) AS item_sales_value,

    q.quality_order_count,

    ROUND(
        q.average_delivery_days,
        2
    ) AS average_delivery_days,

    ROUND(
        q.late_delivery_rate_pct,
        2
    ) AS late_delivery_rate_pct,

    ROUND(
        q.average_review_score,
        2
    ) AS average_review_score,

    ROUND(
        q.negative_review_rate_pct,
        2
    ) AS negative_review_rate_pct

FROM seller_sales AS s

INNER JOIN seller_quality AS q
    ON s.seller_id = q.seller_id

WHERE q.quality_order_count >= 200

ORDER BY
    s.item_sales_value DESC;

-- 
-- 8. HIGH-VALUE SELLERS WITH ABOVE-MEDIAN NEGATIVE REVIEW RATE
-- 

WITH seller_sales AS (

    SELECT
        seller_id,
        seller_state,

        SUM(price)
            AS item_sales_value

    FROM fact_order_items

    WHERE order_status = 'delivered'

    GROUP BY
        seller_id,
        seller_state
),

single_seller_orders AS (

    SELECT DISTINCT
        oi.order_id,
        oi.seller_id

    FROM fact_order_items AS oi

    INNER JOIN fact_orders AS o
        ON oi.order_id = o.order_id

    WHERE
        o.order_status = 'delivered'
        AND o.unique_seller_count = 1
        AND o.delivery_delay_days IS NOT NULL
        AND o.review_score IS NOT NULL
),

seller_quality AS (

    SELECT
        s.seller_id,

        COUNT(*) AS quality_order_count,

        100.0
        * COUNT(*) FILTER (
            WHERE o.delivery_delay_days > 0
        )
        / COUNT(*)
            AS late_delivery_rate_pct,

        AVG(o.review_score)
            AS average_review_score,

        100.0
        * COUNT(*) FILTER (
            WHERE o.review_score <= 2
        )
        / COUNT(*)
            AS negative_review_rate_pct

    FROM single_seller_orders AS s

    INNER JOIN fact_orders AS o
        ON s.order_id = o.order_id

    GROUP BY
        s.seller_id
),

large_sellers AS (

    SELECT
        s.seller_id,
        s.seller_state,
        s.item_sales_value,

        q.quality_order_count,
        q.late_delivery_rate_pct,
        q.average_review_score,
        q.negative_review_rate_pct

    FROM seller_sales AS s

    INNER JOIN seller_quality AS q
        ON s.seller_id = q.seller_id

    WHERE q.quality_order_count >= 200
),

benchmark AS (

    SELECT
        MEDIAN(negative_review_rate_pct)
            AS median_negative_review_rate

    FROM large_sellers
)

SELECT
    l.seller_id,
    l.seller_state,

    ROUND(
        l.item_sales_value,
        2
    ) AS item_sales_value,

    l.quality_order_count,

    ROUND(
        l.late_delivery_rate_pct,
        2
    ) AS late_delivery_rate_pct,

    ROUND(
        l.average_review_score,
        2
    ) AS average_review_score,

    ROUND(
        l.negative_review_rate_pct,
        2
    ) AS negative_review_rate_pct,

    ROUND(
        b.median_negative_review_rate,
        2
    ) AS large_seller_median_negative_rate

FROM large_sellers AS l

CROSS JOIN benchmark AS b

WHERE
    l.negative_review_rate_pct
        > b.median_negative_review_rate

ORDER BY
    l.item_sales_value DESC

LIMIT 20;

