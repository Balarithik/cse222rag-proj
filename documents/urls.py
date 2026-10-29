from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("upload/", views.upload_documents, name="upload_documents"),
    path("ask/", views.ask_question, name="ask_question"),
    path("documents/<int:pk>/delete/", views.delete_document, name="delete_document"),
    path("clear-chat/", views.clear_chat, name="clear_chat"),
]
