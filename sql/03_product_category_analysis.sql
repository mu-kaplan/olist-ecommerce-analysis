-- 
-- OLIST E-COMMERCE ANALYSIS
-- 03 - PRODUCT AND CATEGORY PERFORMANCE
-- 
--
-- Primary grain:
-- One row per order item.
--
-- Main commercial scope:
-- Items belonging to delivered orders.
--
-- price = item sales value before freight.
-- freight_value is analyzed separately.
--
-- Unknown categories are retained rather than silently removed.
-- 

-- 
-- 1. CATEGORY PERFORMANCE
-- 

WITH category_performance AS (

    SELECT
        product_category_name_english
            AS category,

        COUNT(*) AS item_count,

        COUNT(DISTINCT order_id)
            AS order_count,

        COUNT(DISTINCT product_id)
            AS unique_products,

        COUNT(DISTINCT seller_id)
            AS unique_sellers,

        SUM(price)
            AS item_sales_value,

        SUM(freight_value)
            AS freight_value,

        AVG(price)
            AS average_item_price

    FROM fact_order_items

    WHERE order_status = 'delivered'

    GROUP BY
        product_category_name_english
)

SELECT
    category,
    item_count,
    order_count,
    unique_products,
    unique_sellers,

    ROUND(
        item_sales_value,
        2
    ) AS item_sales_value,

    ROUND(
        100.0
        * item_sales_value
        / SUM(item_sales_value) OVER (),
        2
    ) AS item_sales_share_pct,

    ROUND(
        freight_value,
        2
    ) AS freight_value,

    ROUND(
        average_item_price,
        2
    ) AS average_item_price

FROM category_performance

ORDER BY
    item_sales_value DESC;

-- 
-- 2. CATEGORY RANKINGS
-- 

WITH category_performance AS (

    SELECT
        product_category_name_english
            AS category,

        COUNT(*) AS item_count,

        COUNT(DISTINCT order_id)
            AS order_count,

        SUM(price)
            AS item_sales_value,

        AVG(price)
            AS average_item_price

    FROM fact_order_items

    WHERE order_status = 'delivered'

    GROUP BY
        product_category_name_english
)

SELECT
    category,

    ROUND(
        item_sales_value,
        2
    ) AS item_sales_value,

    RANK() OVER (
        ORDER BY item_sales_value DESC
    ) AS sales_rank,

    item_count,

    RANK() OVER (
        ORDER BY item_count DESC
    ) AS item_volume_rank,

    order_count,

    RANK() OVER (
        ORDER BY order_count DESC
    ) AS order_count_rank,

    ROUND(
        average_item_price,
        2
    ) AS average_item_price,

    RANK() OVER (
        ORDER BY average_item_price DESC
    ) AS average_price_rank

FROM category_performance

ORDER BY
    sales_rank;

-- 
-- 3. CATEGORY SALES CONCENTRATION
-- 

WITH category_sales AS (

    SELECT
        product_category_name_english
            AS category,

        SUM(price)
            AS item_sales_value

    FROM fact_order_items

    WHERE order_status = 'delivered'

    GROUP BY
        product_category_name_english
),

ranked_categories AS (

    SELECT
        category,
        item_sales_value,

        ROW_NUMBER() OVER (
            ORDER BY item_sales_value DESC
        ) AS sales_rank,

        SUM(item_sales_value) OVER ()
            AS total_item_sales_value

    FROM category_sales
),

with_cumulative_share AS (

    SELECT
        category,
        sales_rank,
        item_sales_value,

        100.0
        * item_sales_value
        / total_item_sales_value
            AS item_sales_share_pct,

        100.0
        * SUM(item_sales_value) OVER (
            ORDER BY sales_rank

            ROWS BETWEEN
                UNBOUNDED PRECEDING
                AND CURRENT ROW
        )
        / total_item_sales_value
            AS cumulative_sales_share_pct

    FROM ranked_categories
)

SELECT
    sales_rank,
    category,

    ROUND(
        item_sales_value,
        2
    ) AS item_sales_value,

    ROUND(
        item_sales_share_pct,
        2
    ) AS item_sales_share_pct,

    ROUND(
        cumulative_sales_share_pct,
        2
    ) AS cumulative_sales_share_pct

FROM with_cumulative_share

ORDER BY sales_rank
LIMIT 20;

-- 
-- 4. TOP-N CATEGORY SALES CONCENTRATION
-- 

