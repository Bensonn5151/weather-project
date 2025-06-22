# Secure Setup Guide for Weather Data Pipeline

## Overview
This guide shows you how to secure your weather data pipeline by removing sensitive credentials from the notebook and using environment variables instead.

## Security Issues in Original Notebook

The original notebook contains sensitive information:
- **API Key**: `b3e33c27add19193791ed2e5e9b78444` (OpenWeatherMap)
- **Database Password**: `bens` (PostgreSQL)

## Solution: Environment Variables

### Step 1: Install Required Packages

```bash
pip install python-dotenv
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

### Step 2: Create Environment File

1. Copy the example configuration:
```bash
cp config_example.env .env
```

2. Edit `.env` file with your actual credentials:
```bash
# OpenWeatherMap API Configuration
OPENWEATHER_API_KEY=b3e33c27add19193791ed2e5e9b78444
CITY=London

# PostgreSQL Database Configuration
DB_USERNAME=postgres
DB_PASSWORD=bens
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ben

# Optional: File Path Configuration
CSV_FILE_PATH=weather_forecast_json.csv
```

### Step 3: Secure Your Credentials

**IMPORTANT**: Add `.env` to your `.gitignore` file to prevent it from being committed to version control:

```bash
echo ".env" >> .gitignore
```

### Step 4: Use the Secure Script

Instead of running the notebook, use the secure Python script:

```bash
python weather_pipeline_secure.py
```

## Alternative: Update Your Notebook

If you prefer to keep using the notebook, replace the credential cells with:

```python
# Cell 1: Load environment variables
import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration from environment variables
API_KEY = os.getenv('OPENWEATHER_API_KEY')
CITY = os.getenv('CITY', 'London')

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
```

## Security Benefits

1. **No Hardcoded Credentials**: Sensitive data is not in your code
2. **Environment-Specific**: Different credentials for development/production
3. **Version Control Safe**: Credentials won't be committed to Git
4. **Easy Rotation**: Change credentials without touching code
5. **Team Collaboration**: Each developer can have their own `.env` file

## Production Deployment

For production environments, consider:

1. **Secrets Management**: Use services like AWS Secrets Manager, Azure Key Vault, or HashiCorp Vault
2. **Environment Variables**: Set directly in your deployment environment
3. **Configuration Management**: Use tools like Ansible or Terraform

## Troubleshooting

### Common Issues:

1. **"Environment variable not found"**
   - Check that `.env` file exists in the same directory
   - Verify variable names match exactly

2. **"Database connection failed"**
   - Verify PostgreSQL is running
   - Check database credentials in `.env`

3. **"API key invalid"**
   - Verify your OpenWeatherMap API key is correct
   - Check if you've exceeded API limits

### Testing Your Setup:

```python
# Test script to verify environment variables
import os
from dotenv import load_dotenv

load_dotenv()

print("Environment Variables Test:")
print(f"API Key: {'✓ Set' if os.getenv('OPENWEATHER_API_KEY') else '✗ Missing'}")
print(f"DB Password: {'✓ Set' if os.getenv('DB_PASSWORD') else '✗ Missing'}")
print(f"City: {os.getenv('CITY', 'Not set')}")
```

## Portfolio Considerations

For your portfolio, you can:

1. **Include the secure script** (`weather_pipeline_secure.py`)
2. **Show the setup guide** (this file)
3. **Remove the original notebook** or clearly mark it as "development version"
4. **Document the security improvements** in your README

This demonstrates:
- Security best practices
- Production-ready code
- Environment management
- Professional development practices 