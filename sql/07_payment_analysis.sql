-- 
-- OLIST E-COMMERCE ANALYSIS
-- 07 - PAYMENT ANALYSIS
-- 
--
-- Order-level payment analysis uses payments_order_level logic
-- already incorporated into fact_orders.
--
-- Raw payment-record analysis uses payments_clean where needed.
--
-- total_payment_value is customer payment value and should not
-- be interpreted as profit.
-- 

-- 
-- 1. PRIMARY PAYMENT METHOD MIX
-- 

SELECT
    primary_payment_type,

    COUNT(*) AS order_count,

    ROUND(
        100.0
        * COUNT(*)
        / SUM(COUNT(*)) OVER (),
        2
    ) AS order_share_pct,

    ROUND(
        SUM(total_payment_value),
        2
    ) AS total_payment_value,

    ROUND(
        100.0
        * SUM(total_payment_value)
        / SUM(SUM(total_payment_value)) OVER (),
        2
    ) AS payment_value_share_pct,

    ROUND(
        AVG(total_payment_value),
        2
    ) AS average_payment_value

FROM fact_orders

WHERE
    order_status = 'delivered'
    AND primary_payment_type IS NOT NULL

GROUP BY
    primary_payment_type

ORDER BY
    order_count DESC;

-- 
-- 2. ORDER VALUE BY PRIMARY PAYMENT TYPE
-- 

SELECT
    primary_payment_type,

    COUNT(*) AS order_count,

    ROUND(
        AVG(total_payment_value),
        2
    ) AS average_payment_value,

    ROUND(
        MEDIAN(total_payment_value),
        2
    ) AS median_payment_value,

    ROUND(
        MIN(total_payment_value),
        2
    ) AS minimum_payment_value,

    ROUND(
        MAX(total_payment_value),
        2
    ) AS maximum_payment_value

FROM fact_orders

WHERE
    order_status = 'delivered'
    AND primary_payment_type IS NOT NULL

GROUP BY
    primary_payment_type

ORDER BY
    average_payment_value DESC;

-- 
-- 3. CREDIT-CARD INSTALLMENT DISTRIBUTION
-- 

SELECT
    payment_installments_clean
        AS installments,

    COUNT(*) AS payment_records,

    ROUND(
        100.0
        * COUNT(*)
        / SUM(COUNT(*)) OVER (),
        2
    ) AS payment_record_share_pct,

    ROUND(
        AVG(payment_value),
        2
    ) AS average_payment_value

FROM payments_clean

WHERE
    payment_type_clean = 'credit_card'
    AND payment_installments_clean IS NOT NULL

GROUP BY
    payment_installments_clean

ORDER BY
    installments;

-- 
-- 4. CREDIT-CARD INSTALLMENTS VS PAYMENT VALUE
-- 

SELECT
    payment_installments_clean
        AS installments,

    COUNT(*) AS payment_records,

    ROUND(
        AVG(payment_value),
        2
    ) AS average_payment_value,

    ROUND(
        MEDIAN(payment_value),
        2
    ) AS median_payment_value

FROM payments_clean

WHERE
    payment_type_clean = 'credit_card'
    AND payment_installments_clean IS NOT NULL

GROUP BY
    payment_installments_clean

HAVING COUNT(*) >= 50

ORDER BY
    installments;

-- 
-- 5. SINGLE VS MULTIPLE PAYMENT RECORDS
-- 

SELECT
    CASE
        WHEN payment_record_count = 1
            THEN 'Single payment record'

        ELSE 'Multiple payment records'
    END AS payment_structure,

    COUNT(*) AS order_count,

    ROUND(
        100.0
        * COUNT(*)
        / SUM(COUNT(*)) OVER (),
        2
    ) AS order_share_pct,

    ROUND(
        AVG(total_payment_value),
        2
    ) AS average_payment_value,

    ROUND(
        MEDIAN(total_payment_value),
        2
    ) AS median_payment_value,

    ROUND(
        AVG(item_count),
        2
    ) AS average_item_count

FROM fact_orders

WHERE
    order_status = 'delivered'
    AND payment_record_count IS NOT NULL

GROUP BY
    CASE
        WHEN payment_record_count = 1
            THEN 'Single payment record'

        ELSE 'Multiple payment records'
    END

ORDER BY average_payment_value DESC;

--
-- 6. SINGLE-TYPE VS MIXED-TYPE PAYMENT ORDERS
--

SELECT
    CASE
        WHEN uses_multiple_payment_types = TRUE
            THEN 'Multiple payment types'

        ELSE 'Single payment type'
    END AS payment_type_structure,

    COUNT(*) AS order_count,

    ROUND(
        100.0
        * COUNT(*)
        / SUM(COUNT(*)) OVER (),
        2
    ) AS order_share_pct,

    ROUND(
        AVG(total_payment_value),
        2
    ) AS average_payment_value,

    ROUND(
        MEDIAN(total_payment_value),
        2
    ) AS median_payment_value,

    ROUND(
        AVG(payment_record_count),
        2
    ) AS average_payment_records,

    ROUND(
        AVG(primary_payment_share) * 100.0,
        2
    ) AS average_primary_payment_share_pct

FROM fact_orders

WHERE
    order_status = 'delivered'
    AND payment_type_count IS NOT NULL

GROUP BY
    uses_multiple_payment_types

ORDER BY average_payment_value DESC;

-- 
-- 7. MOST COMMON MULTI-PAYMENT-TYPE COMBINATIONS
-- 

WITH order_payment_types AS (

    SELECT DISTINCT
        order_id,
        payment_type_clean

    FROM payments_clean

    WHERE payment_type_clean IS NOT NULL
),

payment_combinations AS (

    SELECT
        order_id,

        STRING_AGG(
            payment_type_clean,
            ' + '
            ORDER BY payment_type_clean
        ) AS payment_combination,

        COUNT(*) AS payment_type_count

    FROM order_payment_types

    GROUP BY order_id
),

mixed_orders AS (

    SELECT
        p.order_id,
        p.payment_combination,
        o.total_payment_value

    FROM payment_combinations AS p

    INNER JOIN fact_orders AS o
        ON p.order_id = o.order_id

    WHERE
        p.payment_type_count > 1
        AND o.order_status = 'delivered'
)

SELECT
    payment_combination,

    COUNT(*) AS order_count,

    ROUND(
        100.0
        * COUNT(*)
        / SUM(COUNT(*)) OVER (),
        2
    ) AS share_of_mixed_orders_pct,

    ROUND(
        AVG(total_payment_value),
        2
    ) AS average_payment_value

FROM mixed_orders

GROUP BY payment_combination

ORDER BY order_count DESC;

