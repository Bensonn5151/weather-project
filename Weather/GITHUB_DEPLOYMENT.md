# GitHub Deployment Guide - Weather Data Pipeline

## 🚨 CRITICAL: What NOT to Push to GitHub

### ❌ NEVER Push These Files:
- `.env` (contains your actual API keys and passwords)
- `weatherdatapipeline.ipynb` (contains hardcoded credentials)
- `*.csv` files (generated data files)
- Any file with your actual API keys or database passwords

### ✅ SAFE to Push These Files:
- `weather_pipeline_secure.py` (secure script)
- `config_example.env` (template only)
- `requirements.txt` (dependencies)
- `SETUP_SECURE.md` (setup guide)
- `queries.sql` (SQL queries)
- `README.md` (documentation)
- `.gitignore` (protects sensitive files)

## Step-by-Step GitHub Deployment

### Step 1: Clean Your Repository

```bash
# Remove sensitive files from tracking (if already tracked)
git rm --cached .env
git rm --cached weatherdatapipeline.ipynb
git rm --cached *.csv

# Remove from git history if they were previously committed
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch weatherdatapipeline.ipynb" \
  --prune-empty --tag-name-filter cat -- --all
```

### Step 2: Verify .gitignore is Working

```bash
# Check what files will be committed
git status

# You should NOT see these files:
# - .env
# - weatherdatapipeline.ipynb
# - *.csv files
```

### Step 3: Create Your .env File (Local Only)

```bash
# Copy the example and add your real credentials
cp config_example.env .env

# Edit .env with your actual values
nano .env  # or use your preferred editor
```

### Step 4: Commit and Push

```bash
# Add all safe files
git add .

# Commit with a descriptive message
git commit -m "Add secure weather data pipeline with environment variables

- Add secure Python script (weather_pipeline_secure.py)
- Add environment variable configuration
- Add comprehensive setup documentation
- Add SQL queries for data analysis
- Exclude sensitive files with .gitignore"

# Push to GitHub
git push origin main
```

## Repository Structure After Deployment

```
Weather/
├── .gitignore                 ✅ Safe to push
├── README.md                  ✅ Safe to push
├── requirements.txt           ✅ Safe to push
├── config_example.env         ✅ Safe to push (template only)
├── weather_pipeline_secure.py ✅ Safe to push
├── SETUP_SECURE.md            ✅ Safe to push
├── queries.sql                ✅ Safe to push
├── data_modelling_structure.md ✅ Safe to push
├── .env                       ❌ NOT pushed (contains real credentials)
├── weatherdatapipeline.ipynb  ❌ NOT pushed (contains hardcoded credentials)
├── weather_forecast_json.csv  ❌ NOT pushed (generated data)
└── weather_data_scd.csv       ❌ NOT pushed (generated data)
```

## For Portfolio Presentation

### What to Show in Your Portfolio:

1. **GitHub Repository**: Clean, professional, no sensitive data
2. **README.md**: Comprehensive documentation
3. **Secure Script**: Production-ready code
4. **Setup Guide**: Shows security knowledge
5. **SQL Queries**: Demonstrates data analysis skills

### What to Explain in Interviews:

```markdown
"I implemented a secure weather data pipeline using environment variables
to protect sensitive credentials. The pipeline extracts data from OpenWeatherMap API,
transforms it using SCD Type 2 methodology, and loads it into PostgreSQL with
complete historical tracking. I used python-dotenv for secure configuration
management and included comprehensive documentation for deployment."
```

## Security Checklist Before Pushing

- [ ] `.env` file is in `.gitignore`
- [ ] No API keys in any committed files
- [ ] No database passwords in any committed files
- [ ] `weatherdatapipeline.ipynb` is not tracked
- [ ] Generated CSV files are not tracked
- [ ] `config_example.env` contains only placeholder values

## Testing Your Deployment

### Local Test:
```bash
# Verify .env works locally
python weather_pipeline_secure.py
```

### GitHub Test:
```bash
# Clone to a new directory to test
git clone <your-repo-url> test-clone
cd test-clone/Weather

# Should fail without .env (this is good!)
python weather_pipeline_secure.py
# Expected: "OPENWEATHER_API_KEY environment variable is required"
```

## Common Mistakes to Avoid

### ❌ Don't Do This:
```bash
# Don't commit .env file
git add .env
git commit -m "Add configuration"

# Don't leave credentials in notebook
# Don't push CSV files with data
```

### ✅ Do This Instead:
```bash
# Only commit the example template
git add config_example.env
git commit -m "Add configuration template"

# Use environment variables
# Keep data files local
```

## Benefits of This Approach

1. **Security**: No credentials exposed
2. **Professional**: Production-ready code
3. **Portfolio-Ready**: Clean, documented repository
4. **Collaborative**: Others can use your code safely
5. **Maintainable**: Easy to update and deploy

## Next Steps

1. **Deploy to GitHub** following this guide
2. **Update your portfolio** with the GitHub link
3. **Document the security approach** in your resume
4. **Practice explaining** the SCD Type 2 implementation
5. **Consider adding** automated testing and CI/CD

This approach demonstrates professional development practices that employers value! 