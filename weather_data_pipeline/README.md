# Weather Data Pipeline Orchestrated with Airflow

## Why Airflow?
This project uses **Apache Airflow** to automate and schedule the end-to-end weather data pipeline. Airflow ensures reliability, repeatability, and easy monitoring of all ETL steps.

## What is SCD Type 2?
The pipeline loads weather data into PostgreSQL using the **Slowly Changing Dimension (SCD) Type 2** method. This approach preserves historical changes, so you always know how and when forecasts changed.

## Why Use Airflow and SCD Type 2 Together?
- **Airflow**: Automates and schedules the pipeline, making it robust and production-ready.
- **SCD Type 2**: Ensures you never lose historical weather forecast changes, supporting analytics, compliance, and data lineage.
- **Combined**: You get a reliable, auditable, and fully automated weather data history system.

## Quick Start

1. **Install Dependencies**
```bash
pip install pandas requests psycopg2-binary sqlalchemy python-dotenv apache-airflow
```

2. **Configure Environment**
Create a `.env` file in the project root:
```env
OPENWEATHER_API_KEY=your_api_key
DB_USERNAME=your_db_username
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ben
CITY=London
```


3. **Run with Airflow**
```bash
export AIRFLOW_HOME=~/airflow
airflow db init
# (First time only) Create an admin user:
airflow users create --username admin --firstname FIRST --lastname LAST --role Admin --email admin@example.com
# Copy or symlink `dags/weather_pipeline_dag.py` to your Airflow `dags/` folder
airflow scheduler &
airflow webserver or airflow api-server &
```
- Open http://localhost:8080, enable `weather_pipeline_dag`, and trigger as needed.

## Project Overview

This project implements a comprehensive weather data pipeline that extracts weather forecast data from the OpenWeatherMap API, transforms it into a structured format, and loads it into a PostgreSQL database using Slowly Changing Dimension (SCD) Type 2 methodology. The pipeline addresses critical challenges in data versioning and historical tracking that are common in real-time data ingestion scenarios.

## Architecture

```
OpenWeatherMap API → Data Extraction → Transformation → PostgreSQL (SCD Type 2)
```

## Key Components

1. **Airflow Orchestration**
   - Manages, schedules, and monitors the entire ETL pipeline as a DAG (Directed Acyclic Graph)
   - Ensures reliable, repeatable, and automated execution of all steps

2. **Data Extraction (ETL)**
   - API Integration: Connects to OpenWeatherMap API using REST endpoints
   - Data Fetching: Retrieves 5-day weather forecasts (40 data points, 3-hour intervals)
   - Error Handling: Implements status code validation and response processing

3. **Data Transformation**
   - Temperature Conversion: Converts Kelvin to Celsius for better usability
   - Weather Information Structuring: Organizes weather conditions and descriptions
   - Timestamp Processing: Handles datetime formatting and validation

4. **Data Loading with SCD Type 2**
   - Historical Tracking: Maintains complete audit trail of all data changes
   - Version Control: Tracks when data was valid and when it changed
   - Current State Management: Identifies the most recent version of each record

## The Critical Problem: Data Versioning Challenges

### Why Traditional Approaches Fail

When working with real-time APIs like weather data, several critical issues arise:

#### 1. **Data Overwriting Problem**
```sql
-- Traditional approach - DESTRUCTIVE
UPDATE weather_data 
SET temperature = 25.5, 
    weather_info = '{"weather": "Clouds", "description": "scattered clouds"}'
WHERE datetime = '2025-06-22 09:00:00';
```
**Problem**: Previous values are permanently lost. You can't answer questions like:
- "What was the temperature forecast yesterday vs. today?"
- "How many times did the forecast change for this time period?"
- "What was the original prediction vs. the updated one?"

#### 2. **API Data Updates**
Weather APIs frequently update their forecasts:
- **Initial forecast**: 25°C, sunny
- **Updated forecast**: 23°C, cloudy
- **Final actual**: 24°C, partly cloudy

