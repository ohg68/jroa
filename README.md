# PDF Catalog Extractor

Web application to extract products from PDF catalogs using AI (Claude API) and export them to Odoo-compatible CSV format.

## Features

- Upload PDF product catalogs
- AI-powered product extraction (text + vision for scanned PDFs)
- Dashboard with processing metrics
- Editable product table with inline editing
- Filter products by review status, missing prices
- PDF optimization (reduce file size)
- Reprocess catalogs
- Export to Odoo-compatible CSV (global or per catalog)
- Odoo CSV fields: `name`, `default_code`, `list_price`, `categ_id`, `description_sale`

## Tech Stack

- **Frontend**: React + TypeScript + Vite + Tailwind CSS
- **Backend**: Python + FastAPI
- **Database**: SQLite (via SQLAlchemy)
- **AI**: Anthropic Claude API
- **PDF**: PyMuPDF (fitz)

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Anthropic API key

### Backend

```bash
cd backend
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-api-key-here"
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server runs on `http://localhost:5173` and proxies API requests to the backend on port 8000.

## PDF Storage

PDFs are stored on the **local filesystem** in the `backend/uploads/` directory. The database stores file paths (not file content). This keeps the DB lightweight and allows direct file system operations for PDF optimization.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/catalogs/dashboard` | Dashboard metrics |
| POST | `/api/catalogs/upload` | Upload PDF catalog |
| GET | `/api/catalogs/` | List all catalogs |
| GET | `/api/catalogs/{id}` | Get catalog details |
| POST | `/api/catalogs/{id}/reprocess` | Reprocess catalog |
| POST | `/api/catalogs/{id}/optimize` | Optimize PDF |
| DELETE | `/api/catalogs/{id}` | Delete catalog |
| DELETE | `/api/catalogs/` | Delete all catalogs |
| GET | `/api/products/` | List products (with filters) |
| PUT | `/api/products/{id}` | Update product |
| DELETE | `/api/products/{id}` | Delete product |
| GET | `/api/export/csv` | Export all products CSV |
| GET | `/api/export/csv/{catalog_id}` | Export catalog CSV |
