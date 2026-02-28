(function () {
    "use strict";

    var form = document.getElementById("upload-video-form");
    var videoInput = document.getElementById("video_file_input");
    var fileNameEl = document.getElementById("upload-file-name");
    var uploadZone = document.getElementById("upload-zone");
    var message = document.getElementById("upload-message");

    function setFileName(text) {
        if (fileNameEl) fileNameEl.textContent = text || "";
    }

    function showMessage(text, type) {
        if (!message) return;
        message.style.display = "block";
        message.className = "uv-message " + (type || "");
        message.textContent = text;
    }

    function fileToDataUrl(file) {
        return new Promise(function (resolve, reject) {
            var reader = new FileReader();
            reader.onload = function () { resolve(String(reader.result || "")); };
            reader.onerror = function () { reject(reader.error || new Error("FileReader failed")); };
            reader.readAsDataURL(file);
        });
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

    function submitVideo(e) {
        e.preventDefault();
        if (!videoInput || !videoInput.files || !videoInput.files.length) {
            showMessage("გთხოვ აირჩიო ვიდეო ფაილი.", "error");
            return;
        }
        if (!window.YescoursesStore) {
            showMessage("შიდა საცავი ვერ ჩაიტვირთა.", "error");
            return;
        }

        var data = new FormData(form);
        var packId = String(data.get("pack_id") || "basic");
        var title = String(data.get("title") || "ვიდეო");
        var description = String(data.get("description") || "");
        var orderIndex = Math.max(1, Number(data.get("order_index")) || 1);
        var file = videoInput.files[0];
        var videoId = Date.now().toString();
        var blobId = "blob_" + videoId;

        window.YescoursesStore.saveVideoBlob(blobId, file).then(function () {
            var videos = window.YescoursesStore.getVideos();
            videos.push({
                id: videoId,
                pack_id: packId,
                title: title,
                description: description,
                order_index: orderIndex,
                blob_id: blobId,
                url: ""
            });
            window.YescoursesStore.setVideos(videos);
            showMessage("ვიდეო შენახულია და დაემატა კურსს.", "success");
            setTimeout(function () {
                window.location.href = "course.html?pack=" + encodeURIComponent(packId);
            }, 500);
        }).catch(function () {
            // Fallback for environments where IndexedDB is blocked/unavailable.
            fileToDataUrl(file).then(function (dataUrl) {
                var videos = window.YescoursesStore.getVideos();
                videos.push({
                    id: videoId,
                    pack_id: packId,
                    title: title,
                    description: description,
                    order_index: orderIndex,
                    blob_id: "",
                    url: dataUrl
                });
                window.YescoursesStore.setVideos(videos);
                showMessage("ვიდეო დაემატა fallback რეჟიმით.", "success");
                setTimeout(function () {
                    window.location.href = "course.html?pack=" + encodeURIComponent(packId);
                }, 500);
            }).catch(function () {
                showMessage("ვიდეოს შენახვა ვერ მოხერხდა. სცადე უფრო მცირე ფაილი.", "error");
            });
        });
    }

    function init() {
        if (!form) return;
        initFileInput();
        initUploadZone();
        form.addEventListener("submit", submitVideo);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
