import streamlit as st
import pandas as pd
import json
from datetime import datetime
from PIL import Image
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# -- Database configuration
def load_db_env():
    """Load database parameters depending on environment."""
    # Try .env.local first (for host)
    local_env = "/Users/apple/Desktop/DEV/PORTFOLIO/weather-project/.env.local"

    if os.path.exists(local_env):
        load_dotenv(dotenv_path=local_env)

    return {
        "DB_USERNAME": os.getenv('DB_USERNAME', 'postgres'),
        "DB_PASSWORD": os.getenv('DB_PASSWORD', 'bens'),
        "DB_HOST": os.getenv('DB_HOST', 'postgres'),
        "DB_PORT": os.getenv('DB_PORT', '5433'),
        "DB_NAME": os.getenv('DB_NAME', 'weather_app')
    }

# -- Database connection with SQLAlchemy
@st.cache_resource
def get_db_engine():
    """Create SQLAlchemy database engine."""
    db_config = load_db_env()
    
    try:
        # Create connection string
        connection_string = f"postgresql://{db_config['DB_USERNAME']}:{db_config['DB_PASSWORD']}@{db_config['DB_HOST']}:{db_config['DB_PORT']}/{db_config['DB_NAME']}"
        
        # Create engine
        engine = create_engine(connection_string)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            
        return engine
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
        return None

# -- Load data from database using SQLAlchemy
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_weather_data():
    """Load weather data from PostgreSQL database using SQLAlchemy."""
    engine = get_db_engine()
    if engine is None:
        return pd.DataFrame()
    
    try:
        # Query to get weather data
        query = """
        SELECT 
            datetime,
            conv_temp,
            weather_info
        FROM calgary_weather_data
        ORDER BY datetime DESC
        """
        
        # Use SQLAlchemy to execute query and load into DataFrame
        with engine.connect() as connection:
            df = pd.read_sql_query(text(query), connection, parse_dates=["datetime"])
        
        # Parse weather info column - SQLAlchemy may return JSON as dict or string depending on configuration
        if "weather_info" in df.columns and df["weather_info"].notna().any():
            try:
                # Handle both dict and string cases
                def parse_weather_value(weather_data, key):
                    if pd.isna(weather_data):
                        return "Unknown" if key == "weather" else "No description"
                    
                    # If it's already a dictionary (SQLAlchemy with JSON support)
                    if isinstance(weather_data, dict):
                        return weather_data.get(key, "Unknown" if key == "weather" else "No description")
                    # If it's a string, try to parse as JSON
                    elif isinstance(weather_data, str):
                        try:
                            parsed = json.loads(weather_data)
                            return parsed.get(key, "Unknown" if key == "weather" else "No description")
                        except json.JSONDecodeError:
                            return "Unknown" if key == "weather" else "No description"
                    else:
                        return "Unknown" if key == "weather" else "No description"
                
                df["weather_main"] = df["weather_info"].apply(
                    lambda x: parse_weather_value(x, "weather")
                )
                df["weather_description"] = df["weather_info"].apply(
                    lambda x: parse_weather_value(x, "description")
                )
                
            except Exception as e:
                st.error(f"Error parsing weather_info: {e}")
                # If parsing fails, create default columns
                df["weather_main"] = "Unknown"
                df["weather_description"] = "No description"
        
        return df
        
    except Exception as e:
        st.error(f"❌ Error loading data from database: {e}")
        return pd.DataFrame()

# -- Initialize the app
st.set_page_config(page_title="Weather Dashboard", layout="wide")
st.title("🌦️ Weather Dashboard")

# -- Load data
df = load_weather_data()

if df.empty:
    st.warning("⚠️ No data found in the database. Please check your connection and data.")
    st.stop()

# -- Date Range Filter
st.sidebar.subheader("🔍 Filters")
date_range = st.sidebar.date_input(
    "📅 Select Date Range",
    [df["datetime"].min().date(), df["datetime"].max().date()]
)

if len(date_range) == 2:
    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    df_filtered = df[(df["datetime"] >= start_date) & (df["datetime"] <= end_date)]