Without versioning, you lose the evolution of predictions.

#### 3. **Audit Trail Requirements**
Many use cases require complete historical records:
- **Compliance**: Regulatory requirements for data retention
- **Analysis**: Understanding forecast accuracy over time
- **Debugging**: Identifying when and why data changed

#### 4. **Data Lineage Issues**
```python
# Problem: No way to track data provenance
weather_data = {
    'datetime': '2025-06-22 09:00:00',
    'temperature': 25.5,  # When was this value set?
    'source': 'api'       # Which API call? When?
}
```
## SCD Type 2 Solution

### How SCD Type 2 Solves These Problems

SCD Type 2 creates a complete audit trail by:

#### 1. **Non-Destructive Updates**
```sql
-- Instead of updating, we expire the old record and insert a new one
UPDATE weather_data_scd 
SET valid_to = NOW(), is_current = FALSE
WHERE datetime = '2025-06-22 09:00:00' AND is_current = TRUE;

INSERT INTO weather_data_scd (
    datetime, temperature, conv_temp, weather_info,
    valid_from, valid_to, is_current
) VALUES (
    '2025-06-22 09:00:00', 23.0, 23.0, 
    '{"weather": "Clouds", "description": "scattered clouds"}',
    NOW(), NULL, TRUE
);
```

#### 2. **Complete Historical Record**
```sql
-- Query to see all versions of a specific forecast
SELECT datetime, temperature, conv_temp, weather_info,
       valid_from, valid_to, is_current
FROM weather_data_scd 
WHERE datetime = '2025-06-22 09:00:00'
ORDER BY valid_from;
```

**Result**:
```
datetime            | temperature | conv_temp | weather_info                    | valid_from           | valid_to             | is_current
2025-06-22 09:00:00 | 293.22      | 20.07     | {"weather": "Clouds", ...}     | 2025-06-21 17:47:50  | 2025-06-22 08:30:15  | FALSE
2025-06-22 09:00:00 | 293.15      | 20.00     | {"weather": "Clouds", ...}     | 2025-06-22 08:30:15  | NULL                 | TRUE
```

#### 3. **Current State Queries**
```sql
-- Get only current forecasts
SELECT * FROM weather_data_scd WHERE is_current = TRUE;

-- Get historical analysis
SELECT datetime, 
       COUNT(*) as forecast_changes,
       MIN(conv_temp) as min_temp,
       MAX(conv_temp) as max_temp
FROM weather_data_scd 
GROUP BY datetime
HAVING COUNT(*) > 1;
```

## Implementation Details

### Database Schema

```sql
CREATE TABLE weather_data_scd (
    id SERIAL PRIMARY KEY,
    datetime TIMESTAMP,
    temperature DECIMAL(5,2),
    conv_temp DECIMAL(5,2),
    weather_info JSONB NOT NULL,
    valid_from TIMESTAMP DEFAULT NOW(),
    valid_to TIMESTAMP,
    is_current BOOLEAN DEFAULT TRUE,
    UNIQUE(datetime, valid_from)
);
```

### Key Features

1. **JSONB Storage**: Efficient storage of weather information as JSON
2. **Timestamp Tracking**: `valid_from` and `valid_to` for temporal queries
3. **Current Flag**: `is_current` for quick current state access
4. **Unique Constraints**: Prevents duplicate entries for same datetime/valid_from

### Upsert Logic

```python
def upsert_weather_scd_type2(new_data):
    # 1. Expire current record if data has changed
    # 2. Insert new current record if not already present
    # 3. Maintain referential integrity
```

## Benefits of This Approach

### 1. **Complete Data Lineage**
- Track every change to weather forecasts
- Understand data evolution over time
- Maintain audit trails for compliance

### 2. **Analytical Capabilities**
```sql
-- Forecast accuracy analysis
SELECT 
    datetime,
    COUNT(*) as forecast_updates,
    AVG(conv_temp) as avg_forecast_temp,
    STDDEV(conv_temp) as temp_variance
FROM weather_data_scd 
WHERE datetime < NOW()
GROUP BY datetime
ORDER BY datetime;
```

