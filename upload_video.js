(function () {
    "use strict";

    var videoInput = document.getElementById("video_file_input");
    var fileNameEl = document.getElementById("upload-file-name");
    var uploadZone = document.getElementById("upload-zone");

    function setFileName(text) {
        if (fileNameEl) fileNameEl.textContent = text || "";
    }

    function initFileInput() {
        if (!videoInput || !fileNameEl) return;
        videoInput.addEventListener("change", function () {
            setFileName(this.files && this.files.length ? this.files[0].name : "");
        });
    }

    function initUploadZone() {
        if (!uploadZone || !videoInput) return;
        uploadZone.addEventListener("click", function (e) {
            e.preventDefault();
            videoInput.click();
        });
        uploadZone.addEventListener("dragover", function (e) {
            e.preventDefault();
            e.stopPropagation();
            uploadZone.classList.add("uv-dragover");
        });
        uploadZone.addEventListener("dragleave", function (e) {
            e.preventDefault();
            uploadZone.classList.remove("uv-dragover");
        });
        uploadZone.addEventListener("drop", function (e) {
            e.preventDefault();
            e.stopPropagation();
            uploadZone.classList.remove("uv-dragover");
            if (e.dataTransfer.files && e.dataTransfer.files.length) {
                videoInput.files = e.dataTransfer.files;
                setFileName(e.dataTransfer.files[0].name);
            }
        });
    }

    function init() {
        if (!videoInput) return;
        initFileInput();
        initUploadZone();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
