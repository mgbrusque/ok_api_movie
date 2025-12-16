(function () {
    function ModalController(options) {
        const {
            elements,
            fetcher,
            fallbackThumb,
            getLang,
            t,
            applyImgFallback,
            safePushState
        } = options;

        let currentVideoId = null;
        let currentVideoTitle = "";
        let translate = t;

        const {
            modal,
            modalTitle,
            videoFrame,
            imdbInfo,
            imdbPoster,
            imdbTitle,
            imdbGenres,
            imdbScore,
            imdbSynopsis,
            imdbLoading,
            closeBtn,
            downloadBtn,
            qualitySelect
        } = elements;

        function resetImdbUI() {
            if (!imdbLoading || !imdbInfo) return;
            imdbLoading.style.display = "block";
            imdbLoading.dataset.state = "loading";
            imdbLoading.textContent = translate("imdbLoading");
            imdbInfo.style.display = "none";
            if (imdbPoster) {
                imdbPoster.src = "";
                imdbPoster.style.display = "none";
            }
            if (imdbTitle) imdbTitle.textContent = "";
            if (imdbGenres) imdbGenres.textContent = "";
            if (imdbScore) {
                imdbScore.textContent = "";
                imdbScore.style.display = "none";
                imdbScore.dataset.score = "";
            }
            if (imdbSynopsis) imdbSynopsis.textContent = "";
        }

        function showImdbNotFound() {
            if (!imdbLoading || !imdbInfo) return;
            imdbLoading.style.display = "none";
            imdbLoading.dataset.state = "empty";
            imdbInfo.style.display = "none";
        }

        function renderImdbInfo(data) {
            if (!imdbLoading || !imdbInfo) return;
            const hasContent = data && !data.empty && (data.titulo || data.sinopse || data.imagem || data.nota || data.generos);
            if (!hasContent) {
                showImdbNotFound();
                return;
            }
            imdbLoading.style.display = "none";
            imdbLoading.dataset.state = "done";
            imdbInfo.style.display = "grid";
            if ((!currentVideoTitle || modalTitle.innerText === translate("loadingVideo")) && data.titulo) {
                currentVideoTitle = data.titulo;
                modalTitle.innerText = data.titulo;
            }
            if (imdbTitle) imdbTitle.textContent = data.titulo || currentVideoTitle || "";
            if (imdbGenres) imdbGenres.textContent = data.generos || "";
            if (imdbScore) {
                const scoreVal = data.nota ? `IMDb ${data.nota}` : "";
                imdbScore.textContent = scoreVal;
                imdbScore.dataset.score = scoreVal;
                imdbScore.style.display = scoreVal ? "inline-flex" : "none";
            }
            if (imdbPoster) {
                if (data.imagem) {
                    imdbPoster.src = data.imagem;
                    imdbPoster.style.display = "block";
                } else {
                    imdbPoster.style.display = "none";
                    imdbPoster.removeAttribute("src");
                }
                applyImgFallback(imdbPoster, fallbackThumb);
            }
            if (imdbSynopsis) imdbSynopsis.textContent = data.sinopse || "";
        }

        function carregarInfoImdb(videoId, title, thumb) {
            if (!imdbLoading || !imdbInfo) return;
            resetImdbUI();
            if (!videoId) {
                showImdbNotFound();
                return;
            }
            const params = new URLSearchParams();
            if (title) params.append("title", title);
            if (thumb) params.append("thumb", thumb);
            if (getLang) params.append("lang", getLang());
            fetcher(`/info/${encodeURIComponent(videoId)}?${params.toString()}`)
                .then(res => res.json().then(data => ({ ok: res.ok, data })))
                .then(({ ok, data }) => {
                    if (!ok || !data) {
                        showImdbNotFound();
                        return;
                    }
                    renderImdbInfo(data);
                })
                .catch(() => {
                    showImdbNotFound();
                });
        }

        function open(videoId, title, thumb) {
            currentVideoId = videoId;
            currentVideoTitle = title || "";
            const safeTitle = title || "";
            modalTitle.innerText = safeTitle || translate("loadingVideo");
            videoFrame.src = `https://ok.ru/videoembed/${videoId}`;
            modal.style.display = "flex";
            if (downloadBtn && !downloadBtn.disabled) {
                downloadBtn.textContent = translate("buttonDownload");
            }
            carregarInfoImdb(videoId, safeTitle, thumb);
            safePushState(`?video=${videoId}`);
        }

        function close() {
            modal.style.display = "none";
            videoFrame.src = "";
            currentVideoId = null;
            currentVideoTitle = "";
            resetImdbUI();
            safePushState(window.location.pathname);
        }

        function handleDownload() {
            if (!currentVideoId || !downloadBtn) return;
            downloadBtn.disabled = true;
            downloadBtn.textContent = translate("preparingDownload");
            const qual = qualitySelect ? qualitySelect.value : "";
            const url = qual ? `/download/${encodeURIComponent(currentVideoId)}?h=${qual}` : `/download/${encodeURIComponent(currentVideoId)}`;
            fetcher(url)
                .then(res => res.json().then(data => ({ ok: res.ok, data })))
                .then(({ ok, data }) => {
                    downloadBtn.disabled = false;
                    downloadBtn.textContent = translate("buttonDownload");
                    if (!ok || !data || data.error || !data.url) {
                        alert(data && data.error ? data.error : translate("downloadErrorGeneric"));
                        return;
                    }
                    if (data.streaming) {
                        alert(translate("downloadStreamingOnly"));
                        return;
                    }
                    const a = document.createElement("a");
                    a.href = data.url;
                    a.target = "_blank";
                    a.download = `${(currentVideoTitle || "video").replace(/[^a-z0-9_-]+/gi, "_")}.mp4`;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                })
                .catch(() => {
                    downloadBtn.disabled = false;
                    downloadBtn.textContent = translate("buttonDownload");
                    alert(translate("downloadFail"));
                });
        }

        function refreshLanguage(newT) {
            translate = newT;
            if (imdbLoading) {
                const state = imdbLoading.dataset.state;
                if (state === "loading") imdbLoading.textContent = translate("imdbLoading");
                if (state === "empty") imdbLoading.textContent = translate("imdbNotFound");
            }
            if (downloadBtn && !downloadBtn.disabled) {
                downloadBtn.textContent = translate("buttonDownload");
            }
        }

        function bindEvents() {
            if (closeBtn) closeBtn.addEventListener("click", close);
            window.addEventListener("click", function (event) {
                if (event.target === modal) {
                    close();
                }
            });
            if (downloadBtn) {
                downloadBtn.addEventListener("click", handleDownload);
            }
            const videoIdParam = new URLSearchParams(window.location.search).get("video");
            if (videoIdParam) {
                open(videoIdParam, "", "");
            } else {
                modal.style.display = "none";
            }
        }

        bindEvents();

        return {
            open,
            close,
            refreshLanguage
        };
    }

    window.ModalController = ModalController;
})();
