# DocuMind — Django RAG Web App

A Django web application that lets a user upload PDFs, index their content with LangChain + FAISS, and ask questions answered by Google Gemini using the retrieved document passages.

## Features

- Django server-rendered web UI, responsive CSS, and chat history.
- Upload up to five PDFs at a time (15 MB per PDF; ten PDFs per browser-session workspace).
- PDF text extraction with `PyPDFLoader`.
- Chunking with `RecursiveCharacterTextSplitter` (1,000-character chunks, 150-character overlap by default).
- Text embeddings through `gemini-embedding-001`.
- FAISS local vector index saved on disk and reused between questions.
- Retrieval of the four most similar chunks followed by answer generation with a Gemini Flash model.
- Display of source filename, page number, and retrieved excerpt for each answer.
- Browser-session workspace isolation: documents, indexes, and chat history are namespaced per session.
- CSRF protection, upload extension/signature/size checks, and document deletion with index rebuilding.

> This is a local development / learning MVP, not a fully production-hardened multi-tenant service. Read the security notes below before public deployment.

## Architecture

```text
PDF upload
   │
   ▼
Django view ──► PyPDFLoader ──► RecursiveCharacterTextSplitter
                                      │
                                      ▼
                           Gemini text embeddings
                                      │
                                      ▼
                               FAISS index
                                      │
          user question ─────────────┘
                │
                ▼
        FAISS similarity search (k=4)
                │
                ▼
   retrieved chunks + source/page metadata
                │
                ▼
    LangChain prompt → Gemini chat model
                │
                ▼
       answer + expandable source excerpts
```

### Important distinction

FAISS retrieves candidate document chunks. Gemini generates the answer. LangChain connects the steps; the model is explicitly prompted to use retrieved passages and to say when the passages do not contain the answer. Prompting does not guarantee perfect factuality, so always inspect the source excerpts.

## Requirements

- Python 3.13 (the project pins the supported minor series in `.python-version`).
- `uv` installed.
- A Google AI Studio API key with access to the configured Gemini models.
- Windows x86-64, Linux, or macOS environment with a compatible `faiss-cpu` wheel. If `uv sync` cannot resolve/install FAISS on your platform, see the platform notes at the bottom.

## Setup on Windows PowerShell

### 1. Open the project folder

```powershell
cd path\to\rag_django_app
```

### 2. Create your environment and install dependencies

```powershell
uv sync
```

This creates a virtual environment and installs dependencies from `pyproject.toml`. `uv.lock` can be generated locally with `uv lock` and committed to pin exact resolved versions.

### 3. Configure environment variables

```powershell
Copy-Item .env.example .env
```

Open `.env` and set your real API key:

```dotenv
GOOGLE_API_KEY=your_real_google_ai_studio_key
GEMINI_CHAT_MODEL=gemini-3.8-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
DJANGO_SECRET_KEY=use-a-long-random-value-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
```

