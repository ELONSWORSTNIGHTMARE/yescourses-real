/**
 * index.js — script for main landing page (index.html)
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

    var faq = document.querySelectorAll(".faq-item");
    faq.forEach(function (item) {
        var btn = item.querySelector(".faq-question");
        if (btn)
            btn.addEventListener("click", function () {
                var open = item.classList.contains("open");
                faq.forEach(function (i) {
                    i.classList.remove("open");
                });
                if (!open) item.classList.add("open");
            });
    });

    var modal = document.getElementById("auth-modal");
    if (modal) {
        var openBtn = document.getElementById("open-auth-modal");
        var closeBtn = document.getElementById("close-auth-modal");
        var heroBtn = document.getElementById("hero-start-btn");
        if (openBtn)
            openBtn.addEventListener("click", function () {
                modal.classList.remove("hidden");
            });
        if (heroBtn)
            heroBtn.addEventListener("click", function () {
                modal.classList.remove("hidden");
            });
        if (closeBtn)
            closeBtn.addEventListener("click", function () {
                modal.classList.add("hidden");
            });
        modal.addEventListener("click", function (e) {
            if (e.target === modal) modal.classList.add("hidden");
        });
    }

    var choosePack = document.querySelectorAll(".choose-pack");
    choosePack.forEach(function (btn) {
        btn.addEventListener("click", function (e) {
            if (btn.tagName === "BUTTON" && !btn.querySelector("a")) {
                var modal = document.getElementById("auth-modal");
                if (modal && !modal.classList.contains("hidden")) return;
                if (modal) modal.classList.remove("hidden");
            }
        });
    });
});
