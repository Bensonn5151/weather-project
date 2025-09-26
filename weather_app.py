import streamlit as st
import pandas as pd

# Load data
@st.cache_data
def load_weather_data():
    return pd.read_csv("weather_forecast_json.csv", parse_dates=["datetime"])

df = load_weather_data()

st.title("Weather Data Dashboard")

# Date filter
date_range = st.date_input(
    "Select date range",
    [df['datetime'].min(), df['datetime'].max()]
)
if len(date_range) == 2:
    df = df[(df['datetime'] >= pd.to_datetime(date_range[0])) & (df['datetime'] <= pd.to_datetime(date_range[1]))]

# Location filter (if you have a 'location' column)
if 'location' in df.columns:
    location = st.selectbox("Select location", df['location'].unique())
    df = df[df['location'] == location]

# Show data
st.write("Filtered Data", df.head())

# Line chart (e.g., temperature over time)
if 'conv_temp' in df.columns:
    st.line_chart(df.set_index('datetime')['conv_temp'])

# More visualizations
if 'precipitation' in df.columns:
    st.bar_chart(df.set_index('datetime')['precipitation'])

# Map (if you have lat/lon)
if {'latitude', 'longitude'}.issubset(df.columns):
    st.map(df[['latitude', 'longitude']])