from django.test import TestCase
from django.urls import reverse

from .models import ChatMessage


class WorkspaceViewTests(TestCase):
    def test_home_page_renders_without_documents(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "DocuMind")
        self.assertContains(response, "Upload PDF files")

    def test_upload_without_files_redirects(self):
        response = self.client.post(reverse("upload_documents"))
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_question_without_documents_is_rejected(self):
        response = self.client.post(
            reverse("ask_question"),
            {"question": "What are the main ideas?"},
        )
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(ChatMessage.objects.count(), 0)
