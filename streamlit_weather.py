import streamlit as st
import pandas as pd
import json
from datetime import datetime
from PIL import Image
import os

# -- Load data
@st.cache_data
def load_weather_data():
    df = pd.read_csv("weather_forecast_json.csv", parse_dates=["datetime"])
    
    # Parse weather info JSON column
    df["weather_main"] = df["weather_info"].apply(lambda x: json.loads(x)["weather"])
    df["weather_description"] = df["weather_info"].apply(lambda x: json.loads(x)["description"])
    
    return df

df = load_weather_data()

st.set_page_config(page_title="Weather Dashboard", layout="wide")
st.title("🌦️ Weather Dashboard")

# -- Date Range Filter
date_range = st.date_input(
    "📅 Select Date Range",
    [df["datetime"].min(), df["datetime"].max()]
)

if len(date_range) == 2:
    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    df = df[(df["datetime"] >= start_date) & (df["datetime"] <= end_date)]

# -- Location Filter (optional)
if "location" in df.columns:
    location = st.selectbox("📍 Select Location", df["location"].unique())
    df = df[df["location"] == location]

# -- Show data
st.subheader("📋 Filtered Weather Data")
st.dataframe(df[["datetime", "conv_temp", "weather_main", "weather_description"]].sort_values("datetime"), use_container_width=True)

# -- Display Weather Conditions with Icons
st.subheader("🌤️ Weather Conditions with Icons")

weather_icon_map = {
    "Clear": "https://img.icons8.com/emoji/96/000000/sun-emoji.png",
    "Clouds": "https://img.icons8.com/emoji/96/000000/cloud-emoji.png",
    "Rain": "https://img.icons8.com/emoji/96/000000/cloud-with-rain-emoji.png"
    # You can add more (e.g. Snow, Thunderstorm, etc.)
}

for _, row in df.iterrows():
    col1, col2, col3 = st.columns([2, 1, 4])
    with col1:
        st.write(row["datetime"].strftime("%Y-%m-%d %H:%M"))
    with col2:
        icon_url = weather_icon_map.get(row["weather_main"], None)
        if icon_url:
            st.image(icon_url, width=50)
    with col3:
        st.metric(label="Temp (°C)", value=round(row["conv_temp"], 1))
        st.caption(row["weather_description"].capitalize())

# -- Temperature Line Chart
if "conv_temp" in df.columns:
    st.subheader("📈 Temperature Over Time")
    chart_df = df[["datetime", "conv_temp"]].set_index("datetime")
    st.line_chart(chart_df)

# -- Precipitation Bar Chart
if "precipitation" in df.columns:
    st.subheader("🌧️ Precipitation Over Time")
    st.bar_chart(df.set_index("datetime")["precipitation"])

# -- Map view (if coordinates available)
if {"latitude", "longitude"}.issubset(df.columns):
    st.subheader("🗺️ Weather Location Map")
    st.map(df[["latitude", "longitude"]])
