/**
 * admin.js — script for admin page (admin.html)
 * Circles background animation
 */
document.addEventListener("DOMContentLoaded", function () {
    var c = document.getElementById("circles-container");
    if (c) {
        var dots = [],
            n = 16;
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
});
