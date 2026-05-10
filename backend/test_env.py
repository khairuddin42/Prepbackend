#!/usr/bin/env python3
"""
Test script to verify .env file loading from project root
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root (same logic as main.py)
BASE_DIR = Path(__file__).resolve().parent  # points to backend/
PROJECT_ROOT = BASE_DIR.parent  # points to ai-prep-tutor/
ENV_PATH = PROJECT_ROOT / ".env"

print("=== .env File Loading Test ===")
print(f"Current working directory: {os.getcwd()}")
print(f"Backend directory: {BASE_DIR}")
print(f"Project root directory: {PROJECT_ROOT}")
print(f".env file path: {ENV_PATH}")
print(f".env file exists: {ENV_PATH.exists()}")

# Load the .env file
load_dotenv(ENV_PATH)

print("\n=== Environment Variables ===")
supabase_url = os.getenv("SUPABASE_URL")
supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")

print(f"SUPABASE_URL: {supabase_url}")
print(f"SUPABASE_SERVICE_KEY: {supabase_service_key[:10]}..." if supabase_service_key else "SUPABASE_SERVICE_KEY: None")
print(f"SUPABASE_ANON_KEY: {supabase_anon_key[:10]}..." if supabase_anon_key else "SUPABASE_ANON_KEY: None")

print("\n=== Pydantic Settings Test ===")
try:
    from app.config import settings
    print(f"Settings SUPABASE_URL: {settings.SUPABASE_URL}")
    print(f"Settings SUPABASE_SERVICE_KEY: {settings.SUPABASE_SERVICE_KEY[:10]}...")
    print(f"Settings SUPABASE_ANON_KEY: {settings.SUPABASE_ANON_KEY[:10]}...")
    
    # Check if values are still placeholders
    if "your-project" in settings.SUPABASE_URL:
        print("\n❌ WARNING: Still using placeholder values!")
    else:
        print("\n✅ SUCCESS: Real Supabase values detected!")
        
except Exception as e:
    print(f"Error loading settings: {e}")
