# Generated for the initial document and chat tables.
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="UploadedDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("workspace_id", models.CharField(db_index=True, max_length=64)),
                ("file", models.FileField(upload_to="rag_uploads/%Y/%m/%d/")),
                ("original_name", models.CharField(max_length=255)),
                ("pages_count", models.PositiveIntegerField(default=0)),
                ("chunks_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ChatMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("workspace_id", models.CharField(db_index=True, max_length=64)),
                ("role", models.CharField(choices=[("user", "User"), ("assistant", "Assistant")], max_length=12)),
                ("content", models.TextField()),
                ("sources", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["created_at"]},
        ),
    ]
