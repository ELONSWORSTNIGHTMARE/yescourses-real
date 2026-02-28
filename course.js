/**
 * course.js — script for course page (course.html)
 * Circles background + video upload form
 */
document.addEventListener("DOMContentLoaded", function () {
    var c = document.getElementById("circles-container");
    if (c) {
        var dots = [],
            n = 18;
        for (var i = 0; i < n; i++) {
            var d = document.createElement("div");
            d.className = "circle";
            var dur = 22 + Math.random() * 16,
                del = Math.random() * -dur;
            var left = Math.random() * 100,
                top = Math.random() * 100;
            d.style.left = left + "%";
            d.style.top = top + "%";
            d.style.animationDuration = dur + "s";
            d.style.animationDelay = del + "s";
            c.appendChild(d);
            dots.push({ left: left, top: top });
        }
        for (var j = 1; j < dots.length; j++) {
            var a = dots[j - 1],
                b = dots[j];
            var line = document.createElement("div");
            line.className = "circle-line";
            var dx = b.left - a.left,
                dy = b.top - a.top;
            var len = Math.sqrt(dx * dx + dy * dy),
                angle = (Math.atan2(dy, dx) * 180) / Math.PI;
            line.style.width = len + "vw";
            line.style.left = a.left + "%";
            line.style.top = a.top + "%";
            line.style.transformOrigin = "0 0";
            line.style.transform = "rotate(" + angle + "deg)";
            c.appendChild(line);
        }
    }

    var courseUploadForm = document.getElementById("course-upload-form");
    var courseVideoFile = document.getElementById("course-video-file");
    var courseUploadZone = document.getElementById("course-upload-zone");
    var courseUploadFilename = document.getElementById("course-upload-filename");

    if (courseVideoFile && courseUploadFilename) {
        courseVideoFile.addEventListener("change", function () {
            courseUploadFilename.textContent =
                this.files && this.files.length ? this.files[0].name : "";
        });
    }

    if (courseUploadZone && courseVideoFile) {
        courseUploadZone.addEventListener("click", function (e) {
            e.preventDefault();
            courseVideoFile.click();
        });
    }

    if (courseUploadForm && courseVideoFile) {
        courseUploadForm.addEventListener("submit", function (e) {
            e.preventDefault();
            if (!courseVideoFile.files || !courseVideoFile.files.length) {
                alert("გთხოვ აირჩიო ვიდეო ფაილი.");
                return false;
            }
            var submitBtn = courseUploadForm.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = "იტვირთება...";
            }
            var redirectTo = courseUploadForm.dataset.redirectUrl || "/course/basic";
            fetch(courseUploadForm.action, {
                method: "POST",
                body: new FormData(courseUploadForm),
                redirect: "follow",
                credentials: "same-origin"
            })
                .then(function (res) {
                    if (res.redirected && res.url) {
                        window.location.href = res.url;
                        return;
                    }
                    if (res.ok) {
                        window.location.href = redirectTo;
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
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.textContent = "ატვირთვა";
                    }
                });
            return false;
        });
    }
});
