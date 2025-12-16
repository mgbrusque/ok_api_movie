document.addEventListener("DOMContentLoaded", function () {
    const utils = window.AppUtils || {};
    const translations = window.APP_TRANSLATIONS || {};
    const ModalController = window.ModalController;
    const SearchController = window.SearchController;

    const FALLBACK_THUMB = "https://media.istockphoto.com/id/1306969366/pt/vetorial/no-video-camera-icon-no-video-recording-vector.jpg?s=612x612&w=0&k=20&c=-bxPuvBGcmtH048X8QoQ3mQbIlxnSnItlQKbCeOpkcI=";

    let currentLang = localStorage.getItem("lang") || "pt";
    if (!translations[currentLang]) currentLang = "pt";

    const langOptions = document.querySelectorAll(".lang-option");
    const totalResults = document.getElementById("totalResults");

    function t(key) {
        if (translations[currentLang] && translations[currentLang][key]) {
            return translations[currentLang][key];
        }
        if (translations.pt && translations.pt[key]) {
            return translations.pt[key];
        }
        return key;
    }

    function applyTranslations() {
        document.documentElement.lang = currentLang;
        document.title = t("appTitle");

        document.querySelectorAll("[data-i18n]").forEach(el => {
            const key = el.dataset.i18n;
            if (key) {
                el.textContent = t(key);
            }
        });

        document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
            const key = el.dataset.i18nPlaceholder;
            if (key) {
                el.placeholder = t(key);
            }
        });

        modalController.refreshLanguage(t);
        searchController.updateLanguage(t);
    }

    function updateLangButtonsUI() {
        langOptions.forEach(btn => {
            const lang = btn.dataset.lang;
            btn.classList.toggle("active", lang === currentLang);
        });
    }

    function setLanguage(lang) {
        currentLang = translations[lang] ? lang : "pt";
        localStorage.setItem("lang", currentLang);
        updateLangButtonsUI();
        applyTranslations();
    }

    const modalController = ModalController({
        elements: {
            modal: document.getElementById("videoModal"),
            modalTitle: document.getElementById("modalTitle"),
            videoFrame: document.getElementById("videoFrame"),
            imdbInfo: document.getElementById("imdbInfo"),
            imdbPoster: document.getElementById("imdbPoster"),
            imdbTitle: document.getElementById("imdbTitle"),
            imdbGenres: document.getElementById("imdbGenres"),
            imdbScore: document.getElementById("imdbScore"),
            imdbSynopsis: document.getElementById("imdbSynopsis"),
            imdbLoading: document.getElementById("imdbLoading"),
            closeBtn: document.querySelector(".close"),
            downloadBtn: document.getElementById("downloadBtn"),
            qualitySelect: document.getElementById("qualitySelect"),
        },
        fetcher: utils.safeFetch || window.fetch.bind(window),
        fallbackThumb: FALLBACK_THUMB,
        getLang: () => currentLang,
        t,
        applyImgFallback: utils.applyImgFallback || (() => {}),
        safePushState: utils.safePushState || (() => {})
    });

    const searchController = SearchController({
        elements: {
            searchForm: document.getElementById("searchForm"),
            videoResults: document.getElementById("videoResults"),
            totalResults,
            fonteSelect: document.getElementById("fonte"),
            durationSelectApi: document.getElementById("duration"),
            hdCheckbox: document.getElementById("hd"),
            durationSelectBd: document.getElementById("duration_bd"),
            orderSelectBd: document.getElementById("order_bd"),
            scrollTopBtn: document.getElementById("scrollTopBtn")
        },
        fetcher: utils.safeFetch || window.fetch.bind(window),
        modalController,
        fallbackThumb: FALLBACK_THUMB,
        t
    });

    if (langOptions.length) {
        langOptions.forEach(btn => {
            btn.addEventListener("click", () => setLanguage(btn.dataset.lang));
        });
    }

    updateLangButtonsUI();
    applyTranslations();
});