else:
    df_filtered = df.copy()

# -- Location Filter (if available)
if "location" in df_filtered.columns and df_filtered["location"].nunique() > 1:
    locations = df_filtered["location"].unique()
    selected_location = st.sidebar.selectbox("📍 Select Location", ["All"] + list(locations))
    if selected_location != "All":
        df_filtered = df_filtered[df_filtered["location"] == selected_location]

# -- Weather Type Filter (if available)
if "weather_main" in df_filtered.columns and df_filtered["weather_main"].nunique() > 1:
    weather_types = df_filtered["weather_main"].unique()
    selected_weather = st.sidebar.selectbox("🌤️ Filter by Weather Type", ["All"] + list(weather_types))
    if selected_weather != "All":
        df_filtered = df_filtered[df_filtered["weather_main"] == selected_weather]

# -- Show data summary
st.sidebar.subheader("📊 Summary")
st.sidebar.metric("Total Records", len(df_filtered))
if "conv_temp" in df_filtered.columns:
    st.sidebar.metric("Avg Temperature", f"{df_filtered['conv_temp'].mean():.1f}°C")

# -- Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📋 Filtered Weather Data")
    display_columns = ["datetime", "conv_temp"]
    if "weather_main" in df_filtered.columns:
        display_columns.extend(["weather_main", "weather_description"])
    if "location" in df_filtered.columns:
        display_columns.append("location")
    
    st.dataframe(df_filtered[display_columns].sort_values("datetime"), use_container_width=True)

with col2:
    st.subheader("ℹ️ Database Info")
    db_config = load_db_env()
    st.write(f"**Host:** {db_config['DB_HOST']}:{db_config['DB_PORT']}")
    st.write(f"**Database:** {db_config['DB_NAME']}")
    st.write(f"**Total records:** {len(df)}")
    st.write(f"**Date range:** {df['datetime'].min().strftime('%Y-%m-%d')} to {df['datetime'].max().strftime('%Y-%m-%d')}")

# -- Display Weather Conditions with Icons
st.subheader("🌤️ Weather Conditions with Icons")

weather_icon_map = {
    "Clear": "https://img.icons8.com/emoji/96/000000/sun-emoji.png",
    "Clouds": "https://img.icons8.com/emoji/96/000000/cloud-emoji.png",
    "Rain": "https://img.icons8.com/emoji/96/000000/cloud-with-rain-emoji.png",
    "Snow": "https://img.icons8.com/emoji/96/000000/snowflake-emoji.png",
    "Thunderstorm": "https://img.icons8.com/emoji/96/000000/cloud-with-lightning-and-rain-emoji.png",
    "Drizzle": "https://img.icons8.com/emoji/96/000000/cloud-with-rain-emoji.png",
    "Mist": "https://img.icons8.com/emoji/96/000000/fog-emoji.png",
    "Fog": "https://img.icons8.com/emoji/96/000000/fog-emoji.png"
}

# Display recent weather entries
for _, row in df_filtered.head(10).iterrows():  # Show first 10 entries
    col1, col2, col3, col4 = st.columns([2, 1, 2, 3])
    with col1:
        st.write(row["datetime"].strftime("%Y-%m-%d %H:%M"))
    with col2:
        icon_url = weather_icon_map.get(row.get("weather_main", "Unknown"), None)
        if icon_url:
            st.image(icon_url, width=50)
    with col3:
        if "conv_temp" in row:
            st.metric(label="Temp (°C)", value=round(row["conv_temp"], 1))
    with col4:
        if "weather_description" in row:
            st.caption(row["weather_description"].capitalize())
        if "location" in row:
            st.caption(f"📍 {row['location']}")

# -- Temperature Line Chart
if "conv_temp" in df_filtered.columns:
    st.subheader("📈 Temperature Over Time")
    if not df_filtered.empty:
        chart_df = df_filtered[["datetime", "conv_temp"]].set_index("datetime").sort_index()
        st.line_chart(chart_df)

# -- Refresh button
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()