WITH category_sales AS (

    SELECT
        product_category_name_english
            AS category,

        SUM(price)
            AS item_sales_value

    FROM fact_order_items

    WHERE order_status = 'delivered'

    GROUP BY
        product_category_name_english
),

ranked_categories AS (

    SELECT
        category,
        item_sales_value,

        ROW_NUMBER() OVER (
            ORDER BY item_sales_value DESC
        ) AS sales_rank,

        SUM(item_sales_value) OVER ()
            AS total_item_sales_value

    FROM category_sales
)

SELECT
    ROUND(
        100.0
        * SUM(
            CASE
                WHEN sales_rank <= 5
                    THEN item_sales_value
                ELSE 0
            END
        )
        / MAX(total_item_sales_value),
        2
    ) AS top_5_share_pct,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN sales_rank <= 10
                    THEN item_sales_value
                ELSE 0
            END
        )
        / MAX(total_item_sales_value),
        2
    ) AS top_10_share_pct,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN sales_rank <= 20
                    THEN item_sales_value
                ELSE 0
            END
        )
        / MAX(total_item_sales_value),
        2
    ) AS top_20_share_pct

FROM ranked_categories;

-- 
-- 5. CATEGORIES REQUIRED TO REACH 80% OF ITEM SALES
-- 

WITH category_sales AS (

    SELECT
        product_category_name_english
            AS category,

        SUM(price)
            AS item_sales_value

    FROM fact_order_items

    WHERE order_status = 'delivered'

    GROUP BY
        product_category_name_english
),

ranked_categories AS (

    SELECT
        category,
        item_sales_value,

        ROW_NUMBER() OVER (
            ORDER BY item_sales_value DESC
        ) AS sales_rank,

        SUM(item_sales_value) OVER ()
            AS total_item_sales_value

    FROM category_sales
),

cumulative_sales AS (

    SELECT
        category,
        sales_rank,
        item_sales_value,

        100.0
        * SUM(item_sales_value) OVER (
            ORDER BY sales_rank

            ROWS BETWEEN
                UNBOUNDED PRECEDING
                AND CURRENT ROW
        )
        / total_item_sales_value
            AS cumulative_sales_share_pct

    FROM ranked_categories
)

SELECT
    sales_rank
        AS categories_needed,

    category
        AS threshold_category,

    ROUND(
        cumulative_sales_share_pct,
        2
    ) AS cumulative_sales_share_pct

FROM cumulative_sales

WHERE cumulative_sales_share_pct >= 80

ORDER BY sales_rank

LIMIT 1;

-- 
-- 6. TOP PRODUCTS BY ITEM SALES VALUE
-- 

WITH product_performance AS (

    SELECT
        product_id,

        product_category_name_english
            AS category,

        COUNT(*) AS item_count,

        COUNT(DISTINCT order_id)
            AS order_count,

        COUNT(DISTINCT seller_id)
            AS seller_count,

        SUM(price)
            AS item_sales_value,

        AVG(price)
            AS average_item_price

    FROM fact_order_items

    WHERE order_status = 'delivered'

    GROUP BY
        product_id,
        product_category_name_english
)

SELECT
    product_id,
    category,
    item_count,
    order_count,
    seller_count,

    ROUND(
        item_sales_value,
        2
    ) AS item_sales_value,

    ROUND(
        average_item_price,
        2
    ) AS average_item_price

FROM product_performance

ORDER BY
    item_sales_value DESC

LIMIT 20;

-- 
-- 7. PRODUCT SALES VS VOLUME RANKING
-- 

WITH product_performance AS (

    SELECT
        product_id,

        product_category_name_english
            AS category,

        COUNT(*) AS item_count,

        COUNT(DISTINCT order_id)
            AS order_count,

        SUM(price)
            AS item_sales_value,

        AVG(price)
            AS average_item_price

    FROM fact_order_items

    WHERE order_status = 'delivered'

    GROUP BY
        product_id,
        product_category_name_english
),

ranked_products AS (

    SELECT
        product_id,
        category,
        item_count,
        order_count,
        item_sales_value,
        average_item_price,

        RANK() OVER (
            ORDER BY item_sales_value DESC
        ) AS sales_rank,

        RANK() OVER (
            ORDER BY item_count DESC
        ) AS volume_rank,

        RANK() OVER (
            ORDER BY average_item_price DESC
        ) AS price_rank

    FROM product_performance
)

