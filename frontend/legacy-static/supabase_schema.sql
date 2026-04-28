create table if not exists company_profiles (
  id uuid primary key default gen_random_uuid(),
  auth_user_id uuid unique references auth.users(id) on delete cascade,
  company_name text,
  industry text,
  contact_email text,
  contact_phone text,
  knowledge_base_url text,
  proposal_template_url text,
  created_at timestamptz default now()
);
