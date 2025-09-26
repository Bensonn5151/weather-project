# Weather Data Pipeline - Secure Version
# This script uses environment variables for sensitive configuration

import json
import requests
import csv
import pandas as pd
from datetime import datetime
import os
import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import JSONB
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration from environment variables
API_KEY = os.getenv('OPENWEATHER_API_KEY')
CITY = os.getenv('CITY', 'Calgary')

# Database Configuration from environment variables
DB_USERNAME = os.getenv('DB_USERNAME', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'ben')

# Validate required environment variables
if not API_KEY:
    raise ValueError("OPENWEATHER_API_KEY environment variable is required")
if not DB_PASSWORD:
    raise ValueError("DB_PASSWORD environment variable is required")

# Pipeline configuration
lat = []
lon = []
state_code = []
country_code = []
limit = 5
cnt = 240  # 240 hours

def main_request(baseurl, endpoint):
    """Make API request to OpenWeatherMap"""
    url = f"{baseurl}{endpoint}"
    r = requests.get(url)
    return r.json()

def parse_list(response):
    """Parse weather data from API response"""
    charlist = []
    for item in response['list']:
        dt = item['dt_txt']
        temp = item['main']['temp']
        weather_info = {
            "weather": item['weather'][0]['main'],
            "description": item['weather'][0]['description']
        }
        conv_temp = temp - 273.15
        print(f"{dt}: {temp}K", {weather_info['weather']}, {weather_info['description']})
        
        char = {
            "datetime": dt,
            "temperature": temp,
            "weather_info": json.dumps(weather_info),
            "conv_temp": round(conv_temp, 2)
        }
        charlist.append(char)
    return charlist

def create_database_engine():
    """Create SQLAlchemy engine with secure credentials"""
    connection_string = f'postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    return create_engine(connection_string)

def create_weather_table(engine):
    """Create the weather_data_scd table if it doesn't exist"""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS calgary_weather_data (
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
        """))

def upsert_weather_scd_type2(engine, new_data):
    """Upsert weather data using SCD Type 2 methodology"""
    with engine.begin() as conn:
        # Expire current record if data has changed
        expire_query = text("""
            UPDATE calgary_weather_data
            SET valid_to = NOW(), is_current = FALSE
            WHERE datetime = :datetime
              AND is_current = TRUE
              AND (
                  temperature != :temperature OR
                  conv_temp != :conv_temp OR
                  weather_info != :weather_info
              );
        """)
        conn.execute(expire_query, new_data)

        # Insert new current record if not already there
        insert_query = text("""
            INSERT INTO calgary_weather_data (
                datetime, temperature, conv_temp, weather_info,
                valid_from, valid_to, is_current
            )
            SELECT 
                :datetime, :temperature, :conv_temp, :weather_info,
                NOW(), NULL, TRUE
            WHERE NOT EXISTS (
                SELECT 1 FROM calgary_weather_data
                WHERE datetime = :datetime
                  AND temperature = :temperature
                  AND conv_temp = :conv_temp
                  AND weather_info = :weather_info
                  AND is_current = TRUE
            );
        """)
        conn.execute(insert_query, new_data)

def main():
    """Main pipeline execution"""
    print("Starting Weather Data Pipeline...")
    
    # Step 1: Extract data from API
    print("1. Extracting data from OpenWeatherMap API...")
    baseurl = 'http://api.openweathermap.org/data/2.5/forecast?q='
    endpoint = f'{CITY}&cnt={cnt}&appid={API_KEY}'
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={CITY}&cnt={cnt}&appid={API_KEY}"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        data = main_request(baseurl, endpoint)
        print("✓ API data extracted successfully")
    else:
        print(f"✗ Failed to retrieve data. Status code: {response.status_code}")
        return
    
    # Step 2: Transform data
    print("2. Transforming data...")
    parsed_data = parse_list(data)
    weather_df = pd.DataFrame(parsed_data)
    weather_df['valid_from'] = datetime.now()
    print("✓ Data transformation completed")
    
    # Step 3: Save to CSV
    print("3. Saving to CSV...")
    weather_df.to_csv('weather_forecast_json.csv', index=False)
    print("✓ CSV file saved")
    
    # Step 4: Load to database
    print("4. Loading data to PostgreSQL...")
    try:
        engine = create_database_engine()
        create_weather_table(engine)
        
        # Insert data using SCD Type 2
        for _, row in weather_df.iterrows():
            new_data = {
                'datetime': row['datetime'],
                'temperature': row['temperature'],
                'conv_temp': row['conv_temp'],
                'weather_info': row['weather_info']
            }
            upsert_weather_scd_type2(engine, new_data)
        
        print("✓ Data loaded to database successfully")
        
        # Step 5: Verify data
        print("5. Verifying data...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM calgary_weather_data WHERE is_current = TRUE"))
            current_count = result.fetchone()[0]
            print(f"✓ Current records in database: {current_count}")
            
    except Exception as e:
        print(f"✗ Database error: {e}")
        return
    
    print("Pipeline completed successfully!")

if __name__ == "__main__":
    main() 