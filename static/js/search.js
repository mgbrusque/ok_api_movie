(function () {
    function SearchController(options) {
        const {
            elements,
            fetcher,
            modalController,
            fallbackThumb,
            t
        } = options;

        let translate = t;
        let offset = 0;
        let loading = false;
        let totalCount = 0;
        const idsExibidos = (window.AppUtils && window.AppUtils.createIdStore) ? window.AppUtils.createIdStore() : new Set();

        const {
            searchForm,
            videoResults,
            totalResults,
            fonteSelect,
            durationSelectApi,
            hdCheckbox,
            durationSelectBd,
            orderSelectBd,
            scrollTopBtn
        } = elements;

        function updateTotalResults(newCount) {
            if (typeof newCount === "number") {
                totalCount = newCount;
            }
            if (totalResults) {
                totalResults.innerHTML = `${translate("totalLabel")}: <b>${totalCount}</b>`;
            }
        }

        function refreshVideoCardsLanguage() {
            const durationLabel = translate("durationLabel");
            document.querySelectorAll(".video-duration").forEach(el => {
                const durationValue = el.getAttribute("data-duration-value") || "";
                el.textContent = durationValue ? `${durationLabel}: ${durationValue}` : durationLabel;
            });
            document.querySelectorAll(".watch-btn").forEach(btn => {
                btn.textContent = translate("watchButton");
            });
        }

        function coletarFiltros() {
            const fonte = fonteSelect.value;
            if (fonte === "API") {
                return {
                    fonte,
                    duration: durationSelectApi.value,
                    hd: hdCheckbox.checked ? "ON" : ""
                };
            }
            return {
                fonte,
                duration_bd: durationSelectBd.value,
                order_bd: orderSelectBd.value
            };
        }

        function alternarFiltros() {
            const fonte = fonteSelect.value;
            document.getElementById("filters-api").style.display = fonte === "API" ? "flex" : "none";
            document.getElementById("filters-bd").style.display = fonte === "BD" ? "flex" : "none";
        }

        function adicionarVideoCard(video) {
            if (idsExibidos.has(video.id)) return;
            const videoCard = document.createElement("div");
            videoCard.classList.add("video-card");
            const durationText = translate("durationLabel");
            const watchText = translate("watchButton");
            const thumb = video.thumbnail || fallbackThumb;
            videoCard.innerHTML = `
                <img src="${thumb}" alt="${video.title}" class="video-thumbnail">
                <h3 class="video-title">${video.title}</h3>
                <p class="video-duration" data-duration-value="${video.duration}">${durationText}: ${video.duration}</p>
                <div class="card-actions">
                    <button class="watch-btn" data-id="${video.id}" data-title="${video.title}" data-thumb="${thumb}">${watchText}</button>
                </div>
            `;
            const thumbImg = videoCard.querySelector(".video-thumbnail");
            if (window.AppUtils && window.AppUtils.applyImgFallback) {
                window.AppUtils.applyImgFallback(thumbImg, fallbackThumb);
            }
            const watchBtn = videoCard.querySelector(".watch-btn");
            watchBtn.addEventListener("click", () => modalController.open(video.id, video.title, thumb));
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
            let body = "";
            if (window.AppUtils && window.AppUtils.buildFormBody) {
                body = window.AppUtils.buildFormBody(paramsObj);
            } else {
                const params = new URLSearchParams();
                Object.keys(paramsObj).forEach(key => params.append(key, paramsObj[key]));
                body = params.toString();
            }

            fetcher("/buscar", {
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
                    console.error(translate("searchError"), error);
                    loading = false;
                });
        }

        function bindEvents() {
            searchForm.addEventListener("submit", function (event) {
                event.preventDefault();
                const queryInput = document.getElementById("query").value.trim();
                const filtros = coletarFiltros();
                buscarVideos(queryInput, true, filtros);
            });

            durationSelectApi.addEventListener("change", () => {
                const queryInput = document.getElementById("query").value.trim();
                const filtros = coletarFiltros();
                buscarVideos(queryInput, true, filtros);
            });

            hdCheckbox.addEventListener("change", () => {
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

            fonteSelect.addEventListener("change", () => {
                alternarFiltros();
                const queryInput = document.getElementById("query").value.trim();
                const filtros = coletarFiltros();
                buscarVideos(queryInput, true, filtros);
            });

            window.addEventListener("scroll", function () {
                if (scrollTopBtn) {
                    if (window.scrollY > 280) {
                        scrollTopBtn.classList.add("visible");
                    } else {
                        scrollTopBtn.classList.remove("visible");
                    }
                }
                if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 200 && !loading) {
                    const queryInput = document.getElementById("query").value.trim();
                    if (queryInput) {
                        const filtros = coletarFiltros();
                        buscarVideos(queryInput, false, filtros);
                    }
                }
            });

            if (scrollTopBtn) {
                scrollTopBtn.addEventListener("click", () => {
                    if ("scrollTo" in window) {
                        window.scrollTo({ top: 0, behavior: "smooth" });
                        return;
                    }
                    document.documentElement.scrollTop = 0;
                    document.body.scrollTop = 0;
                });
            }

            alternarFiltros();
        }

        function updateLanguage(newT) {
            translate = newT;
            refreshVideoCardsLanguage();
            updateTotalResults();
        }

        bindEvents();

        return {
            buscarVideos,
            updateLanguage
        };
    }

    window.SearchController = SearchController;
})();