Get your API key from [Google AI Studio](https://aistudio.google.com/). Never commit `.env` to GitHub.

The chat model is configurable. If `gemini-3.8-flash` is not available to your API account, change `GEMINI_CHAT_MODEL` to a current model that your account can access. The embedding model is configured separately.

### 4. Create the database tables

```powershell
uv run python manage.py migrate
```

### 5. Start the development server

```powershell
uv run python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

### 6. Use the application

1. Upload one or more text-based PDFs from the left panel.
2. Wait for the indexing confirmation; it reports extracted pages and searchable chunks.
3. Ask a question in the chat panel.
4. Expand **retrieved sources** below the answer to inspect the passages FAISS returned.
5. Remove a PDF from the sidebar to rebuild the index without that document.

The first upload makes embedding API requests and can take a while. Each question makes an embedding request for the query and a Gemini chat request.

## Project structure

```text
rag_django_app/
├── manage.py
├── pyproject.toml
├── .env.example
├── ragproject/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
└── documents/
    ├── models.py          # uploaded PDFs and chat history
    ├── views.py           # Django request handling and session isolation
    ├── services.py        # LangChain + FAISS + Gemini pipeline
    ├── urls.py
    ├── migrations/
    ├── templates/documents/
    └── static/documents/
```

## How the RAG pipeline works

1. **Load:** `PyPDFLoader` extracts text and page metadata from each PDF.
2. **Chunk:** `RecursiveCharacterTextSplitter` divides text into overlapping chunks.
3. **Embed:** `GoogleGenerativeAIEmbeddings` converts chunks to vectors.
4. **Index:** `FAISS.from_documents` creates a searchable index; it is saved under `private_rag_data/` for each session workspace.
5. **Retrieve:** the user question is embedded and FAISS returns up to four similar chunks.
6. **Generate:** the retrieved text, filename, and page number are placed in a prompt sent to the configured Gemini chat model.
7. **Inspect:** the answer is displayed with the source passages used as context.

## Configuration

Variables can be changed in `.env`:

| Variable | Default | Purpose |
|---|---|---|
| `GOOGLE_API_KEY` | none | API authentication |
| `GEMINI_CHAT_MODEL` | `gemini-3.8-flash` | Answer-generation model |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-001` | Embedding model |
| `DJANGO_SECRET_KEY` | development fallback | Session/CSRF signing; set a strong key before deployment |
| `DJANGO_DEBUG` | `True` | Django debug mode |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Allowed hostnames |

Chunk settings, upload limits, and retrieval `k` are configured in `ragproject/settings.py`.

## Troubleshooting

### `GOOGLE_API_KEY is not configured`

Check that `.env` is in the same directory as `manage.py`, and that it contains `GOOGLE_API_KEY=...`. Restart the Django process after changing environment values.

### Model not found / permission denied

Confirm that the model name in `.env` is currently available to your Google AI Studio account. Change `GEMINI_CHAT_MODEL` if needed. Embedding and chat model names are independent.

### PDF uploaded, but no readable text was extracted

This starter uses text extraction, not OCR. Scanned/image-only PDFs need an OCR process before chunking. Some protected, malformed, or unusual PDFs may also fail to load.

### FAISS package cannot install

FAISS wheels are platform-specific. Use a supported Python/platform combination and consult the `faiss-cpu` package page. On Windows, use a 64-bit Python installation. If your target deployment platform has no compatible wheel, use a Linux environment/container or choose a supported vector store for that platform.

### Answers are wrong

Expand the retrieved sources first. If the relevant passage wasn't retrieved, investigate extraction, chunking, embeddings, and retrieval. If the correct passage was retrieved but the answer is incorrect, investigate prompt/context construction and generation. RAG does not automatically guarantee correctness.

### Need a clean reset

Stop the server, back up anything you need, and remove `db.sqlite3`, `media/`, and `private_rag_data/`; then run `uv run python manage.py migrate` again. This deletes local uploads, indexes, chat history, and the local database.

## Security and deployment notes

- The app isolates workspaces by browser session, not by verified user account. It is suitable for a single-user learning MVP or controlled demo; it does **not** implement login, account-based ownership, rate limiting, abuse monitoring, or production retention policies.
- Uploaded PDFs and FAISS indexes are stored locally. Do not expose the upload directory or `private_rag_data/` as public static/media files.
- The index loader uses LangChain's `allow_dangerous_deserialization=True`, because FAISS's persisted document mapping contains a pickle. This path is only for indexes generated by this app. Never load user-provided or otherwise untrusted index files.
- PDF upload checks are a baseline, not a complete malware/document parser security boundary. Add stricter content inspection, quotas, rate limits, and background indexing jobs before public deployment.
- Extracted document text is sent to Google's embedding API; retrieved passages are sent to the configured Gemini chat model. Do not upload confidential data unless your privacy and data-processing requirements permit that transfer.
- For production: set `DJANGO_DEBUG=False`, use a new random `DJANGO_SECRET_KEY`, configure `DJANGO_ALLOWED_HOSTS`, enforce HTTPS, use persistent private storage, add authentication/authorization, configure proper logging, and run Django's deployment checks. SQLite and local FAISS storage are starter choices; multi-instance deployment requires a shared/persistent storage strategy and coordination around index updates.
- CSS loads DM Sans / Manrope / DM Mono from Google Fonts when internet access is available; the app remains functional without those fonts.
# cse222rag-proj
