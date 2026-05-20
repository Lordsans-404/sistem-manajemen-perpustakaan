# supabase_client.py
from supabase import create_client, Client
from decouple import config

SUPABASE_URL = config('SUPABASE_URL')
SUPABASE_KEY = config('SUPABASE_ANON_KEY')  # gunakan service_role key untuk operasi server-side

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
