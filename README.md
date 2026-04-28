# DataSmith AI - Tender Proposal Automation

DataSmith AI is a full-stack document intelligence system that helps companies process tender documents, extract proposal formats, retrieve relevant company knowledge, and generate structured tender proposal drafts. The project combines a FastAPI backend, a React frontend, Supabase storage/database, Qdrant vector search, Cohere embeddings, and a LangGraph-based proposal generation workflow.

## Problem Statement

Tender response preparation is usually slow, repetitive, and error-prone. Teams need to read long PDF tender documents, identify technical and financial proposal formats, compare requirements against company knowledge, fill tables, and produce a submission-ready document. This becomes harder when tenders contain complex tables, annexures, BOQs, multiple sections, or mixed document formats.

This project solves that problem by building an automated tender proposal assistant that can:

- Onboard a company with its knowledge base and proposal template.
- Upload and parse tender PDF documents.
- Detect whether a tender contains its own proposal response format.
- Extract, chunk, embed, and store tender content for semantic retrieval.
- Retrieve relevant tender and company context for each proposal section.
- Generate a proposal document in DOCX format.
- Let the frontend guide users through onboarding, upload, processing, review, and export.

## Solution Overview

The system works as a pipeline:

1. A company registers or logs in through the frontend.
2. The company uploads its knowledge base and proposal template during onboarding.
3. The backend stores files in Supabase and embeds company knowledge into Qdrant.
4. The user uploads a tender PDF.
5. The backend parses the PDF, extracts sections and tables, detects proposal formats, chunks the tender, and stores embeddings.
6. The frontend checks whether the uploaded tender has a built-in proposal format.
7. The user generates a proposal using either the tender format or the onboarded company template.
8. A LangGraph workflow retrieves relevant context, generates section content, validates output, and compiles a downloadable DOCX proposal.

## Tech Stack

### Frontend

- React
- Vite
- JavaScript
- CSS
- Browser localStorage for workflow state
- Fetch API for backend communication

### Backend

- Python
- FastAPI
- Uvicorn
- python-multipart for file upload forms
- bcrypt for password hashing
- python-docx for DOCX parsing and generation
- ReportLab for basic DOCX to PDF conversion
- PyMuPDF for PDF extraction
- Docling for document parsing
- LangGraph for proposal generation flow
- OpenAI-compatible client pointed at local Ollama

### Storage, Retrieval, and AI Services

- Supabase database and object storage
- Qdrant vector database
- Cohere multilingual embeddings
- Ollama local LLM endpoint for generation

## Project Structure

```text
DataExtraction/
|-- api.py
|-- config.py
|-- graph.py
|-- retrieval.py
|-- documents/
|-- uploaded_pdfs/
|-- extracted_proposals/
|-- generated_proposal.docx
|-- agents/
|   |-- graph.py
|   |-- state.py
|   |-- nodes/
|       |-- load_sections_node.py
|       |-- process_section_node.py
|       |-- validate_section_node.py
|       |-- generate_section_node.py
|       |-- check_next_section_node.py
|       |-- compile_proposal_node.py
|-- pipeline_one/
|   |-- parsing/
|   |-- chunking/
|   |-- embedding/
|   |-- retrieval/
|   |-- proposal/
|   |-- utils/
|-- frontend/
|   |-- index.html
|   |-- package.json
|   |-- src/
|   |   |-- main.jsx
|   |   |-- api.js
|   |   |-- styles.css
|   |-- legacy-static/
|   |-- dist/
```

## Backend Structure

### `api.py`

Main FastAPI application. It exposes the backend API used by the React frontend.

Important endpoints:

- `POST /login`  
  Authenticates an existing company using email and password.

- `POST /onboard-company`  
  Registers a company, stores company metadata in Supabase, uploads the knowledge base and proposal template, parses the knowledge base, chunks it, embeds it, and stores vectors in Qdrant.

- `POST /upload-pdf`  
  Uploads a tender PDF, stores it, parses the document, detects proposal sections, extracts proposal format if available, chunks the full tender, embeds it, and stores tender metadata in Supabase.
  Checks whether the uploaded tender contains a proposal format and whether that format includes tables.

- `POST /generate-proposal`  
  Generates and returns `generated_proposal.docx` using either the tender response format or the company template.

### `config.py`

Stores service configuration values used by the generation and retrieval pipeline.

For production, secrets should be moved to environment variables and never committed to source control.

### `pipeline_one/parsing/`

Responsible for PDF parsing and normalization.

Key files:

- `pipeline.py`: Entry point for parsing PDFs into a structured `ParsedDocument`.
- `docling_parser.py`: Uses Docling and PyMuPDF to extract structured text, sections, links, and tables.
- `normaliser.py`: Converts raw parser output into the internal parsed document model.
- `models/parsed_document.py`: Data structures for parsed documents, sections, and tables.

### `pipeline_one/chunking/`

Responsible for converting parsed documents into retrieval-ready chunks.

Key files:

- `pipeline.py`: Entry point for chunking.
- `chunker.py`: Splits large text sections into overlapping chunks and keeps tables atomic.
- `metadata_builder.py`: Adds metadata such as document id, page numbers, section title, chunk type, and language.
- `section_walker.py`: Traverses nested document sections.
- `models/chunk_model.py`: Chunk data model.

### `pipeline_one/embedding/`

Responsible for vector generation and storage.

Key files:

- `pipeline.py`: Connects to Qdrant, creates collections, embeds chunks, and stores vectors.
- `cohere_embedder.py`: Uses Cohere `embed-multilingual-v3.0` for document and query embeddings.
- `qdrant_store.py`: Creates Qdrant collections and upserts chunk vectors.

### `pipeline_one/retrieval/`

Responsible for semantic search during proposal generation.

Key file:

- `retrieve_context.py`: Retrieves matching tender chunks and company knowledge from Qdrant, expands neighboring tender chunks, combines context, and removes duplicates.

### `pipeline_one/proposal/`

Responsible for finding and converting proposal response formats.

Key files:

- `detector.py`: Detects proposal-related sections using keywords such as annexure, BOQ, financial proposal, technical proposal, bid format, and price bid.
- `extractor.py`: Extracts proposal-related pages from the original tender PDF.
- `json_builder.py`: Converts extracted proposal sections and tables into JSON used by the generation workflow.

### `pipeline_one/utils/`

Utility modules.

Key file:

- `supabase_client.py`: Loads Supabase credentials, creates the Supabase client, and uploads files to Supabase storage buckets.

### `agents/`

Contains the LangGraph proposal generation workflow.

Key files:

- `graph.py`: Builds the LangGraph state machine.
- `state.py`: Defines the proposal generation state.
- `nodes/load_sections_node.py`: Loads sections or table rows from the proposal format.
- `nodes/process_section_node.py`: Selects the current section or table row.
- `nodes/validate_section_node.py`: Decides whether a section should be skipped or generated.
- `nodes/generate_section_node.py`: Retrieves relevant context and generates proposal content.
- `nodes/check_next_section_node.py`: Checks whether more sections remain.
- `nodes/compile_proposal_node.py`: Builds the final DOCX document and preserves table structure when in table mode.

## Frontend Structure

### `frontend/src/main.jsx`

Main React application. It contains the full single-page workflow:

- Home and overview
- Company onboarding
- Tender upload
- Processing status
- Dashboard
- Proposal generation
- Review
- Export

The app uses hash-based routing and stores workflow state in `localStorage` so the user can continue across page refreshes.

### `frontend/src/api.js`

Central API client for the frontend. It reads backend configuration from Vite environment variables and exposes helper functions for:

- `loginCompany`
- `onboardCompany`
- `uploadPdf`
- `checkProposalFormat`
- `generateProposal`
- `normalizeCompanySession`

### `frontend/src/styles.css`

Application styling for the React interface.

### `frontend/legacy-static/`

Older static HTML, CSS, JavaScript, and Supabase schema files preserved for reference.

### `frontend/dist/`

Production build output generated by Vite.

## Runtime Folders

- `documents/`: Sample tender documents and parsed outputs.
- `uploaded_pdfs/`: Local copies of uploaded tender PDFs.
- `extracted_proposals/`: Extracted proposal-format PDFs generated from uploaded tenders.
- `generated_proposal.docx`: Latest generated proposal output.
- `frontend/node_modules/`: Installed frontend dependencies.
- `frontend/dist/`: Built frontend assets.

## Environment Variables

Create a backend `.env` file in the project root:

```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_role_or_backend_key
COHERE_KEY=your_cohere_api_key
QDRANT_URL=your_qdrant_cluster_url
QDRANT_KEY=your_qdrant_api_key
GROQ_API_KEY=optional_if_used
NVIDIA_API_KEY=optional_if_used
```

Create a frontend `.env` file inside `frontend/`:

