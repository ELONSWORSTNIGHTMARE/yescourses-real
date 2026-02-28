document.addEventListener("DOMContentLoaded", () => {
    const circlesContainer = document.getElementById("circles-container");
    if (circlesContainer) {
        const circleCount = 12;
        for (let i = 0; i < circleCount; i++) {
            const circle = document.createElement("div");
            circle.className = "circle";
            const size = 120 + Math.random() * 260;
            const duration = 22 + Math.random() * 14;
            const delay = Math.random() * -duration;
            circle.style.width = `${size}px`;
            circle.style.height = `${size}px`;
            circle.style.left = `${Math.random() * 100}%`;
            circle.style.top = `${Math.random() * 100}%`;
            circle.style.animationDuration = `${duration}s`;
            circle.style.animationDelay = `${delay}s`;
            circlesContainer.appendChild(circle);
        }
    }

    const faqItems = document.querySelectorAll(".faq-item");
    faqItems.forEach((item) => {
        const btn = item.querySelector(".faq-question");
        btn.addEventListener("click", () => {
            const isOpen = item.classList.contains("open");
            faqItems.forEach((i) => i.classList.remove("open"));
            if (!isOpen) item.classList.add("open");
        });
    });

    const authModal = document.getElementById("auth-modal");
    const openAuth = document.getElementById("open-auth-modal");
    const closeAuth = document.getElementById("close-auth-modal");
    const heroStartBtn = document.getElementById("hero-start-btn");

    function showModal() {
        if (authModal) authModal.classList.remove("hidden");
    }

    function hideModal() {
        if (authModal) authModal.classList.add("hidden");
    }

    if (openAuth) openAuth.addEventListener("click", showModal);
    if (heroStartBtn) heroStartBtn.addEventListener("click", showModal);
    if (closeAuth) closeAuth.addEventListener("click", hideModal);
    if (authModal) {
        authModal.addEventListener("click", (e) => {
            if (e.target === authModal) hideModal();
        });
    }

    const tabButtons = document.querySelectorAll(".tab-button");
    const tabPanels = document.querySelectorAll(".tab-panel");
    tabButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            const target = btn.dataset.tab;
            tabButtons.forEach((b) => b.classList.remove("active"));
            tabPanels.forEach((p) => p.classList.remove("active"));
            btn.classList.add("active");
            const panel = document.getElementById(target);
            if (panel) panel.classList.add("active");
        });
    });

    const chooseButtons = document.querySelectorAll(".choose-pack");
    chooseButtons.forEach((btn) => {
        btn.addEventListener("click", (e) => {
            const loggedIn = document.querySelector(".user-name") !== null;
            if (!loggedIn) {
                e.preventDefault();
                showModal();
            }
        });
    });
});

