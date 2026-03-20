(function () {
    "use strict";

    var STORAGE_USER = "yescoursesUser";
    var STORAGE_ACCOUNTS = "yescoursesAccounts";
    var STORAGE_CURRENT_USER_EMAIL = "yescoursesCurrentUserEmail";
    var STORAGE_ADMIN = "yescoursesAdmin";
    var STORAGE_VIDEOS = "yescoursesVideos";
    var DB_NAME = "yescoursesData";
    var DB_VERSION = 1;
    var BLOB_STORE = "videoBlobs";

    function readJSON(key, fallback) {
        try {
            var raw = localStorage.getItem(key);
            return raw ? JSON.parse(raw) : fallback;
        } catch (e) {
            return fallback;
        }
    }

    function writeJSON(key, value) {
        localStorage.setItem(key, JSON.stringify(value));
    }

    function getAccounts() {
        var accounts = readJSON(STORAGE_ACCOUNTS, []);
        return Array.isArray(accounts) ? accounts : [];
    }

    function setAccounts(accounts) {
        writeJSON(STORAGE_ACCOUNTS, accounts || []);
    }

    function getCurrentUserEmail() {
        return localStorage.getItem(STORAGE_CURRENT_USER_EMAIL) || "";
    }

    function setCurrentUserEmail(email) {
        if (!email) {
            localStorage.removeItem(STORAGE_CURRENT_USER_EMAIL);
            return;
        }
        localStorage.setItem(STORAGE_CURRENT_USER_EMAIL, email);
    }

    function getCurrentAccount() {
        var email = getCurrentUserEmail();
        if (!email) return null;
        var accounts = getAccounts();
        return accounts.find(function (a) { return a.email === email; }) || null;
    }

    function saveAccount(updatedAccount) {
        var accounts = getAccounts();
        var idx = accounts.findIndex(function (a) { return a.email === updatedAccount.email; });
        if (idx >= 0) {
            accounts[idx] = updatedAccount;
        } else {
            accounts.push(updatedAccount);
        }
        setAccounts(accounts);
    }

    function userHasPack(account, packId) {
        return Boolean(
            account &&
            Array.isArray(account.purchased) &&
            account.purchased.indexOf(packId) !== -1
        );
    }

    function purchasePack(packId) {
        var account = getCurrentAccount();
        if (!account) return false;
        if (!Array.isArray(account.purchased)) account.purchased = [];
        if (account.purchased.indexOf(packId) === -1) {
            account.purchased.push(packId);
            saveAccount(account);
        }
        return true;
    }

    function ensureLegacyUserMigrated() {
        var legacy = readJSON(STORAGE_USER, null);
        var currentEmail = getCurrentUserEmail();
        if (!legacy || currentEmail) return;
        if (!legacy.email) return;

        var accounts = getAccounts();
        var exists = accounts.some(function (a) { return a.email === legacy.email; });
        if (!exists) {
            accounts.push({
                name: legacy.name || "მომხმარებელი",
                email: legacy.email,
                password: "",
                purchased: []
            });
            setAccounts(accounts);
        }
        setCurrentUserEmail(legacy.email);
    }

    function ensureSystemAccounts() {
        var accounts = getAccounts();
        var systemEmail = "matebedeladze@gmail.com";
        var requiredPacks = ["basic", "plus", "premium"];
        var existing = accounts.find(function (a) { return a.email === systemEmail; });

        if (existing) {
            existing.name = "admin mate";
            existing.password = "Matebedeladze1";
            if (!Array.isArray(existing.purchased)) existing.purchased = [];
            requiredPacks.forEach(function (packId) {
                if (existing.purchased.indexOf(packId) === -1) existing.purchased.push(packId);
            });
        } else {
            accounts.push({
                name: "admin mate",
                email: systemEmail,
                password: "Matebedeladze1",
                purchased: requiredPacks.slice()
            });
        }

        setAccounts(accounts);
    }

    function getVideos() {
        var videos = readJSON(STORAGE_VIDEOS, []);
        return Array.isArray(videos) ? videos : [];
    }

    function setVideos(videos) {
        writeJSON(STORAGE_VIDEOS, videos || []);
    }

    function openVideoDb() {
        return new Promise(function (resolve, reject) {
            if (!window.indexedDB) {
                reject(new Error("IndexedDB is not available"));
                return;
            }
            var req = indexedDB.open(DB_NAME, DB_VERSION);
            req.onupgradeneeded = function (event) {
                var db = event.target.result;
                if (!db.objectStoreNames.contains(BLOB_STORE)) {
                    db.createObjectStore(BLOB_STORE);
                }
            };
            req.onsuccess = function () { resolve(req.result); };
            req.onerror = function () { reject(req.error); };
        });
    }

    function saveVideoBlob(blobId, file) {
        return openVideoDb().then(function (db) {
            return new Promise(function (resolve, reject) {
                var tx = db.transaction(BLOB_STORE, "readwrite");
                tx.objectStore(BLOB_STORE).put(file, blobId);
                tx.oncomplete = function () { db.close(); resolve(); };
                tx.onerror = function () { db.close(); reject(tx.error); };
            });
        });
    }

    function getVideoBlob(blobId) {
        return openVideoDb().then(function (db) {
            return new Promise(function (resolve, reject) {
                var tx = db.transaction(BLOB_STORE, "readonly");
                var req = tx.objectStore(BLOB_STORE).get(blobId);
                req.onsuccess = function () { db.close(); resolve(req.result || null); };
                req.onerror = function () { db.close(); reject(req.error); };
            });
        });
    }

    function deleteVideoBlob(blobId) {
        if (!blobId) return Promise.resolve();
        return openVideoDb().then(function (db) {
            return new Promise(function (resolve, reject) {
                var tx = db.transaction(BLOB_STORE, "readwrite");
                tx.objectStore(BLOB_STORE).delete(blobId);
                tx.oncomplete = function () { db.close(); resolve(); };
                tx.onerror = function () { db.close(); reject(tx.error); };
            });
        });
    }

    window.YescoursesStore = {
        getVideos: getVideos,
        setVideos: setVideos,
        saveVideoBlob: saveVideoBlob,
        getVideoBlob: getVideoBlob,
        deleteVideoBlob: deleteVideoBlob
    };

    function initBackground() {
        var c = document.getElementById("circles-container");
        if (!c) return;
        var dots = [];
        var n = 18;
        for (var i = 0; i < n; i++) {
            var d = document.createElement("div");
            d.className = "circle";
            var dur = 22 + Math.random() * 16;
            var del = Math.random() * -dur;
            var left = Math.random() * 100;
            var top = Math.random() * 100;
            d.style.left = left + "%";
            d.style.top = top + "%";
            d.style.animationDuration = dur + "s";
            d.style.animationDelay = del + "s";
            c.appendChild(d);
            dots.push({ left: left, top: top });
        }
        for (var j = 1; j < dots.length; j++) {
            var a = dots[j - 1];
            var b = dots[j];
            var line = document.createElement("div");
            line.className = "circle-line";
            var dx = b.left - a.left;
            var dy = b.top - a.top;
            var len = Math.sqrt(dx * dx + dy * dy);
            var angle = Math.atan2(dy, dx) * 180 / Math.PI;
            line.style.width = len + "vw";
            line.style.left = a.left + "%";
            line.style.top = a.top + "%";
            line.style.transformOrigin = "0 0";
            line.style.transform = "rotate(" + angle + "deg)";
            c.appendChild(line);
        }
    }

    function initFaq() {
        var faqItems = document.querySelectorAll(".faq-item");
        faqItems.forEach(function (item) {
            var btn = item.querySelector(".faq-question");
            if (!btn) return;
            btn.addEventListener("click", function () {
                var isOpen = item.classList.contains("open");
                faqItems.forEach(function (i) { i.classList.remove("open"); });
                if (!isOpen) item.classList.add("open");
            });
        });
    }

    function initAuthModal() {
        var authModal = document.getElementById("auth-modal");
        if (!authModal) return;

        var openAuth = document.getElementById("open-auth-modal");
        var closeAuth = document.getElementById("close-auth-modal");
        var heroStartBtn = document.getElementById("hero-start-btn");
        var logoutBtn = document.getElementById("logout-btn");
        var profileWrap = document.getElementById("profile-menu-wrap");
        var profileBtn = document.getElementById("profile-avatar-btn");
        var profileInitial = document.getElementById("profile-avatar-initial");
        var profileDropdown = document.getElementById("profile-dropdown");
        var profileName = document.getElementById("profile-dropdown-name");
        var profileEmail = document.getElementById("profile-dropdown-email");
        var openSettingsBtn = document.getElementById("open-settings-modal");
        var settingsModal = document.getElementById("settings-modal");
        var closeSettingsBtn = document.getElementById("close-settings-modal");
        var settingsUsername = document.getElementById("settings-username");
        var settingsEmail = document.getElementById("settings-email");
        var settingsMessage = document.getElementById("settings-message");
        var changePasswordForm = document.getElementById("change-password-form");
        var message = document.getElementById("auth-message");
        var registerForm = document.getElementById("register-form");
        var loginForm = document.getElementById("login-form");

        function showModal() { authModal.classList.remove("hidden"); }
        function hideModal() { authModal.classList.add("hidden"); }
        function hideProfileDropdown() {
            if (profileDropdown) profileDropdown.classList.add("hidden");
        }

        function paintUser() {
            var account = getCurrentAccount();
            if (account && account.name) {
                if (profileWrap) profileWrap.style.display = "inline-block";
                if (profileInitial) {
                    profileInitial.textContent = (account.name || "U").trim().charAt(0).toUpperCase();
                }
                if (profileName) profileName.textContent = account.name;
                if (profileEmail) profileEmail.textContent = account.email || "";
                if (settingsUsername) settingsUsername.textContent = account.name;
                if (settingsEmail) settingsEmail.textContent = account.email || "";
                if (openAuth) openAuth.style.display = "none";
                if (logoutBtn) logoutBtn.style.display = "inline-flex";
            } else {
                if (profileWrap) profileWrap.style.display = "none";
                if (openAuth) openAuth.style.display = "inline-flex";
                if (logoutBtn) logoutBtn.style.display = "none";
                hideProfileDropdown();
            }
        }

        function setMessage(text, type) {
            if (!message) return;
            message.textContent = text;
            message.className = "auth-message " + (type || "");
        }

        if (openAuth) openAuth.addEventListener("click", showModal);
        if (heroStartBtn) heroStartBtn.addEventListener("click", showModal);
        if (closeAuth) closeAuth.addEventListener("click", hideModal);
        if (logoutBtn) {
            logoutBtn.addEventListener("click", function () {
                localStorage.removeItem(STORAGE_USER);
                setCurrentUserEmail("");
                paintUser();
                initPricingActions();
                hideProfileDropdown();
            });
        }

        if (profileBtn) {
            profileBtn.addEventListener("click", function (e) {
                e.stopPropagation();
                if (profileDropdown) profileDropdown.classList.toggle("hidden");
            });
        }

        document.addEventListener("click", function (e) {
            if (!profileWrap || !profileDropdown) return;
            if (!profileWrap.contains(e.target)) {
                profileDropdown.classList.add("hidden");
            }
        });

        function showSettingsModal() {
            if (settingsMessage) settingsMessage.textContent = "";
            if (settingsModal) settingsModal.classList.remove("hidden");
            hideProfileDropdown();
        }

        function hideSettingsModal() {
            if (settingsModal) settingsModal.classList.add("hidden");
        }

        if (openSettingsBtn) {
            openSettingsBtn.addEventListener("click", showSettingsModal);
        }
        if (closeSettingsBtn) {
            closeSettingsBtn.addEventListener("click", hideSettingsModal);
        }
        if (settingsModal) {
            settingsModal.addEventListener("click", function (e) {
                if (e.target === settingsModal) hideSettingsModal();
            });
        }

        if (changePasswordForm) {
            changePasswordForm.addEventListener("submit", function (e) {
                e.preventDefault();
                var account = getCurrentAccount();
                if (!account) return;
                var data = new FormData(changePasswordForm);
                var newPassword = (data.get("new_password") || "").toString();
                if (newPassword.length < 6) {
                    if (settingsMessage) {
                        settingsMessage.className = "auth-message error";
                        settingsMessage.textContent = "პაროლი მინიმუმ 6 სიმბოლო.";
                    }
                    return;
                }
                account.password = newPassword;
                saveAccount(account);
                if (settingsMessage) {
                    settingsMessage.className = "auth-message success";
                    settingsMessage.textContent = "პაროლი წარმატებით განახლდა.";
                }
                changePasswordForm.reset();
            });
        }

        authModal.addEventListener("click", function (e) {
            if (e.target === authModal) hideModal();
        });

        var tabButtons = document.querySelectorAll(".tab-button");
        var tabPanels = document.querySelectorAll(".tab-panel");
        tabButtons.forEach(function (btn) {
            btn.addEventListener("click", function () {
                var target = btn.dataset.tab;
                tabButtons.forEach(function (b) { b.classList.remove("active"); });
                tabPanels.forEach(function (p) { p.classList.remove("active"); });
                btn.classList.add("active");
                var panel = document.getElementById(target);
                if (panel) panel.classList.add("active");
            });
        });

        if (registerForm) {
            registerForm.addEventListener("submit", function (e) {
                e.preventDefault();
                var data = new FormData(registerForm);
                var name = (data.get("name") || "").toString().trim();
                var email = (data.get("email") || "").toString().trim();
                var password = (data.get("password") || "").toString();
                if (!name || !email) {
                    setMessage("შეავსე ყველა ველი.", "error");
                    return;
                }
                if (password.length < 6) {
                    setMessage("პაროლი მინიმუმ 6 სიმბოლო.", "error");
                    return;
                }

                var accounts = getAccounts();
                if (accounts.some(function (a) { return a.email === email; })) {
                    setMessage("ეს ელფოსტა უკვე დარეგისტრირებულია.", "error");
                    return;
                }

                var account = {
                    name: name,
                    email: email,
                    password: password,
                    purchased: []
                };
                accounts.push(account);
                setAccounts(accounts);
                setCurrentUserEmail(email);
                writeJSON(STORAGE_USER, { name: name, email: email });
                setMessage("რეგისტრაცია წარმატებულია.", "success");
                paintUser();
                initPricingActions();
                setTimeout(hideModal, 500);
            });
        }

        if (loginForm) {
            loginForm.addEventListener("submit", function (e) {
                e.preventDefault();
                var data = new FormData(loginForm);
                var email = (data.get("email") || "").toString().trim();
                var password = (data.get("password") || "").toString();
                if (!email) {
                    setMessage("შეავსე ელფოსტა.", "error");
                    return;
                }
                var accounts = getAccounts();
                var account = accounts.find(function (a) {
                    return a.email === email && a.password === password;
                });
                if (!account) {
                    setMessage("არასწორი ელფოსტა ან პაროლი.", "error");
                    return;
                }
                setCurrentUserEmail(account.email);
                writeJSON(STORAGE_USER, { name: account.name || "მომხმარებელი", email: account.email });
                setMessage("შესვლა წარმატებულია.", "success");
                paintUser();
                initPricingActions();
                setTimeout(hideModal, 500);
            });
        }

        function initPasswordToggles() {
            document.querySelectorAll(".password-toggle").forEach(function (btn) {
                if (btn.dataset.bound === "1") return;
                btn.dataset.bound = "1";
                btn.addEventListener("click", function () {
                    var wrap = btn.closest(".password-field");
                    if (!wrap) return;
                    var input = wrap.querySelector("input");
                    if (!input) return;
                    var show = input.type === "password";
                    input.type = show ? "text" : "password";
                    btn.textContent = show ? "Hide" : "Show";
                    btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
                });
            });
        }

        initPasswordToggles();
        paintUser();
    }

    function initPricingActions() {
        var actions = document.querySelectorAll(".pack-action");
        if (!actions.length) return;

        var account = getCurrentAccount();
        actions.forEach(function (btn) {
            var pack = btn.getAttribute("data-pack") || "basic";
            var purchased = userHasPack(account, pack);
            btn.textContent = purchased ? "კურსის გვერდი" : "ვიყიდო";
            if (btn.dataset.bound === "1") return;
            btn.dataset.bound = "1";
            btn.addEventListener("click", function () {
                var current = getCurrentAccount();
                if (!current) {
                    var openBtn = document.getElementById("open-auth-modal");
                    if (openBtn) openBtn.click();
                    return;
                }

                if (userHasPack(current, pack)) {
                    window.location.href =
                        "/course.html?pack=" + encodeURIComponent(pack);
                    return;
                }

                var ok = window.confirm("გადახდის ბმულს მოგვიანებით დავამატებთ. გინდა ეს პაკეტი ახლა ჩაითვალოს შეძენილად?");
                if (!ok) return;
                purchasePack(pack);
                initPricingActions();
                window.location.href =
                    "/course.html?pack=" + encodeURIComponent(pack);
            });
        });
    }

    function videoMimeFromUrl(url) {
        var path = (url || "").split("?")[0].split("#")[0].toLowerCase();
        if (path.endsWith(".m4v") || path.endsWith(".mp4")) return "video/mp4";
        if (path.endsWith(".webm")) return "video/webm";
        if (path.endsWith(".mov")) return "video/quicktime";
        if (path.endsWith(".mkv")) return "video/x-matroska";
        return "video/mp4";
    }

    /** iOS Safari: playsinline + &lt;source type&gt;; server must send Range + correct Content-Type */
    function courseVideoPlayerHtml(src) {
        if (!src || !String(src).trim()) {
            return (
                '<div class="video-player-wrapper" style="padding:1rem;border-radius:0.8rem;border:1px solid rgba(248,113,113,0.5);background:rgba(127,29,29,0.2);">' +
                '<p class="video-description" style="margin:0;color:#fca5a5;">ვიდეოს წყარო აკლია ან ხელმიუწვდომელია ამ მოწყობილობიდან. ადმინმა უნდა დაამატოს <strong>საჯარო HTTPS ბმული</strong> (MP4) ატვირთვის გვერდზე.</p>' +
                "</div>"
            );
        }
        var esc = escapeHtml(src);
        var mime = videoMimeFromUrl(src);
        return (
            '<div class="video-player-wrapper">' +
            '<video class="video-player" controls playsinline webkit-playsinline ' +
            'preload="metadata" x-webkit-airplay="allow">' +
            '<source src="' +
            esc +
            '" type="' +
            mime +
            '">' +
            "თქვენი ბრაუზერი ვიდეოს არ იგებს." +
            "</video></div>"
        );
    }

    function renderCourseVideosFromServer(list, payload) {
        var title = document.getElementById("course-title");
        if (title) title.textContent = payload.pack_name || "კურსი";
        var warnBox = document.getElementById("course-warnings");
        if (warnBox) {
            var warns = payload.warnings || [];
            if (warns.length) {
                warnBox.style.display = "block";
                warnBox.innerHTML =
                    '<div class="auth-message error" style="max-width:100%;margin:0 0 1rem;padding:0.75rem 1rem;border-radius:0.75rem;">' +
                    warns.map(function (w) {
                        return "<p style=\"margin:0.35rem 0;\">" + escapeHtml(w) + "</p>";
                    }).join("") +
                    "</div>";
            } else {
                warnBox.innerHTML = "";
                warnBox.style.display = "none";
            }
        }
        var videos = payload.videos || [];
        if (!videos.length) {
            list.innerHTML =
                '<article class="video-card"><div class="video-header"><h3 class="video-title">ჯერ ვიდეოები არ არის</h3></div></article>';
            return;
        }
        list.innerHTML = videos
            .map(function (v, i) {
                var src = v.src || "";
                return [
                    '<article class="video-card">',
                    '<div class="video-header"><span class="video-order">#' +
                        (i + 1) +
                        '</span><h3 class="video-title">' +
                        escapeHtml(v.title) +
                        "</h3></div>",
                    v.description
                        ? '<p class="video-description">' + escapeHtml(v.description) + "</p>"
                        : "",
                    courseVideoPlayerHtml(src),
                    "</article>",
                ].join("");
            })
            .join("");
    }

    function initCoursePage() {
        var list = document.getElementById("videos-list");
        if (!list) return;

        var payload = window.__COURSE_PAYLOAD__;
        if (payload && typeof payload === "object" && Array.isArray(payload.videos)) {
            renderCourseVideosFromServer(list, payload);
            return;
        }

        var params = new URLSearchParams(window.location.search);
        var pathMatch = window.location.pathname.match(/\/course\/([^/]+)\/?$/);
        var pack =
            params.get("pack") ||
            (pathMatch ? decodeURIComponent(pathMatch[1]) : null) ||
            "basic";
        var account = getCurrentAccount();
        if (!account) {
            window.location.href = "/";
            return;
        }

        var packNames = {
            basic: "საწყისი პაკეტი",
            plus: "სრული მენტორშიპი",
            premium: "1-1 Mentorship",
            pro: "1-1 Mentorship",
        };
        var title = document.getElementById("course-title");
        if (title) title.textContent = "შენი კურსის სივრცე — " + (packNames[pack] || "საწყისი პაკეტი");

        var videos = getVideos();
        var filtered = videos.filter(function (v) {
            return v.pack_id === pack;
        });
        filtered.sort(function (a, b) {
            return Number(a.order_index || 0) - Number(b.order_index || 0);
        });

        if (!filtered.length) {
            list.innerHTML =
                '<article class="video-card"><div class="video-header"><h3 class="video-title">ჯერ ვიდეოები არ არის</h3></div><p class="video-description">ამ პაკეტის ვიდეოები მალე დაემატება.</p></article>';
            return;
        }

        list.innerHTML = filtered
            .map(function (v, i) {
                return [
                    '<article class="video-card">',
                    '<div class="video-header"><span class="video-order">#' +
                        (i + 1) +
                        '</span><h3 class="video-title">' +
                        escapeHtml(v.title) +
                        "</h3></div>",
                    v.description ? '<p class="video-description">' + escapeHtml(v.description) + "</p>" : "",
                    '<div class="video-player-wrapper"><video class="video-player" data-blob-id="' +
                        escapeHtml(v.blob_id || "") +
                        '" data-fallback-url="' +
                        escapeHtml(v.url || "") +
                        '" controls playsinline webkit-playsinline preload="metadata" x-webkit-airplay="allow">' +
                        (v.url
                            ? '<source src="' +
                              escapeHtml(v.url) +
                              '" type="' +
                              videoMimeFromUrl(v.url) +
                              '">'
                            : "") +
                        "თქვენი ბრაუზერი ვიდეოს არ იგებს.</video></div>",
                    "</article>",
                ].join("");
            })
            .join("");

        list.querySelectorAll(".video-player").forEach(function (video) {
            var blobId = video.getAttribute("data-blob-id");
            var fallbackUrl = video.getAttribute("data-fallback-url");
            if (!blobId) {
                if (fallbackUrl) video.src = fallbackUrl;
                return;
            }
            getVideoBlob(blobId).then(function (blob) {
                if (blob) {
                    video.src = URL.createObjectURL(blob);
                    return;
                }
                if (fallbackUrl) video.src = fallbackUrl;
            }).catch(function () {
                if (fallbackUrl) video.src = fallbackUrl;
            });
        });
    }

    function initAdminPage() {
        var loginView = document.getElementById("admin-login-view");
        var dashView = document.getElementById("admin-dashboard-view");
        if (!loginView || !dashView) return;

        var loginForm = document.getElementById("admin-login-form");
        var message = document.getElementById("admin-auth-message");
        var logoutBtn = document.getElementById("admin-logout-btn");
        var list = document.getElementById("admin-videos-list");
        var statBasic = document.getElementById("admin-stat-basic");
        var statPlus = document.getElementById("admin-stat-plus");
        var statPro = document.getElementById("admin-stat-pro");

        var serverPayload = window.__ADMIN_PAYLOAD__;
        var useServerAdmin =
            serverPayload != null &&
            typeof serverPayload === "object" &&
            Object.prototype.hasOwnProperty.call(serverPayload, "showDashboard");

        function paintServerSalesStats(stats) {
            stats = stats || {};
            if (statBasic) statBasic.textContent = (Number(stats.basic) || 0) + " გაყიდვა";
            if (statPlus) statPlus.textContent = (Number(stats.plus) || 0) + " გაყიდვა";
            if (statPro) statPro.textContent = (Number(stats.premium) || 0) + " გაყიდვა";
        }

        function packSelectHtml(selectedPack) {
            var packs = [
                { id: "basic", label: "საწყისი" },
                { id: "plus", label: "Plus" },
                { id: "premium", label: "Premium" },
            ];
            return packs
                .map(function (p) {
                    return (
                        '<option value="' +
                        escapeHtml(p.id) +
                        '"' +
                        (p.id === selectedPack ? " selected" : "") +
                        ">" +
                        escapeHtml(p.label) +
                        "</option>"
                    );
                })
                .join("");
        }

        function paintServerVideoList(videos) {
            if (!list) return;
            if (!videos || !videos.length) {
                list.innerHTML =
                    '<li style="padding:0.5rem 0;color:#9ca3af;">ვიდეოები ჯერ არ არის ატვირთული.</li>';
                return;
            }
            list.innerHTML = videos
                .map(function (v) {
                    var idAttr = escapeHtml(String(v.id));
                    var safeTitle = escapeHtml(v.title || "");
                    var safeDesc = escapeHtml(v.description || "");
                    var order = Number(v.order_index || 1);
                    var fn = escapeHtml(v.filename || "");
                    var pk = v.pack_id || "basic";
                    return [
                        '<li style="padding:0.8rem 0;border-bottom:1px solid rgba(148,163,184,0.2);">',
                        '<p style="font-size:0.75rem;color:#9ca3af;margin:0 0 0.5rem;word-break:break-all;">ფაილი: ',
                        fn,
                        "</p>",
                        '<form method="post" action="/admin/update_video/',
                        idAttr,
                        '" style="margin-bottom:0.5rem;">',
                        '<div style="display:grid;grid-template-columns:2fr 1fr 100px;gap:0.6rem;margin-bottom:0.6rem;">',
                        '<input type="text" name="title" required value="' +
                            safeTitle +
                            '" placeholder="სათაური">',
                        "<select name=\"pack_id\">" + packSelectHtml(pk) + "</select>",
                        '<input type="number" name="order_index" min="1" value="' +
                            order +
                            '">',
                        "</div>",
                        '<textarea name="description" rows="2" placeholder="აღწერა" style="width:100%;margin-bottom:0.6rem;">',
                        safeDesc,
                        "</textarea>",
                        '<button type="submit" class="btn-primary">შენახვა</button>',
                        "</form>",
                        '<form method="post" action="/admin/delete_video/',
                        idAttr,
                        '" style="display:inline-block;margin-left:0.5rem;" onsubmit="return confirm(\'წავშალოთ ეს ვიდეო?\');">',
                        '<button type="submit" class="btn-secondary">წაშლა</button>',
                        "</form>",
                        "</li>",
                    ].join("");
                })
                .join("");
        }

        if (useServerAdmin) {
            loginView.style.display = serverPayload.showDashboard ? "none" : "block";
            dashView.style.display = serverPayload.showDashboard ? "block" : "none";
            var flashBox = document.getElementById("admin-server-flash");
            if (
                flashBox &&
                serverPayload.flashes &&
                serverPayload.flashes.length
            ) {
                flashBox.style.display = "block";
                flashBox.innerHTML = serverPayload.flashes
                    .map(function (f) {
                        var cat = (f.category || "").toString();
                        var cls =
                            cat === "error"
                                ? "error"
                                : cat === "success"
                                  ? "success"
                                  : "info";
                        return (
                            '<p class="auth-message ' +
                            cls +
                            '" style="margin:0.35rem 0;padding:0.5rem 0.75rem;border-radius:0.5rem;">' +
                            escapeHtml(f.message) +
                            "</p>"
                        );
                    })
                    .join("");
            }
            var diagBar = document.getElementById("admin-diag-banner");
            if (diagBar && serverPayload.showDashboard && serverPayload.diag) {
                var d = serverPayload.diag;
                var sub =
                    "DB: " +
                    (d.database || "?") +
                    " · Vercel: " +
                    (d.vercel ? "yes" : "no") +
                    " · შეამოწმე /healthz სხვა ტელეფონიდან";
                if (d.alert) {
                    diagBar.style.display = "block";
                    diagBar.innerHTML =
                        '<div class="auth-message error" style="padding:0.75rem 1rem;border-radius:0.75rem;">' +
                        "<strong>ყურადღება</strong>" +
                        '<p style="margin:0.35rem 0 0;font-size:0.9rem;">' +
                        escapeHtml(d.alert) +
                        "</p>" +
                        '<p style="margin:0.45rem 0 0;font-size:0.78rem;color:#9ca3af;">' +
                        escapeHtml(sub) +
                        "</p></div>";
                } else {
                    diagBar.style.display = "block";
                    diagBar.innerHTML =
                        '<div style="padding:0.5rem 0.85rem;border-radius:0.75rem;background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.35);font-size:0.82rem;color:#86efac;">' +
                        escapeHtml(sub) +
                        "</div>";
                }
            } else if (diagBar && !serverPayload.showDashboard) {
                diagBar.style.display = "none";
                diagBar.innerHTML = "";
            }
            if (serverPayload.showDashboard) {
                paintServerSalesStats(serverPayload.stats);
                paintServerVideoList(serverPayload.videos);
            }
            if (logoutBtn) {
                logoutBtn.addEventListener("click", function () {
                    localStorage.removeItem(STORAGE_ADMIN);
                    window.location.href = "/admin/logout";
                });
            }
            return;
        }

        function paintSalesStats() {
            var accounts = getAccounts();
            var basic = accounts.filter(function (a) { return userHasPack(a, "basic"); }).length;
            var plus = accounts.filter(function (a) { return userHasPack(a, "plus"); }).length;
            var premium = accounts.filter(function (a) {
                return userHasPack(a, "premium") || userHasPack(a, "pro");
            }).length;
            if (statBasic) statBasic.textContent = basic + " გაყიდვა";
            if (statPlus) statPlus.textContent = plus + " გაყიდვა";
            if (statPro) statPro.textContent = premium + " გაყიდვა";
        }

        function normalizeVideoOrder() {
            var videos = getVideos().slice().sort(function (a, b) {
                return Number(a.order_index || 0) - Number(b.order_index || 0);
            });
            videos = videos.map(function (v, i) {
                v.order_index = i + 1;
                return v;
            });
            setVideos(videos);
            return videos;
        }

        function moveVideo(id, direction) {
            var videos = normalizeVideoOrder();
            var index = videos.findIndex(function (v) { return v.id === id; });
            if (index < 0) return;
            var target = index + direction;
            if (target < 0 || target >= videos.length) return;
            var tmp = videos[index];
            videos[index] = videos[target];
            videos[target] = tmp;
            videos = videos.map(function (v, i) {
                v.order_index = i + 1;
                return v;
            });
            setVideos(videos);
            paintVideoList();
        }

        function paintVideoList() {
            if (!list) return;
            var videos = normalizeVideoOrder();
            if (!videos.length) {
                list.innerHTML = '<li style="padding:0.5rem 0;color:#9ca3af;">ვიდეოები ჯერ არ არის ატვირთული.</li>';
                return;
            }

            list.innerHTML = videos.map(function (v, index) {
                var id = escapeHtml(v.id);
                var safeTitle = escapeHtml(v.title || "");
                var safeDesc = escapeHtml(v.description || "");
                var order = Number(v.order_index || index + 1);
                return [
                    '<li style="padding:0.8rem 0;border-bottom:1px solid rgba(148,163,184,0.2);" data-row-id="' + id + '">',
                    '<div style="display:grid;grid-template-columns:2fr 1fr 100px;gap:0.6rem;margin-bottom:0.6rem;">',
                    '<input type="text" class="admin-video-title" value="' + safeTitle + '" placeholder="სათაური">',
                    '<select class="admin-video-pack"><option value="basic">Basic</option><option value="plus">Plus</option><option value="premium">Premium</option></select>',
                    '<input type="number" class="admin-video-order" min="1" value="' + order + '">',
                    '</div>',
                    '<textarea class="admin-video-desc" rows="2" placeholder="აღწერა" style="width:100%;margin-bottom:0.6rem;">' + safeDesc + '</textarea>',
                    '<div style="display:flex;gap:0.5rem;flex-wrap:wrap;">',
                    '<button class="btn-primary admin-save-video" data-video-id="' + id + '">შენახვა</button>',
                    '<button class="btn-outline admin-move-up" data-video-id="' + id + '">ზემოთ</button>',
                    '<button class="btn-outline admin-move-down" data-video-id="' + id + '">ქვემოთ</button>',
                    '<button class="btn-secondary admin-delete-video" data-video-id="' + id + '">წაშლა</button>',
                    '</div>',
                    '</li>'
                ].join("");
            }).join("");

            list.querySelectorAll(".admin-video-pack").forEach(function (selectEl, idx) {
                selectEl.value = videos[idx].pack_id || "basic";
            });

            list.querySelectorAll(".admin-save-video").forEach(function (btn) {
                btn.addEventListener("click", function () {
                    var id = btn.getAttribute("data-video-id");
                    var row = list.querySelector('[data-row-id="' + id + '"]');
                    if (!row) return;
                    var titleEl = row.querySelector(".admin-video-title");
                    var packEl = row.querySelector(".admin-video-pack");
                    var orderEl = row.querySelector(".admin-video-order");
                    var descEl = row.querySelector(".admin-video-desc");
                    var current = getVideos();
                    var updated = current.map(function (v) {
                        if (v.id !== id) return v;
                        return {
                            id: v.id,
                            title: (titleEl ? titleEl.value : v.title) || "ვიდეო",
                            description: (descEl ? descEl.value : v.description) || "",
                            pack_id: (packEl ? packEl.value : v.pack_id) || "basic",
                            order_index: Math.max(1, Number(orderEl ? orderEl.value : v.order_index) || 1),
                            blob_id: v.blob_id || "",
                            url: v.url || ""
                        };
                    });
                    setVideos(updated);
                    paintVideoList();
                });
            });

            list.querySelectorAll(".admin-delete-video").forEach(function (btn) {
                btn.addEventListener("click", function () {
                    var id = btn.getAttribute("data-video-id");
                    var current = getVideos();
                    var toDelete = current.find(function (v) { return v.id === id; });
                    var updated = current.filter(function (v) { return v.id !== id; });
                    setVideos(updated);
                    deleteVideoBlob(toDelete && toDelete.blob_id ? toDelete.blob_id : "").finally(function () {
                        paintVideoList();
                    });
                });
            });

            list.querySelectorAll(".admin-move-up").forEach(function (btn) {
                btn.addEventListener("click", function () {
                    moveVideo(btn.getAttribute("data-video-id"), -1);
                });
            });

            list.querySelectorAll(".admin-move-down").forEach(function (btn) {
                btn.addEventListener("click", function () {
                    moveVideo(btn.getAttribute("data-video-id"), 1);
                });
            });
        }

        function paintAdmin() {
            var isAdmin = localStorage.getItem(STORAGE_ADMIN) === "1";
            loginView.style.display = isAdmin ? "none" : "block";
            dashView.style.display = isAdmin ? "block" : "none";
            if (isAdmin) {
                paintSalesStats();
                paintVideoList();
            }
        }

        if (loginForm) {
            loginForm.addEventListener("submit", function (e) {
                // If admin form is configured to submit to the server, allow the default POST.
                var action = (loginForm.getAttribute("action") || "").trim();
                if (action) return;

                e.preventDefault();
                var data = new FormData(loginForm);
                var username = (data.get("username") || "").toString().trim();
                var password = (data.get("password") || "").toString().trim();
                if (username === "admin" && password === "yestour111") {
                    localStorage.setItem(STORAGE_ADMIN, "1");
                    paintAdmin();
                    return;
                }
                if (message) {
                    message.style.display = "block";
                    message.className = "auth-message error";
                    message.textContent = "არასწორი მონაცემებია. მომხმარებელი: admin, პაროლი: yestour111";
                }
            });
        }

        if (logoutBtn) {
            logoutBtn.addEventListener("click", function () {
                localStorage.removeItem(STORAGE_ADMIN);
                window.location.href = "/admin/logout";
            });
        }

        paintAdmin();
    }

    function escapeHtml(text) {
        return String(text || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function init() {
        ensureSystemAccounts();
        ensureLegacyUserMigrated();
        initBackground();
        initFaq();
        initAuthModal();
        initPricingActions();
        initCoursePage();
        initAdminPage();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();