### 3. **Data Quality Monitoring**
```sql
-- Identify frequently changing forecasts
SELECT datetime, COUNT(*) as changes
FROM weather_data_scd 
GROUP BY datetime 
HAVING COUNT(*) > 3
ORDER BY changes DESC;
```

### 4. **Rollback Capability**
```sql
-- Restore to any point in time
SELECT * FROM weather_data_scd 
WHERE datetime = '2025-06-22 09:00:00'
  AND valid_from <= '2025-06-22 08:00:00'
  AND (valid_to > '2025-06-22 08:00:00' OR valid_to IS NULL);
```

## Performance Considerations

### 1. **Indexing Strategy**
```sql
-- Essential indexes for performance
CREATE INDEX idx_weather_datetime_current ON weather_data_scd(datetime, is_current);
CREATE INDEX idx_weather_valid_from ON weather_data_scd(valid_from);
CREATE INDEX idx_weather_valid_to ON weather_data_scd(valid_to);
```

### 2. **Partitioning**
For large datasets, consider partitioning by date:
```sql
-- Partition by month for better query performance
CREATE TABLE weather_data_scd_2025_06 PARTITION OF weather_data_scd
FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');
```

### 3. **Data Retention**
Implement archival strategies for old data:
```sql
-- Archive data older than 1 year
INSERT INTO weather_data_archive 
SELECT * FROM weather_data_scd 
WHERE valid_from < NOW() - INTERVAL '1 year';
```

## Alternative Approaches Considered

### 1. **Simple Overwrite (Rejected)**
```python
# Problem: Loses history
df.to_sql('weather_data', engine, if_exists='replace', index=False)
```

### 2. **Append-Only (Rejected)**
```python
# Problem: No way to identify current state
df.to_sql('weather_data', engine, if_exists='append', index=False)
```

### 3. **SCD Type 1 (Rejected)**
```python
# Problem: Still loses history
# Only tracks current state, overwrites previous values
```

### 4. **SCD Type 3 (Considered)**
```python
# Problem: Limited history (only previous value)
# Columns: current_temp, previous_temp, change_date
```

## Lessons Learned

### 1. **API Data Volatility**
- Weather forecasts change frequently
- Initial predictions often differ from final forecasts
- Historical tracking is essential for accuracy analysis

### 2. **Data Architecture Decisions**
- SCD Type 2 provides the best balance of functionality and complexity
- JSONB storage offers flexibility for varying weather data structures
- Proper indexing is crucial for query performance

### 3. **Operational Considerations**
- Regular data archival prevents table bloat
- Monitoring forecast change frequency helps identify data quality issues
- Backup strategies must account for temporal data

## Future Enhancements

### 1. **Real-time Processing**
- Implement streaming pipeline using Apache Kafka
- Real-time SCD Type 2 updates
- Event-driven architecture

### 2. **Advanced Analytics**
- Machine learning for forecast accuracy prediction
- Anomaly detection in weather patterns
- Automated data quality scoring

### 3. **Multi-source Integration**
- Combine multiple weather APIs
- Cross-reference data for accuracy
- Implement data fusion algorithms

## Conclusion

The implementation of SCD Type 2 in this weather data pipeline addresses fundamental challenges in real-time data management. By maintaining complete historical records while providing efficient access to current data, this approach enables sophisticated analytics, ensures data lineage, and supports compliance requirements.

The key insight is that in dynamic data environments like weather forecasting, the ability to track changes over time is not just a nice-to-have feature—it's essential for understanding data quality, accuracy, and evolution.

## Contributing

This project demonstrates best practices for data pipeline development with a focus on data versioning and historical tracking. Contributions are welcome, especially in areas of:

- Performance optimization
- Additional data sources
- Advanced analytics
- Monitoring and alerting 
