# Weather Data Pipeline - Data Modeling Structure

## Overview
This document outlines the data modeling structure for the Weather Data Pipeline using Slowly Changing Dimension (SCD) Type 2 methodology. The pipeline extracts weather forecast data from OpenWeatherMap API, transforms it, and loads it into a PostgreSQL database with complete historical tracking.

## Architecture Workflow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   OpenWeather   │───▶│   Data          │───▶│   Data          │───▶│   PostgreSQL    │
│   Map API       │    │   Extraction    │    │   Transformation│    │   Database      │
│                 │    │   (ETL)         │    │   (ETL)         │    │   (SCD Type 2)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
   ┌─────────────┐       ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
   │ Raw JSON    │       │ Parsed      │       │ Transformed │       │ Historical  │
   │ Response    │       │ Data        │       │ DataFrame   │       │ Records     │
   └─────────────┘       └─────────────┘       └─────────────┘       └─────────────┘
```

## Data Flow Process

```
1. EXTRACT (API Call)
   ┌─────────────────────────────────────────────────────────────┐
   │ OpenWeatherMap API Response                                │
   │ {                                                          │
   │   "list": [                                                │
   │     {                                                      │
   │       "dt": 1750582800,                                    │
   │       "main": {"temp": 294.01, "feels_like": 293.9, ...},  │
   │       "weather": [{"id": 801, "main": "Clouds", ...}],     │
   │       "dt_txt": "2025-06-22 09:00:00"                      │
   │     }                                                      │
   │   ]                                                        │
   │ }                                                          │
   └─────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
2. TRANSFORM (Data Processing)
   ┌─────────────────────────────────────────────────────────────┐
   │ Parsed Data Structure                                       │
   │ {                                                          │
   │   "datetime": "2025-06-22 09:00:00",                       │
   │   "temperature": 294.01,                                    │
   │   "conv_temp": 20.86,                                       │
   │   "weather_info": {                                         │
   │     "weather": "Clouds",                                    │
   │     "description": "few clouds"                             │
   │   }                                                         │
   │ }                                                           │
   └─────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
