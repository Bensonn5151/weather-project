-- =====================================================
-- Weather Data Pipeline - SCD Type 2 Query Examples
-- =====================================================
-- This file contains various SQL queries to analyze weather data
-- stored using Slowly Changing Dimension (SCD) Type 2 methodology

-- =====================================================
-- 1. BASIC DATA EXPLORATION
-- =====================================================

-- View all records in the weather_data_scd table
SELECT * FROM public.weather_data_scd
ORDER BY id ASC;

-- Count total records
SELECT COUNT(*) as total_records FROM weather_data_scd;

-- Count current vs historical records
SELECT 
    is_current,
    COUNT(*) as record_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM weather_data_scd 
GROUP BY is_current;

-- =====================================================
-- 2. TEMPERATURE ANALYSIS WITH LABELS
-- =====================================================

-- Temperature analysis with categorical labels
SELECT 
    datetime,
    weather_info,
    conv_temp,
    CASE
        WHEN conv_temp > 25 THEN 'hot'
        WHEN conv_temp > 18 THEN 'warm'
        WHEN conv_temp > 9 THEN 'mild'
        WHEN conv_temp > 1 THEN 'cold'
        ELSE 'very cold'
    END AS temperature_label
FROM weather_data_scd
-- WHERE is_current = TRUE  -- Uncomment to see only current forecasts
ORDER BY conv_temp DESC;

-- Temperature distribution by category
SELECT 
    CASE
        WHEN conv_temp > 25 THEN 'hot'
        WHEN conv_temp > 18 THEN 'warm'
        WHEN conv_temp > 9 THEN 'mild'
        WHEN conv_temp > 1 THEN 'cold'
        ELSE 'very cold'
    END AS temperature_category,
    COUNT(*) as forecast_count,
    ROUND(AVG(conv_temp), 2) as avg_temperature,
    MIN(conv_temp) as min_temperature,
    MAX(conv_temp) as max_temperature
FROM weather_data_scd
WHERE is_current = TRUE
GROUP BY temperature_category
ORDER BY avg_temperature DESC;

-- =====================================================
-- 3. FORECAST CHANGE ANALYSIS (SCD Type 2 Specific)
-- =====================================================

-- Identify forecasts that have changed (multiple versions)
SELECT 
    datetime, 
    COUNT(*) as forecast_changes,
    MIN(conv_temp) as min_temp,
    MAX(conv_temp) as max_temp,
    ROUND(MAX(conv_temp) - MIN(conv_temp), 2) as temp_variance
FROM weather_data_scd 
GROUP BY datetime
HAVING COUNT(*) > 1
ORDER BY forecast_changes DESC, temp_variance DESC;

-- Detailed view of all versions for a specific datetime
SELECT 
    datetime, 
    temperature, 
    conv_temp, 
    weather_info,
    valid_from, 
    valid_to, 
    is_current
FROM weather_data_scd 
WHERE datetime = '2025-06-22 09:00:00'
ORDER BY valid_from;

-- Show all historical changes with time intervals
SELECT 
    datetime,
    conv_temp,
    weather_info,
    valid_from,
    valid_to,
    is_current,
    CASE 
        WHEN valid_to IS NULL THEN 'Current'
        ELSE CONCAT(
            EXTRACT(EPOCH FROM (valid_to - valid_from))/3600, ' hours'
        )
    END as validity_duration
FROM weather_data_scd 
WHERE datetime IN (
    SELECT datetime 
    FROM weather_data_scd 
    GROUP BY datetime 
    HAVING COUNT(*) > 1
)
ORDER BY datetime, valid_from;

-- =====================================================
-- 4. WEATHER PATTERN ANALYSIS
-- =====================================================

-- Weather condition distribution
SELECT 
    weather_info->>'weather' as weather_type,
    weather_info->>'description' as weather_description,
    COUNT(*) as occurrence_count,
    ROUND(AVG(conv_temp), 2) as avg_temperature
FROM weather_data_scd
WHERE is_current = TRUE
GROUP BY weather_info->>'weather', weather_info->>'description'
ORDER BY occurrence_count DESC;

