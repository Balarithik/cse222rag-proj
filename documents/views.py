"""Web views for uploading PDFs and chatting with the RAG pipeline."""
import hashlib
import hmac
import logging
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import QuestionForm
from .models import ChatMessage, UploadedDocument
from .services import answer_from_documents, index_is_ready, rebuild_index, remove_index

logger = logging.getLogger(__name__)


def workspace_for(request: HttpRequest) -> str:
    """Derive an unguessable workspace ID from this browser's Django session."""
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key or ""
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        session_key.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def home(request: HttpRequest) -> HttpResponse:
    workspace_id = workspace_for(request)
    documents = UploadedDocument.objects.filter(workspace_id=workspace_id)
    chat_messages = list(
        ChatMessage.objects.filter(workspace_id=workspace_id)
        .order_by("-created_at")[:60]
    )
    chat_messages.reverse()
    context = {
        "documents": documents,
        "chat_messages": chat_messages,
        "has_documents": documents.exists(),
        "index_ready": index_is_ready(workspace_id),
        "question_form": QuestionForm(),
        "max_pdf_size_mb": settings.MAX_PDF_SIZE_BYTES // (1024 * 1024),
        "max_pdfs_per_upload": settings.MAX_PDFS_PER_UPLOAD,
        "max_pdfs_per_workspace": settings.MAX_PDFS_PER_WORKSPACE,
    }
    return render(request, "documents/home.html", context)


@require_POST
def upload_documents(request: HttpRequest) -> HttpResponse:
    workspace_id = workspace_for(request)
    uploaded_files = request.FILES.getlist("pdfs")

    if not uploaded_files:
        messages.error(request, "Choose at least one PDF to upload.")
        return redirect("home")
    if len(uploaded_files) > settings.MAX_PDFS_PER_UPLOAD:
        messages.error(
            request,
            f"Upload up to {settings.MAX_PDFS_PER_UPLOAD} PDFs at a time.",
        )
        return redirect("home")

    existing_count = UploadedDocument.objects.filter(workspace_id=workspace_id).count()
    if existing_count + len(uploaded_files) > settings.MAX_PDFS_PER_WORKSPACE:
        messages.error(
            request,
            f"A workspace can contain up to {settings.MAX_PDFS_PER_WORKSPACE} PDFs. Remove a PDF before adding more.",
        )
        return redirect("home")

    # Validate every file before writing any of them to storage.
    for uploaded_file in uploaded_files:
        safe_name = Path(uploaded_file.name or "document.pdf").name
        if Path(safe_name).suffix.lower() != ".pdf":
            messages.error(request, f"{safe_name} is not a PDF file.")
            return redirect("home")
        if uploaded_file.size <= 0 or uploaded_file.size > settings.MAX_PDF_SIZE_BYTES:
            messages.error(
                request,
                f"Each PDF must be between 1 byte and {settings.MAX_PDF_SIZE_BYTES // (1024 * 1024)} MB.",
            )
            return redirect("home")
        header = uploaded_file.read(1024)
        uploaded_file.seek(0)
        if b"%PDF-" not in header:
            messages.error(request, f"{safe_name} does not appear to be a valid PDF.")
            return redirect("home")

    created_records: list[UploadedDocument] = []
    try:
        with transaction.atomic():
            for uploaded_file in uploaded_files:
                original_name = Path(uploaded_file.name or "document.pdf").name[:255]
                record = UploadedDocument(
                    workspace_id=workspace_id,
                    original_name=original_name,
                )
                record.file.save(original_name, uploaded_file, save=False)
                record.save()
                created_records.append(record)

        all_records = list(
            UploadedDocument.objects.filter(workspace_id=workspace_id).order_by("created_at")
        )
        stats = rebuild_index(workspace_id, all_records)
        ChatMessage.objects.filter(workspace_id=workspace_id).delete()
        messages.success(
            request,
            f"Knowledge base updated: {stats['pages']} readable pages and {stats['chunks']} searchable chunks.",
        )
    except Exception as exc:
        logger.exception("PDF upload/indexing failed for workspace %s", workspace_id)
        # Remove this batch if indexing failed. rebuild_index stages the new index,
        # so a previous valid index is preserved when generation fails.
        for record in created_records:
            try:
                if record.file:
                    record.file.delete(save=False)
                record.delete()
            except Exception:
                logger.exception("Could not clean up failed uploaded document")
        if settings.DEBUG:
            messages.error(request, f"Could not index the PDFs: {exc}")
        else:
            messages.error(
                request,
                "The PDFs could not be indexed. Check the API configuration and server logs, then try again.",
            )

    return redirect("home")


@require_POST
def ask_question(request: HttpRequest) -> HttpResponse:
    workspace_id = workspace_for(request)
    form = QuestionForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Enter a question of up to 1,000 characters.")
        return redirect("home")

    question = form.cleaned_data["question"]
    has_documents = UploadedDocument.objects.filter(workspace_id=workspace_id).exists()
    if not has_documents:
        messages.error(request, "Upload and index at least one PDF before asking a question.")
        return redirect("home")

    ChatMessage.objects.create(
        workspace_id=workspace_id,
        role=ChatMessage.USER,
        content=question,
    )

    try:
        if not index_is_ready(workspace_id):
            records = list(UploadedDocument.objects.filter(workspace_id=workspace_id))
            rebuild_index(workspace_id, records)
        answer, sources = answer_from_documents(workspace_id, question)
    except Exception as exc:
        logger.exception("RAG question failed for workspace %s", workspace_id)
        answer = "I couldn't generate an answer right now. Check the API key, model availability, and server logs, then try again."
        if settings.DEBUG:
            answer += f"\n\nDevelopment error: {exc}"
        sources = []

    ChatMessage.objects.create(
        workspace_id=workspace_id,
        role=ChatMessage.ASSISTANT,
        content=answer,
        sources=sources,
    )
    return redirect("home")


@require_POST
def delete_document(request: HttpRequest, pk: int) -> HttpResponse:
    workspace_id = workspace_for(request)
    document = get_object_or_404(
        UploadedDocument,
        pk=pk,
        workspace_id=workspace_id,
    )
    remaining = list(
        UploadedDocument.objects.filter(workspace_id=workspace_id)
        .exclude(pk=document.pk)
        .order_by("created_at")
    )

    try:
        # Rebuild first so a failed rebuild doesn't expose stale deleted content.
        if remaining:
            stats = rebuild_index(workspace_id, remaining)
        else:
            remove_index(workspace_id)
            stats = {"pages": 0, "chunks": 0}

        stored_file = document.file
        document.delete()
        if stored_file:
            stored_file.delete(save=False)
        ChatMessage.objects.filter(workspace_id=workspace_id).delete()
        messages.success(
            request,
            f"Removed {document.original_name}. The knowledge base now has {stats['chunks']} chunks.",
        )
    except Exception as exc:
        logger.exception("Document deletion/reindex failed for workspace %s", workspace_id)
        if settings.DEBUG:
            messages.error(request, f"Could not remove the PDF: {exc}")
        else:
            messages.error(request, "Could not remove the PDF. Please check the server logs and try again.")

    return redirect("home")


@require_POST
def clear_chat(request: HttpRequest) -> HttpResponse:
    workspace_id = workspace_for(request)
    ChatMessage.objects.filter(workspace_id=workspace_id).delete()
    messages.success(request, "Chat history cleared. Your indexed documents are unchanged.")
    return redirect("home")
