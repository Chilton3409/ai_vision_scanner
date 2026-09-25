#!/usr/bin/env python3
import os
from dotenv import load_dotenv

# Load variables out of the local .env workspace file
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
RENDER_BASE_URL = os.environ.get("RENDER_BASE_URL", "http://localhost:8000")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing critical Supabase environment configurations.")