SELECT
    product_id,
    category,

    ROUND(
        item_sales_value,
        2
    ) AS item_sales_value,

    sales_rank,

    item_count,
    volume_rank,

    ROUND(
        average_item_price,
        2
    ) AS average_item_price,

    price_rank

FROM ranked_products

ORDER BY sales_rank

LIMIT 20;

-- 
-- 8. TOP 3 PRODUCTS WITHIN EACH TOP-10 CATEGORY
-- 

WITH category_sales AS (

    SELECT
        product_category_name_english
            AS category,

        SUM(price)
            AS category_sales_value

    FROM fact_order_items

    WHERE order_status = 'delivered'

    GROUP BY
        product_category_name_english
),

top_categories AS (

    SELECT
        category,

        ROW_NUMBER() OVER (
            ORDER BY category_sales_value DESC
        ) AS category_rank

    FROM category_sales
),

product_sales AS (

    SELECT
        product_category_name_english
            AS category,

        product_id,

        COUNT(*) AS item_count,

        COUNT(DISTINCT order_id)
            AS order_count,

        SUM(price)
            AS item_sales_value

    FROM fact_order_items

    WHERE order_status = 'delivered'

    GROUP BY
        product_category_name_english,
        product_id
),

ranked_products AS (

    SELECT
        p.category,
        c.category_rank,
        p.product_id,
        p.item_count,
        p.order_count,
        p.item_sales_value,

        ROW_NUMBER() OVER (
            PARTITION BY p.category

            ORDER BY
                p.item_sales_value DESC,
                p.product_id
        ) AS product_rank_in_category

    FROM product_sales AS p

    INNER JOIN top_categories AS c
        ON p.category = c.category

    WHERE c.category_rank <= 10
)

SELECT
    category_rank,
    category,
    product_rank_in_category,
    product_id,
    item_count,
    order_count,

    ROUND(
        item_sales_value,
        2
    ) AS item_sales_value

FROM ranked_products

WHERE product_rank_in_category <= 3

ORDER BY
    category_rank,
    product_rank_in_category;

-- 
-- 9. TOP-PRODUCT CONCENTRATION WITHIN MAJOR CATEGORIES
-- 

WITH category_sales AS (

    SELECT
        product_category_name_english
            AS category,

        SUM(price)
            AS category_sales_value

    FROM fact_order_items

    WHERE order_status = 'delivered'

    GROUP BY
        product_category_name_english
),

ranked_categories AS (

    SELECT
        category,
        category_sales_value,

        ROW_NUMBER() OVER (
            ORDER BY category_sales_value DESC
        ) AS category_rank

    FROM category_sales
),

product_sales AS (

    SELECT
        product_category_name_english
            AS category,

        product_id,

        SUM(price)
            AS product_sales_value

    FROM fact_order_items

    WHERE order_status = 'delivered'

    GROUP BY
        product_category_name_english,
        product_id
),

ranked_products AS (

    SELECT
        category,
        product_id,
        product_sales_value,

        ROW_NUMBER() OVER (
            PARTITION BY category
            ORDER BY
                product_sales_value DESC,
                product_id
        ) AS product_rank

    FROM product_sales
),

category_concentration AS (

    SELECT
        c.category_rank,
        c.category,
        c.category_sales_value,

        MAX(
            CASE
                WHEN p.product_rank = 1
                    THEN p.product_sales_value
            END
        ) AS top_product_sales,

        SUM(
            CASE
                WHEN p.product_rank <= 3
                    THEN p.product_sales_value
                ELSE 0
            END
        ) AS top_3_product_sales

    FROM ranked_categories AS c

    INNER JOIN ranked_products AS p
        ON c.category = p.category

    WHERE c.category_rank <= 10

    GROUP BY
        c.category_rank,
        c.category,
        c.category_sales_value
)

SELECT
    category_rank,
    category,

    ROUND(
        category_sales_value,
        2
    ) AS category_sales_value,

    ROUND(
        top_product_sales,
        2
    ) AS top_product_sales,

    ROUND(
        100.0
        * top_product_sales
        / category_sales_value,
        2
    ) AS top_product_share_pct,

    ROUND(
        top_3_product_sales,
        2
    ) AS top_3_product_sales,

    ROUND(
        100.0
        * top_3_product_sales
        / category_sales_value,
        2
    ) AS top_3_product_share_pct

FROM category_concentration

ORDER BY category_rank;

