#!/bin/bash

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python -m venv venv
fi

# Activate virtual environment
if [ -f "venv/Scripts/activate" ]; then
    # Windows
    source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
    # Unix/Linux/Mac
    source venv/bin/activate
fi

# Install requirements
pip install -r requirements.txt

# Export environment variables from .env file
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Run the application
python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --reload


npx supabase init --force
 
# Login to Supabase
npx supabase login

# Link your project
npx supabase link --project-ref phphzmeqmkbtezrqjjtv

# Create a new migration
npx supabase migration new schema_sql
 
# Run migrations
npx supabase db push

# Fetch latest migrations
npx supabase migration fetch