-- Temperature trends by hour of day
SELECT 
    EXTRACT(HOUR FROM datetime) as hour_of_day,
    COUNT(*) as forecast_count,
    ROUND(AVG(conv_temp), 2) as avg_temperature,
    MIN(conv_temp) as min_temperature,
    MAX(conv_temp) as max_temperature
FROM weather_data_scd
WHERE is_current = TRUE
GROUP BY EXTRACT(HOUR FROM datetime)
ORDER BY hour_of_day;

-- Temperature trends by day of week
SELECT 
    TO_CHAR(datetime, 'Day') as day_of_week,
    COUNT(*) as forecast_count,
    ROUND(AVG(conv_temp), 2) as avg_temperature,
    MIN(conv_temp) as min_temperature,
    MAX(conv_temp) as max_temperature
FROM weather_data_scd
WHERE is_current = TRUE
GROUP BY TO_CHAR(datetime, 'Day')
ORDER BY avg_temperature DESC;

-- =====================================================
-- 5. DATA QUALITY AND MONITORING QUERIES
-- =====================================================

-- Identify data quality issues
SELECT 
    'Missing valid_to for non-current records' as issue_type,
    COUNT(*) as issue_count
FROM weather_data_scd 
WHERE is_current = FALSE AND valid_to IS NULL

UNION ALL

SELECT 
    'Records with valid_to but marked as current' as issue_type,
    COUNT(*) as issue_count
FROM weather_data_scd 
WHERE is_current = TRUE AND valid_to IS NOT NULL

UNION ALL

SELECT 
    'Duplicate current records for same datetime' as issue_type,
    COUNT(*) as issue_count
FROM (
    SELECT datetime, COUNT(*) as cnt
    FROM weather_data_scd 
    WHERE is_current = TRUE
    GROUP BY datetime
    HAVING COUNT(*) > 1
) duplicates;

-- Data freshness check
SELECT 
    'Oldest current record' as metric,
    MIN(valid_from) as value
FROM weather_data_scd 
WHERE is_current = TRUE

UNION ALL

SELECT 
    'Newest current record' as metric,
    MAX(valid_from) as value
FROM weather_data_scd 
WHERE is_current = TRUE

UNION ALL

SELECT 
    'Total hours of data coverage' as metric,
    EXTRACT(EPOCH FROM (MAX(datetime) - MIN(datetime)))/3600 as value
FROM weather_data_scd 
WHERE is_current = TRUE;

-- =====================================================
-- 6. FORECAST ACCURACY ANALYSIS (Historical)
-- =====================================================

-- Compare forecast changes over time
SELECT 
    datetime,
    COUNT(*) as version_count,
    ROUND(AVG(conv_temp), 2) as avg_forecast_temp,
    ROUND(STDDEV(conv_temp), 2) as temp_std_dev,
    ROUND(MAX(conv_temp) - MIN(conv_temp), 2) as temp_range,
    MIN(valid_from) as first_forecast,
    MAX(valid_from) as last_forecast
FROM weather_data_scd 
WHERE datetime < NOW()  -- Only past forecasts
GROUP BY datetime
HAVING COUNT(*) > 1
ORDER BY temp_range DESC;

-- Forecast stability analysis
SELECT 
    datetime,
    conv_temp,
    weather_info,
    valid_from,
    LAG(conv_temp) OVER (PARTITION BY datetime ORDER BY valid_from) as previous_temp,
    LAG(weather_info) OVER (PARTITION BY datetime ORDER BY valid_from) as previous_weather,
    ROUND(conv_temp - LAG(conv_temp) OVER (PARTITION BY datetime ORDER BY valid_from), 2) as temp_change
FROM weather_data_scd 
WHERE datetime IN (
    SELECT datetime 
    FROM weather_data_scd 
    GROUP BY datetime 
    HAVING COUNT(*) > 1
)
ORDER BY datetime, valid_from;

-- =====================================================
-- 7. OPERATIONAL QUERIES
-- =====================================================

-- Get current weather forecast for next 24 hours
SELECT 
    datetime,
    conv_temp,
    weather_info->>'weather' as weather_type,
    weather_info->>'description' as description
FROM weather_data_scd 
WHERE is_current = TRUE 
  AND datetime BETWEEN NOW() AND NOW() + INTERVAL '24 hours'
