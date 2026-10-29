(() => {
  const fileInput = document.getElementById("pdf-input");
  const selectedFiles = document.getElementById("selected-files");
  const dropzone = document.getElementById("dropzone");
  const uploadForm = document.getElementById("upload-form");
  const uploadButton = document.getElementById("upload-button");
  const questionInput = document.getElementById("question-input");
  const chatScroll = document.getElementById("chat-scroll");

  if (chatScroll) chatScroll.scrollTop = chatScroll.scrollHeight;

  if (fileInput && selectedFiles) {
    const showFiles = (files) => {
      const fileList = Array.from(files || []);
      selectedFiles.replaceChildren();
      if (!fileList.length) {
        selectedFiles.hidden = true;
        uploadButton.disabled = true;
        return;
      }
      selectedFiles.hidden = false;
      fileList.forEach((file) => {
        const item = document.createElement("div");
        item.className = "selected-file";
        const icon = document.createElement("span");
        icon.className = "selected-file-icon";
        icon.textContent = "PDF";
        const label = document.createElement("span");
        label.className = "selected-file-name";
        label.textContent = file.name;
        const size = document.createElement("small");
        size.textContent = `${(file.size / (1024 * 1024)).toFixed(1)} MB`;
        item.append(icon, label, size);
        selectedFiles.append(item);
      });
      uploadButton.disabled = false;
    };

    fileInput.addEventListener("change", () => showFiles(fileInput.files));
    dropzone?.addEventListener("dragover", (event) => {
      event.preventDefault();
      dropzone.classList.add("is-dragging");
    });
    dropzone?.addEventListener("dragleave", () => dropzone.classList.remove("is-dragging"));
    dropzone?.addEventListener("drop", (event) => {
      event.preventDefault();
      dropzone.classList.remove("is-dragging");
      if (!event.dataTransfer?.files?.length) return;
      const transfer = new DataTransfer();
      Array.from(event.dataTransfer.files).forEach((file) => transfer.items.add(file));
      fileInput.files = transfer.files;
      showFiles(fileInput.files);
    });
    uploadForm?.addEventListener("submit", () => {
      uploadButton.disabled = true;
      uploadButton.innerHTML = 'Indexing documents <span class="spinner"></span>';
    });
  }

  document.querySelectorAll("[data-question]").forEach((button) => {
    button.addEventListener("click", () => {
      if (!questionInput || questionInput.disabled) return;
      questionInput.value = button.getAttribute("data-question") || "";
      questionInput.focus();
    });
  });

  document.querySelectorAll("[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.getAttribute("data-confirm"))) event.preventDefault();
    });
  });

  document.querySelectorAll(".toast-close").forEach((button) => {
    button.addEventListener("click", () => button.closest(".toast")?.remove());
  });
})();
