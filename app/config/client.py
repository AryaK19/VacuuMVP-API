from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

# Get Supabase credentials from environment variables
supabase_url = "https://phphzmeqmkbtezrqjjtv.supabase.co"
supabase_key = os.getenv("DB_API_KEY")

# Initialize Supabase client
supabase: Client = create_client(supabase_url, supabase_key)

def get_supabase_client() -> Client:
    """
    Returns the Supabase client instance
    """
    return supabase
