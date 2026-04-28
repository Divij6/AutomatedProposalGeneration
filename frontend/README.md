# Datasmith AI Frontend

React + Vite frontend for the proposal generation workflow.

## Configure API URL
Edit `frontend/.env` whenever ngrok changes:

```env
VITE_BACKEND_BASE_URL=https://your-new-ngrok-url.ngrok-free.app
```

The app reads these endpoint paths from `.env`:

```env
VITE_LOGIN_ENDPOINT=/login
VITE_ONBOARD_COMPANY_ENDPOINT=/onboard-company
VITE_UPLOAD_PDF_ENDPOINT=/upload-pdf
VITE_GENERATE_PROPOSAL_ENDPOINT=/generate-proposal
VITE_CHECK_PROPOSAL_FORMAT_ENDPOINT=/check-proposal-format
```

Optional Supabase verification after login/onboarding:

```env
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
VITE_SUPABASE_COMPANY_TABLE=company_profiles
VITE_SUPABASE_EMAIL_COLUMN=contact_email
```

Keep these blank unless you have a public anon key and RLS policy that allows the read.

## Run

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## API calls implemented

- `POST /login` with `email`, `password`
- `POST /onboard-company` with `company_name`, `industry`, `contact_email`, `contact_phone`, `password`, `knowledge_base`, `proposal_template`
- `POST /upload-pdf` with `company_id`, `file`
- `GET /check-proposal-format?doc_id=...`
- `POST /generate-proposal` with `company_id`, `doc_id`, `format_source`

Old static HTML files are preserved in `frontend/legacy-static/`.
