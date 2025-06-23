from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os

# Add the weather folder to the Python path
sys.path.append('/Users/apple/Desktop/PORTFOLIO/weather')

from weather_pipeline_secure import main

def run_weather_pipeline():
    main()

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'weather_pipeline_dag',
    default_args=default_args,
    description='DAG to run the weather data pipeline daily',
    schedule_interval='0 0 * * *',  # Daily at midnight
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:

    run_pipeline_task = PythonOperator(
        task_id='run_weather_pipeline',
        python_callable=run_weather_pipeline,
    ) 