ORDER BY datetime;

-- Get weather forecast for a specific date range
SELECT 
    datetime,
    conv_temp,
    weather_info->>'weather' as weather_type,
    weather_info->>'description' as description
FROM weather_data_scd 
WHERE is_current = TRUE 
  AND datetime BETWEEN '2025-06-22' AND '2025-06-25'
ORDER BY datetime;

-- Find the most volatile forecasts (frequently changing)
SELECT 
    datetime,
    COUNT(*) as change_count,
    ROUND(MAX(conv_temp) - MIN(conv_temp), 2) as temp_variance,
    ROUND(AVG(conv_temp), 2) as avg_temp
FROM weather_data_scd 
GROUP BY datetime
HAVING COUNT(*) > 2  -- More than 2 versions
ORDER BY change_count DESC, temp_variance DESC
LIMIT 10;

-- =====================================================
-- 8. CLEANUP AND MAINTENANCE QUERIES
-- =====================================================

-- Archive old historical records (older than 30 days)
-- Note: This is a template - implement based on your retention policy
/*
INSERT INTO weather_data_archive 
SELECT * FROM weather_data_scd 
WHERE valid_from < NOW() - INTERVAL '30 days'
  AND is_current = FALSE;

DELETE FROM weather_data_scd 
WHERE valid_from < NOW() - INTERVAL '30 days'
  AND is_current = FALSE;
*/

-- Check for orphaned records (current records with no historical context)
SELECT 
    datetime,
    valid_from,
    'Orphaned current record' as issue
FROM weather_data_scd w1
WHERE is_current = TRUE
  AND NOT EXISTS (
    SELECT 1 FROM weather_data_scd w2
    WHERE w2.datetime = w1.datetime
      AND w2.is_current = FALSE
  );

-- =====================================================
-- 9. PERFORMANCE OPTIMIZATION QUERIES
-- =====================================================

-- Check index usage and query performance
-- (Run these in your database monitoring tool)

-- Suggested indexes for better performance:
/*
CREATE INDEX IF NOT EXISTS idx_weather_datetime_current 
ON weather_data_scd(datetime, is_current);

CREATE INDEX IF NOT EXISTS idx_weather_valid_from 
ON weather_data_scd(valid_from);

CREATE INDEX IF NOT EXISTS idx_weather_valid_to 
ON weather_data_scd(valid_to);

CREATE INDEX IF NOT EXISTS idx_weather_conv_temp 
ON weather_data_scd(conv_temp);

CREATE INDEX IF NOT EXISTS idx_weather_datetime_valid_from 
ON weather_data_scd(datetime, valid_from);
*/

-- =====================================================
-- 10. SUMMARY STATISTICS
-- =====================================================

-- Overall dataset summary
SELECT 
    'Dataset Summary' as metric,
    '' as value

UNION ALL

SELECT 
    'Total Records' as metric,
    COUNT(*)::TEXT as value
FROM weather_data_scd

UNION ALL

SELECT 
    'Current Records' as metric,
    COUNT(*)::TEXT as value
FROM weather_data_scd
WHERE is_current = TRUE

UNION ALL

SELECT 
    'Historical Records' as metric,
    COUNT(*)::TEXT as value
FROM weather_data_scd
WHERE is_current = FALSE

UNION ALL

SELECT 
    'Unique Forecast Times' as metric,
    COUNT(DISTINCT datetime)::TEXT as value
FROM weather_data_scd

UNION ALL

SELECT 
    'Forecasts with Changes' as metric,
    COUNT(*)::TEXT as value
FROM (
    SELECT datetime
    FROM weather_data_scd 
    GROUP BY datetime
    HAVING COUNT(*) > 1
) changes

UNION ALL

SELECT 
    'Average Temperature' as metric,
    ROUND(AVG(conv_temp), 2)::TEXT as value
FROM weather_data_scd
WHERE is_current = TRUE

UNION ALL

SELECT 
    'Temperature Range' as metric,
    CONCAT(ROUND(MIN(conv_temp), 1), '°C to ', ROUND(MAX(conv_temp), 1), '°C') as value
FROM weather_data_scd
WHERE is_current = TRUE; 