# Financial Document Management System

A FastAPI application for financial document management with AI-powered semantic analysis using RAG (Retrieval-Augmented Generation).

## Features

- **Authentication & Authorization**: JWT-based auth with Role-Based Access Control (RBAC)
- **Document Management**: Upload, retrieve, search, and delete financial documents (invoices, reports, contracts)
- **Semantic Search (RAG)**: Vector-based document search using Qdrant + sentence-transformers
- **Reranking**: Cross-encoder reranking for improved retrieval relevance
- **Text Extraction**: Automatic text extraction from PDF, DOCX, and TXT files

## Tech Stack

- **Framework**: FastAPI
- **Database**: SQLite (async via aiosqlite) — swap for PostgreSQL in production
- **Vector DB**: Qdrant
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **Reranker**: cross-encoder/ms-marco-MiniLM-L-6-v2
- **Auth**: JWT (python-jose) + bcrypt

## Setup

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Start Qdrant (Docker)

```bash
docker run -p 6333:6333 qdrant/qdrant
```

> If Qdrant is unavailable, the app falls back to an in-memory vector store for development.

### 3. Seed default roles

```bash
python seed_roles.py
```

### 4. Run the application

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /auth/register | Register a new user |
| POST | /auth/login | User authentication |
| GET | /auth/me | Get current user info |

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /documents/upload | Upload a financial document |
| GET | /documents | Retrieve all documents |
| GET | /documents/search | Search documents by metadata |
| GET | /documents/{document_id} | Retrieve document details |
| DELETE | /documents/{document_id} | Delete a document |

### Roles & Permissions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /roles/create | Create a role |
| POST | /users/assign-role | Assign role to user |
| GET | /users/{id}/roles | Get roles assigned to user |
| GET | /users/{id}/permissions | View user permissions |

### RAG (Semantic Search)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /rag/index-document | Generate embeddings and store in vector DB |
| DELETE | /rag/remove-document/{id} | Remove document embeddings |
| POST | /rag/search | Perform semantic search |
| GET | /rag/context/{document_id} | Retrieve related document context |

## Roles & Permissions

| Role | Permissions |
|------|-------------|
| Admin | Full access |
| Analyst | Upload and edit documents, search |
| Auditor | Review documents (read-only) |
| Client | View company documents |

## RAG Pipeline

```
Document Upload
    ↓
Text Extraction (PDF/DOCX/TXT)
    ↓
Chunking (RecursiveCharacterTextSplitter)
    ↓
Embedding (all-MiniLM-L6-v2)
    ↓
Vector Storage (Qdrant)

User Query
    ↓
Query Embedding
    ↓
Vector Search (Top 20)
    ↓
Cross-Encoder Reranking
    ↓
Top 5 Most Relevant Results
```

## Example Usage

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"analyst1","email":"analyst@example.com","password":"secure123"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"analyst1","password":"secure123"}'

# Upload document (use token from login)
curl -X POST http://localhost:8000/documents/upload \
  -H "Authorization: Bearer <token>" \
  -F "title=Q4 Financial Report" \
  -F "company_name=Acme Corp" \
  -F "document_type=report" \
  -F "file=@report.pdf"

# Index document for semantic search
curl -X POST "http://localhost:8000/rag/index-document?document_id=<doc_id>" \
  -H "Authorization: Bearer <token>"

# Semantic search
curl -X POST http://localhost:8000/rag/search \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query":"financial risk related to high debt ratio","top_k":5}'
```
