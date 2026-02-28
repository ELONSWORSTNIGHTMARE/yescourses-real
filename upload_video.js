/**
 * upload_video.js — standalone script for upload page only
 * Handles form submit via fetch, file input, drag-and-drop
 */
(function () {
    "use strict";

    var form = document.getElementById("upload-video-form");
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

    function submitViaFetch(e) {
        e.preventDefault();
        if (!videoInput.files || !videoInput.files.length) {
            alert("გთხოვ აირჩიო ვიდეო ფაილი.");
            return;
        }
        var btn = form.querySelector('button[type="submit"]');
        var originalText = btn ? btn.textContent : "";
        if (btn) {
            btn.disabled = true;
            btn.textContent = "იტვირთება...";
        }
        fetch(form.action, {
            method: "POST",
            body: new FormData(form),
            redirect: "follow",
            credentials: "same-origin"
        })
            .then(function (res) {
                if (res.redirected && res.url) {
                    window.location.href = res.url;
                    return;
                }
                if (res.ok) {
                    window.location.href = "/course/basic";
                    return;
                }
                return res.text().then(function () {
                    alert("შეცდომა: " + res.status);
                });
            })
            .catch(function () {
                alert("ატვირთვა ვერ მოხერხდა.");
            })
            .finally(function () {
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = originalText;
                }
            });
    }

    function initForm() {
        if (!form || !videoInput) return;
        form.addEventListener("submit", submitViaFetch);
    }

    function init() {
        initFileInput();
        initUploadZone();
        initForm();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