3. LOAD (SCD Type 2)
   ┌─────────────────────────────────────────────────────────────┐
   │ Database Table: weather_data_scd                           │
   │ ┌─────┬─────────────┬──────────┬──────────┬──────────────┐ │
   │ │ id  │ datetime    │ temp     │ conv_temp│ weather_info │ │
   │ ├─────┼─────────────┼──────────┼──────────┼──────────────┤ │
   │ │ 1   │ 2025-06-22  │ 294.01   │ 20.86    │ {"weather":  │ │
   │ │     │ 09:00:00    │          │          │  "Clouds",   │ │
   │ │     │             │          │          │  "desc":     │ │
   │ │     │             │          │          │  "few clouds"│ │
   │ └─────┴─────────────┴──────────┴──────────┴──────────────┘ │
   └─────────────────────────────────────────────────────────────┘
```

## Database Schema Design

### Fact Table: `weather_data_scd`

```sql
CREATE TABLE weather_data_scd (
    id SERIAL PRIMARY KEY,                    -- Surrogate key
    datetime TIMESTAMP,                       -- Business key (forecast time)
    temperature DECIMAL(5,2),                 -- Temperature in Kelvin
    conv_temp DECIMAL(5,2),                   -- Temperature in Celsius
    weather_info JSONB NOT NULL,              -- Weather conditions (JSON)
    valid_from TIMESTAMP DEFAULT NOW(),       -- SCD Type 2: When record became valid
    valid_to TIMESTAMP,                       -- SCD Type 2: When record expired
    is_current BOOLEAN DEFAULT TRUE,          -- SCD Type 2: Current version flag
    UNIQUE(datetime, valid_from)              -- Composite unique constraint
);
```

#### Fact Table Structure
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FACT TABLE: weather_data_scd                      │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────────────────┤
│ Column      │ Data Type   │ Description │ SCD Type 2  │ Sample Value        │
├─────────────┼─────────────┼─────────────┼─────────────┼─────────────────────┤
│ id          │ SERIAL      │ Primary Key │ No          │ 1, 2, 3, ...        │
│ datetime    │ TIMESTAMP   │ Forecast    │ Business    │ 2025-06-22 09:00:00 │
│             │             │ Time        │ Key         │                     │
│ temperature │ DECIMAL(5,2)│ Temp (K)    │ Yes         │ 294.01              │
│ conv_temp   │ DECIMAL(5,2)│ Temp (°C)   │ Yes         │ 20.86               │
│ weather_info│ JSONB       │ Conditions  │ Yes         │ {"weather":         │
│             │             │             │             │  "Clouds",          │
│             │             │             │             │  "description":     │
│             │             │             │             │  "few clouds"}      │
│ valid_from  │ TIMESTAMP   │ Valid From  │ SCD Type 2  │ 2025-06-21 17:47:50 │
│ valid_to    │ TIMESTAMP   │ Valid To    │ SCD Type 2  │ NULL (current)      │
│ is_current  │ BOOLEAN     │ Current     │ SCD Type 2  │ TRUE                │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────────────┘
```

### Dimension Tables (Logical)

#### 1. Time Dimension (Derived from datetime)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TIME DIMENSION (Derived)                             │
├─────────────┬─────────────┬─────────────┬─────────────────────────────────────┤
│ Column      │ Data Type   │ Description │ Sample Value                        │
├─────────────┼─────────────┼─────────────┼─────────────────────────────────────┤
│ datetime    │ TIMESTAMP   │ Full Date   │ 2025-06-22 09:00:00                │
│ date        │ DATE        │ Date Only   │ 2025-06-22                         │
│ hour        │ INTEGER     │ Hour (0-23) │ 9                                  │
│ day_of_week │ VARCHAR     │ Day Name    │ Sunday                             │
│ month       │ INTEGER     │ Month (1-12)│ 6                                  │
│ year        │ INTEGER     │ Year        │ 2025                               │
│ is_weekend  │ BOOLEAN     │ Weekend?    │ FALSE                              │
└─────────────┴─────────────┴─────────────┴─────────────────────────────────────┘
```

#### 2. Weather Condition Dimension (Derived from weather_info)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    WEATHER CONDITION DIMENSION (Derived)                    │
├─────────────┬─────────────┬─────────────┬─────────────────────────────────────┤
│ Column      │ Data Type   │ Description │ Sample Value                        │
├─────────────┼─────────────┼─────────────┼─────────────────────────────────────┤
│ weather_id  │ INTEGER     │ Weather ID  │ 801                                │
│ weather_type│ VARCHAR     │ Main Type   │ Clouds                             │
│ description │ VARCHAR     │ Description │ few clouds                         │
│ icon        │ VARCHAR     │ Icon Code   │ 02d                                │
│ category    │ VARCHAR     │ Category    │ Cloudy                             │
└─────────────┴─────────────┴─────────────┴─────────────────────────────────────┘
```

#### 3. Temperature Category Dimension (Derived from conv_temp)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TEMPERATURE CATEGORY DIMENSION                           │
├─────────────┬─────────────┬─────────────┬─────────────────────────────────────┤
│ Column      │ Data Type   │ Description │ Sample Value                        │
├─────────────┼─────────────┼─────────────┼─────────────────────────────────────┤
│ temp_range  │ VARCHAR     │ Range       │ 20-25°C                            │
│ category    │ VARCHAR     │ Category    │ warm                               │
│ min_temp    │ DECIMAL     │ Min Temp    │ 20.0                               │
│ max_temp    │ DECIMAL     │ Max Temp    │ 25.0                               │
│ description │ VARCHAR     │ Description │ Comfortable warm weather           │
└─────────────┴─────────────┴─────────────┴─────────────────────────────────────┘
```

## SCD Type 2 Implementation Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SCD Type 2 Process Flow                           │
└─────────────────────────────────────────────────────────────────────────────┘

1. NEW DATA ARRIVES
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ New Forecast: datetime='2025-06-22 09:00:00', temp=23.5°C              │
   └─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
2. CHECK FOR EXISTING CURRENT RECORD
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ SELECT * FROM weather_data_scd                                         │
   │ WHERE datetime = '2025-06-22 09:00:00' AND is_current = TRUE          │
   │                                                                        │
   │ Result: Found existing record with temp=20.86°C                       │
   └─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
3. COMPARE DATA FOR CHANGES
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ Old: temp=20.86°C, weather="few clouds"                               │
   │ New: temp=23.5°C, weather="scattered clouds"                          │
   │                                                                        │
   │ Decision: Data has changed → Trigger SCD Type 2                       │
   └─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
4. EXPIRE CURRENT RECORD
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ UPDATE weather_data_scd                                               │
   │ SET valid_to = NOW(), is_current = FALSE                             │
   │ WHERE datetime = '2025-06-22 09:00:00' AND is_current = TRUE          │
   └─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
5. INSERT NEW CURRENT RECORD
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ INSERT INTO weather_data_scd (                                        │
   │   datetime, temperature, conv_temp, weather_info,                     │
   │   valid_from, valid_to, is_current                                    │
   │ ) VALUES (                                                            │
   │   '2025-06-22 09:00:00', 296.65, 23.5,                               │
   │   '{"weather": "Clouds", "description": "scattered clouds"}',         │
   │   NOW(), NULL, TRUE                                                   │
   │ )                                                                      │
   └─────────────────────────────────────────────────────────────────────────┘
```

## Historical Record Example

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Historical Records for 2025-06-22 09:00:00              │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────────────────┤
│ Version     │ Temperature │ Valid From  │ Valid To    │ Weather Condition   │
├─────────────┼─────────────┼─────────────┼─────────────┼─────────────────────┤
│ 1           │ 22.75°C     │ 2025-06-21  │ 2025-06-22  │ few clouds          │
│             │             │ 17:47:50    │ 08:13:29    │                     │
├─────────────┼─────────────┼─────────────┼─────────────┼─────────────────────┤
│ 2           │ 19.62°C     │ 2025-06-22  │ 2025-06-22  │ broken clouds       │
│             │             │ 08:13:29    │ 08:36:28    │                     │
├─────────────┼─────────────┼─────────────┼─────────────┼─────────────────────┤
│ 3           │ 19.97°C     │ 2025-06-22  │ 2025-06-22  │ few clouds          │
│             │             │ 08:36:28    │ 08:39:02    │                     │
├─────────────┼─────────────┼─────────────┼─────────────┼─────────────────────┤
│ 4           │ 20.07°C     │ 2025-06-22  │ 2025-06-22  │ few clouds          │
│             │             │ 08:39:02    │ 08:44:12    │                     │
├─────────────┼─────────────┼─────────────┼─────────────┼─────────────────────┤
│ 5           │ 19.97°C     │ 2025-06-22  │ 2025-06-22  │ few clouds          │
│             │             │ 08:44:12    │ 08:45:31    │                     │
├─────────────┼─────────────┼─────────────┼─────────────┼─────────────────────┤
│ 6           │ 20.07°C     │ 2025-06-22  │ 2025-06-22  │ few clouds          │
│             │             │ 08:45:31    │ 09:03:43    │                     │
├─────────────┼─────────────┼─────────────┼─────────────┼─────────────────────┤
│ 7 (Current) │ 20.82°C     │ 2025-06-22  │ NULL        │ few clouds          │
│             │             │ 09:03:43    │ (Current)   │                     │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────────────┘
```

## Data Quality and Monitoring

### Data Quality Checks
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Data Quality Monitoring                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Completeness: All required fields present                               │
│ 2. Accuracy: Temperature conversion validation (K to °C)                   │
│ 3. Consistency: JSONB format validation for weather_info                   │
│ 4. Timeliness: Data freshness checks                                       │
│ 5. Integrity: SCD Type 2 constraint validation                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Performance Optimization
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Performance Indexes                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ CREATE INDEX idx_weather_datetime_current                                   │
│   ON weather_data_scd(datetime, is_current);                               │
│                                                                             │
│ CREATE INDEX idx_weather_valid_from                                         │
│   ON weather_data_scd(valid_from);                                         │
│                                                                             │
│ CREATE INDEX idx_weather_valid_to                                           │
│   ON weather_data_scd(valid_to);                                           │
│                                                                             │
│ CREATE INDEX idx_weather_conv_temp                                          │
│   ON weather_data_scd(conv_temp);                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Business Intelligence Capabilities

### Analytical Queries Supported
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BI Capabilities                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Historical Trend Analysis                                               │
│    - Temperature changes over time                                         │
│    - Weather pattern evolution                                             │
│                                                                             │
│ 2. Forecast Accuracy Analysis                                              │
│    - Compare initial vs. updated forecasts                                 │
│    - Track forecast stability                                               │
│                                                                             │
│ 3. Temporal Analysis                                                       │
│    - Hourly temperature patterns                                           │
│    - Daily weather trends                                                   │
│                                                                             │
│ 4. Data Quality Metrics                                                    │
│    - Forecast change frequency                                             │
│    - Data completeness rates                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Summary

This data modeling structure provides:

1. **Complete Historical Tracking**: SCD Type 2 maintains all versions of weather data
2. **Flexible Schema**: JSONB allows for extensible weather information
3. **Performance Optimized**: Proper indexing for efficient queries
4. **Data Quality**: Built-in validation and monitoring capabilities
5. **Business Intelligence**: Rich analytical capabilities for weather analysis

The design supports both operational queries (current weather) and analytical queries (historical trends, forecast accuracy) while maintaining data lineage and audit trails. 