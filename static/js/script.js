document.addEventListener("DOMContentLoaded", function () {
    const searchForm = document.getElementById("searchForm");
    const videoResults = document.getElementById("videoResults");
    const totalResults = document.getElementById("totalResults");
    const modal = document.getElementById("videoModal");
    const modalTitle = document.getElementById("modalTitle");
    const videoFrame = document.getElementById("videoFrame");
    const closeBtn = document.querySelector(".close");
    const downloadBtn = document.getElementById("downloadBtn");
    const langOptions = document.querySelectorAll(".lang-option");

    const translations = {
        pt: {
            appTitle: "Busca de Vídeos",
            labelLanguage: "Idioma:",
            optionLangPt: "Português (BR)",
            optionLangEn: "English (US)",
            optionLangEs: "Español",
            labelSource: "Fonte:",
            optionSourceApi: "API",
            optionSourceDb: "Banco",
            labelDurationApi: "Duração:",
            optionDurationAny: "Qualquer duração",
            optionDurationLong: "Longo",
            optionDurationShort: "Curto",
            labelHd: "HD:",
            labelDurationBd: "Duração:",
            optionDurationBdAll: "Todas",
            optionDurationBd0_20: "0-20 min",
            optionDurationBd21_60: "21-60 min",
            optionDurationBd61_90: "61-90 min",
            optionDurationBd91_120: "91-120 min",
            optionDurationBd121_160: "121-160 min",
            optionDurationBd161_200: "161-200 min",
            optionDurationBd201Plus: "> 201 min",
            labelOrder: "Ordem:",
            optionOrderTimeDesc: "Tempo decrescente",
            optionOrderTimeAsc: "Tempo crescente",
            optionOrderNameAsc: "Nome A-Z",
            optionOrderNameDesc: "Nome Z-A",
            optionOrderRandom: "Aleatório",
            placeholderSearch: "Digite o que deseja buscar...",
            buttonSearch: "Buscar",
            totalLabel: "TOTAL",
            durationLabel: "Duração",
            watchButton: "Assistir",
            labelQuality: "Qualidade:",
            optionQualityAuto: "Auto (melhor)",
            buttonDownload: "Baixar vídeo",
            preparingDownload: "Preparando...",
            downloadErrorGeneric: "Não foi possível gerar o link de download.",
            downloadStreamingOnly: "Download não disponível: este vídeo só tem streaming (m3u8/DASH).",
            downloadFail: "Falha ao obter link de download.",
            loadingVideo: "Carregando vídeo...",
            searchError: "Erro ao buscar vídeos"
        },
        en: {
            appTitle: "Video Search",
            labelLanguage: "Language:",
            optionLangPt: "Portuguese (BR)",
            optionLangEn: "English (US)",
            optionLangEs: "Spanish",
            labelSource: "Source:",
            optionSourceApi: "API",
            optionSourceDb: "Database",
            labelDurationApi: "Duration:",
            optionDurationAny: "Any duration",
            optionDurationLong: "Long",
            optionDurationShort: "Short",
            labelHd: "HD:",
            labelDurationBd: "Duration:",
            optionDurationBdAll: "All",
            optionDurationBd0_20: "0-20 min",
            optionDurationBd21_60: "21-60 min",
            optionDurationBd61_90: "61-90 min",
            optionDurationBd91_120: "91-120 min",
            optionDurationBd121_160: "121-160 min",
            optionDurationBd161_200: "161-200 min",
            optionDurationBd201Plus: "> 201 min",
            labelOrder: "Order:",
            optionOrderTimeDesc: "Time descending",
            optionOrderTimeAsc: "Time ascending",
            optionOrderNameAsc: "Name A-Z",
            optionOrderNameDesc: "Name Z-A",
            optionOrderRandom: "Random",
            placeholderSearch: "Type what you want to search...",
            buttonSearch: "Search",
            totalLabel: "TOTAL",
            durationLabel: "Duration",
            watchButton: "Watch",
            labelQuality: "Quality:",
            optionQualityAuto: "Auto (best)",
            buttonDownload: "Download video",
            preparingDownload: "Preparing...",
            downloadErrorGeneric: "Could not generate the download link.",
            downloadStreamingOnly: "Download not available: this video is streaming-only (m3u8/DASH).",
            downloadFail: "Failed to get download link.",
            loadingVideo: "Loading video...",
            searchError: "Error searching videos"
        },
        es: {
            appTitle: "Búsqueda de Videos",
            labelLanguage: "Idioma:",
            optionLangPt: "Portugués (BR)",
            optionLangEn: "Inglés (EE.UU.)",
            optionLangEs: "Español",
            labelSource: "Fuente:",
            optionSourceApi: "API",
            optionSourceDb: "Base de datos",
            labelDurationApi: "Duración:",
            optionDurationAny: "Cualquier duración",
            optionDurationLong: "Largo",
            optionDurationShort: "Corto",
            labelHd: "HD:",
            labelDurationBd: "Duración:",
            optionDurationBdAll: "Todas",
            optionDurationBd0_20: "0-20 min",
            optionDurationBd21_60: "21-60 min",
            optionDurationBd61_90: "61-90 min",
            optionDurationBd91_120: "91-120 min",
            optionDurationBd121_160: "121-160 min",
            optionDurationBd161_200: "161-200 min",
            optionDurationBd201Plus: "> 201 min",
            labelOrder: "Orden:",
            optionOrderTimeDesc: "Tiempo descendente",
            optionOrderTimeAsc: "Tiempo ascendente",
            optionOrderNameAsc: "Nombre A-Z",
            optionOrderNameDesc: "Nombre Z-A",
            optionOrderRandom: "Aleatorio",
            placeholderSearch: "Escribe lo que quieres buscar...",
            buttonSearch: "Buscar",
            totalLabel: "TOTAL",
            durationLabel: "Duración",
            watchButton: "Ver",
            labelQuality: "Calidad:",
            optionQualityAuto: "Auto (mejor)",
            buttonDownload: "Descargar video",
            preparingDownload: "Preparando...",
            downloadErrorGeneric: "No fue posible generar el enlace de descarga.",
            downloadStreamingOnly: "Descarga no disponible: este video solo tiene streaming (m3u8/DASH).",
            downloadFail: "Fallo al obtener el enlace de descarga.",
            loadingVideo: "Cargando video...",
            searchError: "Error al buscar videos"
        }
    };

    // Helpers para compatibilidade em navegadores mais antigos (ex.: WebOS).
    function createIdStore() {
        if (typeof Set !== "undefined") {
            return new Set();
        }
        return {
            _data: {},
            add(id) { this._data[id] = true; },
            has(id) { return !!this._data[id]; },
            clear() { this._data = {}; }
        };
    }

    const hasNativeFetch = typeof window.fetch === "function";
    function safeFetch(url, options) {
        if (hasNativeFetch) {
            return window.fetch(url, options);
        }
        return new Promise((resolve, reject) => {
            try {
                const xhr = new XMLHttpRequest();
                const method = (options && options.method) ? options.method : "GET";
                xhr.open(method, url);
                if (options && options.headers) {
                    Object.keys(options.headers).forEach(key => {
                        xhr.setRequestHeader(key, options.headers[key]);
                    });
                }
                xhr.onload = function () {
                    const text = xhr.responseText || "";
                    resolve({
                        ok: xhr.status >= 200 && xhr.status < 300,
                        status: xhr.status,
                        statusText: xhr.statusText,
                        text: () => Promise.resolve(text),
                        json: () => Promise.resolve().then(() => JSON.parse(text))
                    });
                };
                xhr.onerror = function () {
                    reject(new Error("Network error"));
                };
                xhr.send(options && options.body ? options.body : null);
            } catch (err) {
                reject(err);
            }
        });
    }

    function buildFormBody(obj) {
        if (typeof URLSearchParams !== "undefined") {
            const params = new URLSearchParams();
            Object.keys(obj).forEach(key => {
                const value = obj[key];
                if (value !== undefined && value !== null) {
                    params.append(key, value);
                }
            });
            return params.toString();
        }
        const pairs = [];
        Object.keys(obj).forEach(key => {
            const value = obj[key];
            if (value !== undefined && value !== null) {
                pairs.push(encodeURIComponent(key) + "=" + encodeURIComponent(value));
            }
        });
        return pairs.join("&");
    }

    function getQueryParam(name) {
        if (typeof URLSearchParams !== "undefined") {
            const urlParams = new URLSearchParams(window.location.search);
            return urlParams.get(name);
        }
        const search = window.location.search ? window.location.search.replace(/^\?/, "") : "";
        const parts = search.split("&");
        for (let i = 0; i < parts.length; i++) {
            const segment = parts[i].split("=");
            if (decodeURIComponent(segment[0]) === name) {
                return decodeURIComponent(segment[1] || "");
            }
        }
        return null;
    }

    function safePushState(url) {
        if (window.history && typeof window.history.pushState === "function") {
            history.pushState(null, "", url);
        }
    }

    let currentLang = localStorage.getItem("lang") || "pt";
    if (!translations[currentLang]) currentLang = "pt";

    let offset = 0;
    let loading = false;
    let totalCount = 0;
    const idsExibidos = createIdStore();
    let currentVideoId = null;
    let currentVideoTitle = "";

    function t(key) {
        if (translations[currentLang] && translations[currentLang][key]) {
            return translations[currentLang][key];
        }
        if (translations.pt && translations.pt[key]) {
            return translations.pt[key];
        }
        return key;
    }

    function refreshVideoCardsLanguage() {
        const durationLabel = t("durationLabel");
        document.querySelectorAll(".video-duration").forEach(el => {
            const durationValue = el.getAttribute("data-duration-value") || "";
            el.textContent = durationValue ? `${durationLabel}: ${durationValue}` : durationLabel;
        });

        document.querySelectorAll(".watch-btn").forEach(btn => {
            btn.textContent = t("watchButton");
        });

        if (downloadBtn && !downloadBtn.disabled) {
            downloadBtn.textContent = t("buttonDownload");
        }
    }

    function updateTotalResults(newCount) {
        if (typeof newCount === "number") {
            totalCount = newCount;
        }
        if (totalResults) {
            totalResults.innerHTML = `${t("totalLabel")}: <b>${totalCount}</b>`;
        }
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

        refreshVideoCardsLanguage();
        updateTotalResults();
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

    if (langOptions.length) {
        langOptions.forEach(btn => {
            btn.addEventListener("click", () => setLanguage(btn.dataset.lang));
        });
    }

    updateLangButtonsUI();
    applyTranslations();

    function coletarFiltros() {
        const fonte = document.getElementById("fonte").value;
        if (fonte === "API") {
            return {
                fonte,
                duration: document.getElementById("duration").value,
                hd: document.getElementById("hd").checked ? "ON" : ""
            };
        }
        return {
            fonte,
            duration_bd: document.getElementById("duration_bd").value,
            order_bd: document.getElementById("order_bd").value
        };
    }

    function alternarFiltros() {
        const fonte = document.getElementById("fonte").value;
        document.getElementById("filters-api").style.display = fonte === "API" ? "flex" : "none";
        document.getElementById("filters-bd").style.display = fonte === "BD" ? "flex" : "none";
    }

    document.getElementById("fonte").addEventListener("change", () => {
        alternarFiltros();
        const queryInput = document.getElementById("query").value.trim();
        const filtros = coletarFiltros();
        buscarVideos(queryInput, true, filtros);
    });
    alternarFiltros();

    function abrirModal(videoId, title) {
        currentVideoId = videoId;
        currentVideoTitle = title || "";
        modalTitle.innerText = title || t("loadingVideo");
        videoFrame.src = `https://ok.ru/videoembed/${videoId}`;
        modal.style.display = "flex";
        if (downloadBtn && !downloadBtn.disabled) {
            downloadBtn.textContent = t("buttonDownload");
        }
        safePushState(`?video=${videoId}`);
    }

    function limparModal() {
        modal.style.display = "none";
        videoFrame.src = "";
        currentVideoId = null;
        currentVideoTitle = "";
        safePushState(window.location.pathname);
    }

    function solicitarDownload(videoId, title) {
        if (!videoId || !downloadBtn) return;
        downloadBtn.disabled = true;
        downloadBtn.textContent = t("preparingDownload");
        const qualityEl = document.getElementById("qualitySelect");
        const qual = qualityEl ? qualityEl.value : "";
        const url = qual ? `/download/${encodeURIComponent(videoId)}?h=${qual}` : `/download/${encodeURIComponent(videoId)}`;
        safeFetch(url)
            .then(res => res.json().then(data => ({ ok: res.ok, data })))
            .then(({ ok, data }) => {
                downloadBtn.disabled = false;
                downloadBtn.textContent = t("buttonDownload");
                if (!ok || !data || data.error || !data.url) {
                    alert(data && data.error ? data.error : t("downloadErrorGeneric"));
                    return;
                }
                if (data.streaming) {
                    alert(t("downloadStreamingOnly"));
                    return;
                }
                const a = document.createElement("a");
                a.href = data.url;
                a.target = "_blank";
                a.download = `${(title || "video").replace(/[^a-z0-9_-]+/gi, "_")}.mp4`;
                document.body.appendChild(a);
                a.click();
                a.remove();
            })
            .catch(() => {
                downloadBtn.disabled = false;
                downloadBtn.textContent = t("buttonDownload");
                alert(t("downloadFail"));
            });
    }

    function adicionarVideoCard(video) {
        if (idsExibidos.has(video.id)) return;

        const videoCard = document.createElement("div");
        videoCard.classList.add("video-card");
        const durationText = t("durationLabel");
        const watchText = t("watchButton");
        videoCard.innerHTML = `
            <img src="${video.thumbnail}" alt="${video.title}" class="video-thumbnail">
            <h3 class="video-title">${video.title}</h3>
            <p class="video-duration" data-duration-value="${video.duration}">${durationText}: ${video.duration}</p>
            <div class="card-actions">
                <button class="watch-btn" data-id="${video.id}" data-title="${video.title}">${watchText}</button>
            </div>
        `;

        const watchBtn = videoCard.querySelector(".watch-btn");
        watchBtn.addEventListener("click", () => abrirModal(video.id, video.title));

        videoResults.appendChild(videoCard);
        idsExibidos.add(video.id);
    }

    function buscarVideos(queryText, novaBusca = false, filtros = {}) {
        if (loading || !queryText) return;
        loading = true;

        if (novaBusca) {
            offset = 0;
            idsExibidos.clear();
            videoResults.innerHTML = "";
        }

        const paramsObj = { query: queryText, offset, fonte: filtros.fonte };
        Object.entries(filtros).forEach(([k, v]) => {
            if (k !== "fonte" && v !== "") {
                paramsObj[k] = v;
            }
        });
        const body = buildFormBody(paramsObj);

        safeFetch("/buscar", {
            method: "POST",
            body: body,
            headers: { "Content-Type": "application/x-www-form-urlencoded" }
        })
            .then(response => response.json())
            .then(data => {
                if (novaBusca) {
                    updateTotalResults(data.totalCount);
                }

                data.videos.forEach(adicionarVideoCard);

                offset += data.videos.length;
                loading = false;
            })
            .catch(error => {
                console.error(t("searchError"), error);
                loading = false;
            });
    }

    searchForm.addEventListener("submit", function (event) {
        event.preventDefault();
        const queryInput = document.getElementById("query").value.trim();
        const filtros = coletarFiltros();
        buscarVideos(queryInput, true, filtros);
    });

    document.getElementById("duration").addEventListener("change", () => {
        const queryInput = document.getElementById("query").value.trim();
        const filtros = coletarFiltros();
        buscarVideos(queryInput, true, filtros);
    });

    document.getElementById("hd").addEventListener("change", () => {
        const queryInput = document.getElementById("query").value.trim();
        const filtros = coletarFiltros();
        buscarVideos(queryInput, true, filtros);
    });

    ["duration_bd", "order_bd"].forEach(id => {
        document.getElementById(id).addEventListener("change", () => {
            const queryInput = document.getElementById("query").value.trim();
            const filtros = coletarFiltros();
            buscarVideos(queryInput, true, filtros);
        });
    });

    closeBtn.addEventListener("click", limparModal);

    window.addEventListener("click", function (event) {
        if (event.target === modal) {
            limparModal();
        }
    });

    window.addEventListener("scroll", function () {
        if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 200 && !loading) {
            const queryInput = document.getElementById("query").value.trim();
            if (queryInput) {
                const filtros = coletarFiltros();
                buscarVideos(queryInput, false, filtros);
            }
        }
    });

    if (downloadBtn) {
        downloadBtn.addEventListener("click", () => solicitarDownload(currentVideoId, currentVideoTitle));
    }

    const videoIdParam = getQueryParam("video");
    if (videoIdParam) {
        abrirModal(videoIdParam, t("loadingVideo"));
    } else {
        modal.style.display = "none";
    }
});
