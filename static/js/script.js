document.addEventListener("DOMContentLoaded", function () {
    const searchForm = document.getElementById("searchForm");
    const videoResults = document.getElementById("videoResults");
    const totalResults = document.getElementById("totalResults");
    const modal = document.getElementById("videoModal");
    const modalTitle = document.getElementById("modalTitle");
    const videoFrame = document.getElementById("videoFrame");
    const closeBtn = document.querySelector(".close");
    const toggleThemeBtn = document.getElementById("toggle-theme");

    let offset = 0;
    let loading = false;
    let totalCount = 0;
    const idsExibidos = new Set(); // IDs já exibidos na tela

    function coletarFiltros() {
        const fonte = document.getElementById("fonte").value;
        if (fonte === "API") {
          return {
            fonte,
            duration: document.getElementById("duration").value,
            hd: document.getElementById("hd").checked ? "ON" : ""
          };
        }
        // Banco
        return {
          fonte,
          duration_bd: document.getElementById("duration_bd").value,
          order_bd:    document.getElementById("order_bd").value
        };
      }      

    function alternarFiltros() {
        const fonte = document.getElementById("fonte").value;
        document.getElementById("filters-api").style.display = fonte === "API" ? "flex" : "none";
        document.getElementById("filters-bd").style.display  = fonte === "BD"  ? "flex" : "none";
      }
      document.getElementById("fonte").addEventListener("change", alternarFiltros);
      window.addEventListener("DOMContentLoaded", alternarFiltros);


    function buscarVideos(queryText, novaBusca = false, filtros = {}) {
        if (loading || !queryText) return;
        loading = true;

        if (novaBusca) {
            offset = 0;
            idsExibidos.clear(); // limpa os IDs exibidos se for nova busca
            videoResults.innerHTML = "";
        }

        const params = new URLSearchParams({ query: queryText, offset, fonte: filtros.fonte });
        Object.entries(filtros).forEach(([k,v]) => { if (k !== "fonte" && v !== "") params.append(k,v); });

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

                data.videos.forEach(video => {
                    // Evita vídeos duplicados na tela
                    if (idsExibidos.has(video.id)) return;

                    const videoCard = document.createElement("div");
                    videoCard.classList.add("video-card");
                    videoCard.innerHTML = `
                        <img src="${video.thumbnail}" alt="${video.title}" class="video-thumbnail">
                        <h3 class="video-title">${video.title}</h3>
                        <p class="video-duration">⏳ ${video.duration}</p>
                        <button class="watch-btn" data-id="${video.id}" data-title="${video.title}">Assistir</button>
                    `;
                    videoResults.appendChild(videoCard);
                    idsExibidos.add(video.id); // Marca o ID como exibido
                });

                document.querySelectorAll(".watch-btn").forEach(button => {
                    button.addEventListener("click", function () {
                        const videoId = this.getAttribute("data-id");
                        const title = this.getAttribute("data-title");

                        modalTitle.innerText = title;
                        videoFrame.src = `https://ok.ru/videoembed/${videoId}`;
                        modal.style.display = "flex";
                        history.pushState(null, '', `?video=${videoId}`);
                    });
                });

                offset += data.videos.length;
                loading = false;
            })
            .catch(error => {
                console.error("❌ Erro ao buscar vídeos:", error);
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

    // filtros exclusivos do Banco
    ["duration_bd", "order_bd"].forEach(id => {
        document.getElementById(id).addEventListener("change", () => {
        const queryInput = document.getElementById("query").value.trim();
        const filtros = coletarFiltros();
        buscarVideos(queryInput, true, filtros);
        });
    });

    closeBtn.addEventListener("click", function () {
        modal.style.display = "none";
        videoFrame.src = "";
        history.pushState(null, '', window.location.pathname);
    });

    window.addEventListener("click", function (event) {
        if (event.target === modal) {
            modal.style.display = "none";
            videoFrame.src = "";
            history.pushState(null, '', window.location.pathname);
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

    // Tema
    toggleThemeBtn.addEventListener("change", function () {
        document.body.classList.toggle("light-mode");
        localStorage.setItem("theme", document.body.classList.contains("light-mode") ? "light" : "dark");
    });

    if (localStorage.getItem("theme") === "light") {
        document.body.classList.add("light-mode");
        toggleThemeBtn.checked = true;
    }

    // Correção do modal no carregamento direto por link
    const urlParams = new URLSearchParams(window.location.search);
    const videoIdParam = urlParams.get('video');

    if (videoIdParam) {
        modalTitle.innerText = "Carregando vídeo...";
        videoFrame.src = `https://ok.ru/videoembed/${videoIdParam}`;
        modal.style.display = "flex";
    }

    modal.style.display = "none";
});
