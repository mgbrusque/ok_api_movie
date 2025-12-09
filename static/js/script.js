document.addEventListener("DOMContentLoaded", function () {
    const searchForm = document.getElementById("searchForm");
    const videoResults = document.getElementById("videoResults");
    const totalResults = document.getElementById("totalResults");
    const modal = document.getElementById("videoModal");
    const modalTitle = document.getElementById("modalTitle");
    const videoFrame = document.getElementById("videoFrame");
    const closeBtn = document.querySelector(".close");
    const downloadBtn = document.getElementById("downloadBtn");
    const toggleThemeBtn = document.getElementById("toggle-theme");

    let offset = 0;
    let loading = false;
    let totalCount = 0;
    const idsExibidos = new Set();
    let currentVideoId = null;
    let currentVideoTitle = "";

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
    document.getElementById("fonte").addEventListener("change", alternarFiltros);
    alternarFiltros();

    function abrirModal(videoId, title) {
        currentVideoId = videoId;
        currentVideoTitle = title || "";
        modalTitle.innerText = title;
        videoFrame.src = `https://ok.ru/videoembed/${videoId}`;
        modal.style.display = "flex";
        history.pushState(null, "", `?video=${videoId}`);
    }

    function limparModal() {
        modal.style.display = "none";
        videoFrame.src = "";
        currentVideoId = null;
        currentVideoTitle = "";
        history.pushState(null, "", window.location.pathname);
    }

    function solicitarDownload(videoId, title) {
        if (!videoId || !downloadBtn) return;
        downloadBtn.disabled = true;
        downloadBtn.textContent = "Preparando...";
        const qual = document.getElementById("qualitySelect")?.value || "";
        const url = qual ? `/download/${encodeURIComponent(videoId)}?h=${qual}` : `/download/${encodeURIComponent(videoId)}`;
        fetch(url)
            .then(res => res.json().then(data => ({ ok: res.ok, data })))
            .then(({ ok, data }) => {
                downloadBtn.disabled = false;
                downloadBtn.textContent = "Baixar vídeo";
                if (!ok || !data || data.error || !data.url) {
                    alert(data && data.error ? data.error : "Não foi possível gerar o link de download.");
                    return;
                }
                if (data.streaming) {
                    alert("Download não disponível: este vídeo só tem streaming (m3u8/DASH).");
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
                downloadBtn.textContent = "Baixar vídeo";
                alert("Falha ao obter link de download.");
            });
    }

    function adicionarVideoCard(video) {
        if (idsExibidos.has(video.id)) return;

        const videoCard = document.createElement("div");
        videoCard.classList.add("video-card");
        videoCard.innerHTML = `
            <img src="${video.thumbnail}" alt="${video.title}" class="video-thumbnail">
            <h3 class="video-title">${video.title}</h3>
            <p class="video-duration">Duração: ${video.duration}</p>
            <div class="card-actions">
                <button class="watch-btn" data-id="${video.id}" data-title="${video.title}">Assistir</button>
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

        const params = new URLSearchParams({ query: queryText, offset, fonte: filtros.fonte });
        Object.entries(filtros).forEach(([k, v]) => { if (k !== "fonte" && v !== "") params.append(k, v); });

        fetch("/buscar", {
            method: "POST",
            body: params,
            headers: { "Content-Type": "application/x-www-form-urlencoded" }
        })
            .then(response => response.json())
            .then(data => {
                if (novaBusca) {
                    totalCount = data.totalCount;
                    totalResults.innerHTML = `TOTAL: <b>${totalCount}</b>`;
                }

                data.videos.forEach(adicionarVideoCard);

                offset += data.videos.length;
                loading = false;
            })
            .catch(error => {
                console.error("Erro ao buscar vídeos:", error);
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

    document.getElementById("fonte").addEventListener("change", () => {
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

    toggleThemeBtn.addEventListener("change", function () {
        document.body.classList.toggle("light-mode");
        localStorage.setItem("theme", document.body.classList.contains("light-mode") ? "light" : "dark");
    });

    if (localStorage.getItem("theme") === "light") {
        document.body.classList.add("light-mode");
        toggleThemeBtn.checked = true;
    }

    if (downloadBtn) {
        downloadBtn.addEventListener("click", () => solicitarDownload(currentVideoId, currentVideoTitle));
    }

    const urlParams = new URLSearchParams(window.location.search);
    const videoIdParam = urlParams.get("video");
    if (videoIdParam) {
        abrirModal(videoIdParam, "Carregando vídeo...");
    } else {
        modal.style.display = "none";
    }
});
