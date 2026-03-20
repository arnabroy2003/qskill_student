import pandas as pd
from supabase import create_client

# 1. Supabase Connection
url = "https://rithbuogcwvjmzqoyrcj.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJpdGhidW9nY3d2am16cW95cmNqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzgzNTE5NSwiZXhwIjoyMDg5NDExMTk1fQ.PxESV4VIk9WHR6SMrcoK9HQPArsOzNG6dlmyDc5DZS8" # Database settings > API theke service_role key ta nio
supabase = create_client(url, key)

# 2. Load CSV Data
# Tomar file name 'dummy.xlsx - Sheet1.csv' hole setai dao
df = pd.read_excel('dummy.xlsx')

# Column names cleaning (space thakle remove korbe)
df.columns = df.columns.str.strip()

# --- STEP A: PROFILES TABLE FILLUP ---
# Unique email bar koro (jekhane email-i primary identity)
unique_users = df[['Name', 'Email']].drop_duplicates(subset=['Email'])

print(f"Total Unique Students: {len(unique_users)}")

for _, row in unique_users.iterrows():
    # upsert dile jodi data age theke thake, tobe update hobe, na thakle insert hobe
    supabase.table('profiles').upsert({
        'full_name': row['Name'],
        'email': row['Email']
    }, on_conflict='email').execute()

# --- STEP B: DOMAINS TABLE FILLUP ---
# Unique domains bar koro
unique_domains = df['Domain'].unique()
for d_name in unique_domains:
    supabase.table('domains').upsert({
        'domain_name': d_name.strip()
    }, on_conflict='domain_name').execute()

# --- STEP C: ENROLLMENTS TABLE (MAPPING) ---
# Database theke notun generate howa IDs gulo tule ana mapping er jonno
all_profiles = supabase.table('profiles').select('id, email').execute().data
all_domains = supabase.table('domains').select('id, domain_name').execute().data

# Fast lookup dictionary banano
email_to_id = {p['email']: p['id'] for p in all_profiles}
name_to_domain_id = {d['domain_name']: d['id'] for d in all_domains}

enrollment_entries = []

for _, row in df.iterrows():
    # Student ID generate kora ba CSV theke neya
    # Jodi CSV-te 'Student ID' column thake, seta use koro
    e_data = {
        'user_id': email_to_id[row['Email']],
        'domain_id': name_to_domain_id[row['Domain'].strip()],
        'student_domain_id': row['Student ID'] # 'Student ID' column name check kore nio
    }
    enrollment_entries.append(e_data)

# Bulk insert (9000 data chunk wise insert kora safe)
chunk_size = 500
for i in range(0, len(enrollment_entries), chunk_size):
    chunk = enrollment_entries[i:i + chunk_size]
    supabase.table('enrollments').insert(chunk).execute()
    print(f"Inserted {i + len(chunk)} records...")

print("Database population complete!")