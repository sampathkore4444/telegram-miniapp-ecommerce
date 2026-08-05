/* ShopTrolley — main.js */
(function () {
  "use strict";

  /* ---------- Config ----------
     Signup endpoint. Default: same-origin relay in site/server.py
     which emails the signup via smtplib — no third-party service. */
  const SIGNUP_ENDPOINT = "/api/signup";

  /* ---------- i18n ---------- */
  const SUPPORTED = Object.keys(I18N);
  const saved = localStorage.getItem("st-lang");
  const detected = (navigator.language || "en").toLowerCase().slice(0, 2);
  let current = SUPPORTED.includes(saved) ? saved : SUPPORTED.includes(detected) ? detected : "en";

  const langBtn = document.getElementById("lang-btn");
  const langMenu = document.getElementById("lang-menu");
  const langFlag = document.getElementById("lang-flag");
  const langLabel = document.getElementById("lang-label");

  function applyLang(lang) {
    current = lang;
    localStorage.setItem("st-lang", lang);
    const dict = I18N[lang];
    document.documentElement.lang = LANG_META[lang].htmlLang;
    document.title = dict.meta_title || document.title;
    langFlag.textContent = LANG_META[lang].flag;
    langLabel.textContent = LANG_META[lang].label;
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.dataset.i18n;
      if (dict[key] != null) el.textContent = dict[key];
    });
    document.querySelectorAll("[data-i18n-ph]").forEach((el) => {
      const key = el.dataset.i18nPh;
      if (dict[key] != null) el.placeholder = dict[key];
    });
    langMenu.querySelectorAll("li").forEach((li) => {
      li.classList.toggle("active", li.dataset.lang === lang);
    });
  }

  langBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    const open = langMenu.classList.toggle("open");
    langBtn.setAttribute("aria-expanded", String(open));
  });
  document.addEventListener("click", () => {
    langMenu.classList.remove("open");
    langBtn.setAttribute("aria-expanded", "false");
  });
  langMenu.querySelectorAll("li").forEach((li) => {
    li.addEventListener("click", () => {
      applyLang(li.dataset.lang);
      langMenu.classList.remove("open");
      langBtn.setAttribute("aria-expanded", "false");
    });
  });

  /* ---------- Mobile nav ---------- */
  const burger = document.getElementById("nav-burger");
  const navLinks = document.getElementById("nav-links");
  burger.addEventListener("click", () => navLinks.classList.toggle("open"));
  navLinks.querySelectorAll("a").forEach((a) =>
    a.addEventListener("click", () => navLinks.classList.remove("open"))
  );

  /* ---------- Nav shadow ---------- */
  const nav = document.getElementById("nav");
  const onScroll = () => nav.classList.toggle("scrolled", window.scrollY > 10);
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  /* ---------- FAQ accordion ---------- */
  document.querySelectorAll(".faq-item").forEach((item) => {
    item.querySelector(".faq-q").addEventListener("click", () => {
      const isOpen = item.classList.toggle("open");
      document.querySelectorAll(".faq-item").forEach((o) => {
        if (o !== item) o.classList.remove("open");
      });
      if (!isOpen) return;
    });
  });

  /* ---------- Reveal on scroll ---------- */
  const revealTargets = document.querySelectorAll(
    ".sec-head, .feat, .step, .market, .plan, .quote, .faq-item, .cta-box, .stats, .hero-copy, .hero-visual"
  );
  revealTargets.forEach((el) => el.classList.add("reveal"));
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add("in");
          io.unobserve(e.target);
        }
      });
    },
    { threshold: 0.12 }
  );
  revealTargets.forEach((el) => io.observe(el));

  /* ---------- Signup form ---------- */
  const form = document.getElementById("signup-form");
  if (form) {
    const submitBtn = document.getElementById("signup-submit");
    const errorEl = document.getElementById("form-error");
    const successEl = document.getElementById("signup-success");
    const gridInputs = form.querySelectorAll(".signup-grid input, .signup-grid select");
    const fields = () => ({
      storeName: form.querySelector("#s-store").value.trim(),
      name: form.querySelector("#s-name").value.trim(),
      email: form.querySelector("#s-email").value.trim(),
      market: form.querySelector("#s-market").value,
      telegram: form.querySelector("#s-telegram").value.trim(),
    });

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      errorEl.classList.add("hidden");
      const dict = I18N[current];
      const f = fields();

      if (!f.storeName || !f.name || !f.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email)) {
        errorEl.textContent = dict.signup_val || dict.signup_err;
        errorEl.classList.remove("hidden");
        return;
      }

      submitBtn.disabled = true;
      const payload = {
        store_name: f.storeName,
        name: f.name,
        email: f.email,
        market: f.market,
        telegram: f.telegram,
        language: current,
        _subject: `[ShopTrolley] New signup: ${f.storeName} (${f.market})`,
      };

      try {
        const res = await fetch(SIGNUP_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error("submit failed");
        gridInputs.forEach((el) => (el.disabled = true));
        form.querySelector(".signup-btn").classList.add("hidden");
        form.querySelector(".signup-note").classList.add("hidden");
        successEl.classList.remove("hidden");
        successEl.scrollIntoView({ behavior: "smooth", block: "center" });
      } catch (err) {
        errorEl.textContent = dict.signup_err;
        errorEl.classList.remove("hidden");
      } finally {
        submitBtn.disabled = false;
      }
    });

    document.getElementById("signup-again").addEventListener("click", () => {
      form.reset();
      successEl.classList.add("hidden");
      form.querySelector(".signup-btn").classList.remove("hidden");
      form.querySelector(".signup-note").classList.remove("hidden");
      gridInputs.forEach((el) => (el.disabled = false));
    });
  }

  /* ---------- Footer year ---------- */
  document.getElementById("year").textContent = new Date().getFullYear();

  applyLang(current);
})();
