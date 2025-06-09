document.addEventListener("DOMContentLoaded", function () {
    const searchForm = document.getElementById("searchForm");
    const videoResults = document.getElementById("videoResults");
    const totalResults = document.getElementById("totalResults");
    const modal = document.getElementById("videoModal");
    const modalTitle = document.getElementById("modalTitle");
    const videoFrame = document.getElementById("videoFrame");
    const closeBtn = document.querySelector(".close");
    const toggleThemeBtn = document.getElementById("toggle-theme");

    let currentIndex = 0;
    let query = "";
    let offset = 0;
    let loading = false;
    let totalCount = 0;
    let filmes = []; // Inicialmente vazio
    let elementosNavegaveis = [];
    
    function coletarFiltros() {
        return {
            duration: document.getElementById("duration").value,
            hd: document.getElementById("hd").checked ? "ON" : ""
        };
    }
    
    function buscarVideos(novaBusca = false, filtros = {}) {
        if (loading) return;
        loading = true;
    
        if (novaBusca) {
            offset = 0;
            videoResults.innerHTML = "";
        }
    
        const params = new URLSearchParams({
            query,
            offset,
            duration: filtros.duration || "",
            hd: filtros.hd || ""
        });

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

            const videoIdsExistentes = new Set();
            document.querySelectorAll(".watch-btn").forEach(button => {
                videoIdsExistentes.add(button.getAttribute("data-id"));
            });

            let novosVideos = 0;

            data.videos.forEach(video => {
                if (!videoIdsExistentes.has(video.id)) {
                    const videoCard = document.createElement("div");
                    videoCard.classList.add("video-card");
                    videoCard.innerHTML = `
                        <img src="${video.thumbnail}" alt="${video.title}" class="video-thumbnail">
                        <h3 class="video-title">${video.title}</h3> <!-- Aqui foi corrigido -->
                        <p class="video-duration">⏳ ${video.duration}</p>
                        <p class="video-meta">👁 ${video.views} views</p> 
                        <button class="watch-btn" data-id="${video.id}" data-title="${video.title}">Assistir</button>
                    `;
                    videoResults.appendChild(videoCard);
                    novosVideos++;
                }
            });

            document.querySelectorAll(".watch-btn").forEach(button => {
                button.addEventListener("click", function () {
                    const videoId = this.getAttribute("data-id");
                    const title = this.getAttribute("data-title");

                    modalTitle.innerText = title;
                    videoFrame.src = `https://ok.ru/videoembed/${videoId}`;
                    modal.style.display = "flex";  
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
        query = document.getElementById("query").value;
    
        const duration = document.getElementById("duration").value;
        const hd = document.getElementById("hd").checked ? "ON" : "";
    
        buscarVideos(true, { duration, hd });
    });
    
    document.getElementById("duration").addEventListener("change", () => {
        query = document.getElementById("query").value;
        const filtros = coletarFiltros();
        buscarVideos(true, filtros);
    });
    
    document.getElementById("hd").addEventListener("change", () => {
        query = document.getElementById("query").value;
        const filtros = coletarFiltros();
        buscarVideos(true, filtros);
    });
    
    closeBtn.addEventListener("click", function () {
        modal.style.display = "none";
        videoFrame.src = "";
    });

    window.addEventListener("click", function (event) {
        if (event.target === modal) {
            modal.style.display = "none";
            videoFrame.src = "";
        }
    });

    window.addEventListener("scroll", function () {
        if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 200 && !loading) {
            buscarVideos();
        }
    });

    // Alternância de tema
    toggleThemeBtn.addEventListener("change", function () {
        document.body.classList.toggle("light-mode");
        localStorage.setItem("theme", document.body.classList.contains("light-mode") ? "light" : "dark");
    });

    // Mantém o tema salvo do usuário
    if (localStorage.getItem("theme") === "light") {
        document.body.classList.add("light-mode");
        toggleThemeBtn.checked = true;
    }

    // Correção do modal: Certifica que ele está oculto ao carregar a página
    modal.style.display = "none";
});