```env
VITE_BACKEND_BASE_URL=http://localhost:8000
VITE_LOGIN_ENDPOINT=/login
VITE_ONBOARD_COMPANY_ENDPOINT=/onboard-company
VITE_UPLOAD_PDF_ENDPOINT=/upload-pdf
VITE_GENERATE_PROPOSAL_ENDPOINT=/generate-proposal
VITE_CHECK_PROPOSAL_FORMAT_ENDPOINT=/check-proposal-format
```

Optional frontend Supabase values can be configured only if a public anon key and proper Row Level Security policies are available:

```env
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
VITE_SUPABASE_COMPANY_TABLE=company_profiles
VITE_SUPABASE_EMAIL_COLUMN=contact_email
```

## Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer
- npm
- Supabase project with required tables and storage buckets
- Qdrant Cloud cluster
- Cohere API key
- Ollama running locally for proposal generation

The generation node currently calls an OpenAI-compatible local endpoint:

```text
http://localhost:11434/v1
```

Make sure Ollama is running and the configured model is available before generating proposals.

## Backend Setup

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```powershell
pip install fastapi uvicorn python-multipart supabase python-dotenv bcrypt python-docx reportlab pymupdf qdrant-client cohere openai langgraph docling langdetect requests
```

Start the backend:

```powershell
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

The backend will run at:

```text
http://localhost:8000
```

FastAPI interactive API documentation is available at:

```text
http://localhost:8000/docs
```

## Frontend Setup

Open a new terminal and run:

```powershell
cd frontend
npm install
npm run dev
```

The frontend will run at:

```text
http://localhost:5173
```

To build the frontend for production:

```powershell
cd frontend
npm run build
```

To preview the production build:

```powershell
cd frontend
npm run preview
```

The preview server runs at:

```text
http://localhost:4173
```

## Supabase Requirements

The backend expects Supabase to provide:

- A `companies` table for company profile, contact, password hash, knowledge base URL, and proposal template URL.
- A `tenders` table for uploaded tender metadata, document id, proposal detection status, and extracted proposal JSON.
- A `company-documents` storage bucket for company knowledge bases and proposal templates.
- A `tender-documents` storage bucket for uploaded tender PDFs.

The frontend legacy folder includes `frontend/legacy-static/supabase_schema.sql`, which can be used as a reference for database setup.

## API Reference

### Login

```http
POST /login
Content-Type: multipart/form-data
```

Fields:

- `email`
- `password`

Returns company session details.

### Onboard Company

```http
POST /onboard-company
Content-Type: multipart/form-data
```

Fields:

- `company_name`
- `industry`
- `contact_email`
- `contact_phone`
- `password`
- `knowledge_base`
- `proposal_template`

Returns company id and uploaded file paths.

### Upload Tender PDF

```http
POST /upload-pdf
Content-Type: multipart/form-data
```

Fields:

- `company_id`
- `file`

Returns parsing, chunking, embedding, and proposal-format detection results.

### Check Proposal Format

```http
GET /check-proposal-format?doc_id=your_document_id
```

Returns whether the tender contains a detected proposal format.

### Generate Proposal

```http
POST /generate-proposal
Content-Type: multipart/form-data
```

Fields:

- `company_id`
- `doc_id`
- `format_source`

`format_source` can be:

- `tender`: Use proposal format extracted from the tender PDF.
- `template`: Use the company proposal template uploaded during onboarding.

Returns a downloadable DOCX file.

## End-to-End Workflow

1. Start Supabase, Qdrant, and Ollama requirements.
2. Start the FastAPI backend on port `8000`.
3. Start the Vite frontend on port `5173`.
4. Open the frontend in the browser.
5. Onboard a company by uploading a knowledge base and proposal template.
6. Upload a tender PDF.
7. Let the backend parse, chunk, embed, and detect proposal format.
8. Choose whether to generate using tender format or onboarded template.
9. Generate the proposal.
10. Review and export the generated DOCX file.

## Production Notes

- Move all hardcoded credentials out of source files and into environment variables.
- Do not commit `.env`, generated proposals, uploaded PDFs, extracted proposal PDFs, `node_modules`, or build artifacts.
- Add a backend `requirements.txt` or `pyproject.toml` for reproducible deployments.
- Add authentication/session tokens for production instead of relying only on company id stored in browser state.
- Add validation for uploaded file size, type, and scan status.
- Configure CORS origins for deployed frontend domains only.
- Use secure Supabase Row Level Security policies.
- Add logging, monitoring, retries, and background jobs for long-running parsing and embedding tasks.
- Store generated proposal outputs with unique names to avoid overwriting `generated_proposal.docx`.

## Authors

Raman Gandewar  
Prathamesh Ghalsasi  
Divij Gujarathi
