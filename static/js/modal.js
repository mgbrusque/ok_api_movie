(function () {
    function ModalController(options) {
        const {
            elements,
            fetcher,
            fallbackThumb,
            getLang,
            t,
            applyImgFallback,
            safePushState,
            getCsrfToken,
            onAuthRequired
        } = options;

        let currentVideoId = null;
        let currentVideoTitle = "";
        let translate = t;
        let authenticated = false;

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
            qualitySelect,
            adminPanel,
            checkFormatsBtn,
            jdQualitySelect,
            sendJdBtn,
            adminDownloadStatus
        } = elements;

        function parseResponse(response) {
            return response.json()
                .catch(() => ({}))
                .then(data => ({ ok: response.ok, status: response.status, data }));
        }

        function setAdminStatus(message, state) {
            if (!adminDownloadStatus) return;
            adminDownloadStatus.textContent = message || "";
            adminDownloadStatus.dataset.state = state || "";
        }

        function resetAdminUI() {
            if (jdQualitySelect) {
                jdQualitySelect.innerHTML = "";
                const option = document.createElement("option");
                option.value = "";
                option.textContent = translate("optionCheckFormatsFirst");
                jdQualitySelect.appendChild(option);
                jdQualitySelect.disabled = true;
            }
            if (sendJdBtn) sendJdBtn.disabled = true;
            if (checkFormatsBtn) {
                checkFormatsBtn.disabled = false;
                checkFormatsBtn.textContent = translate("buttonCheckFormats");
            }
            setAdminStatus("", "");
        }

        function formatBytes(bytes) {
            const value = Number(bytes || 0);
            if (!value) return "";
            const megabytes = value / (1024 * 1024);
            return megabytes >= 1024 ? `${(megabytes / 1024).toFixed(1)} GB` : `${Math.round(megabytes)} MB`;
        }

        function renderFormats(formats) {
            if (!jdQualitySelect || !sendJdBtn) return;
            jdQualitySelect.innerHTML = "";
            if (!formats || !formats.length) {
                const option = document.createElement("option");
                option.value = "";
                option.textContent = translate("noDirectFormats");
                jdQualitySelect.appendChild(option);
                jdQualitySelect.disabled = true;
                sendJdBtn.disabled = true;
                setAdminStatus(translate("noDirectFormatsHelp"), "error");
                return;
            }
            formats.forEach(format => {
                const option = document.createElement("option");
                option.value = format.format_id;
                const details = [format.ext ? String(format.ext).toUpperCase() : "", formatBytes(format.filesize)]
                    .filter(Boolean)
                    .join(" · ");
                option.textContent = `${format.height}p${details ? ` — ${details}` : ""}`;
                jdQualitySelect.appendChild(option);
            });
            jdQualitySelect.disabled = false;
            sendJdBtn.disabled = false;
            setAdminStatus(translate("formatsReady").replace("{count}", formats.length), "success");
        }

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
            resetAdminUI();
            carregarInfoImdb(videoId, safeTitle, thumb);
            safePushState(`?video=${videoId}`);
        }

        function close() {
            modal.style.display = "none";
            videoFrame.src = "";
            currentVideoId = null;
            currentVideoTitle = "";
            resetImdbUI();
            resetAdminUI();
            safePushState(window.location.pathname);
        }

        function handleCheckFormats() {
            if (!currentVideoId || !authenticated || !checkFormatsBtn) return;
            checkFormatsBtn.disabled = true;
            checkFormatsBtn.textContent = translate("checkingFormats");
            if (sendJdBtn) sendJdBtn.disabled = true;
            setAdminStatus(translate("checkingFormatsHelp"), "loading");
            fetcher(`/admin/formats/${encodeURIComponent(currentVideoId)}`, { credentials: "same-origin" })
                .then(parseResponse)
                .then(({ ok, status, data }) => {
                    if (status === 401) {
                        if (onAuthRequired) onAuthRequired();
                        throw new Error("authentication required");
                    }
                    if (!ok) throw new Error(data.error || translate("formatsError"));
                    renderFormats(data.formats || []);
                })
                .catch(error => {
                    if (error.message !== "authentication required") {
                        setAdminStatus(error.message || translate("formatsError"), "error");
                    }
                })
                .finally(() => {
                    checkFormatsBtn.disabled = false;
                    checkFormatsBtn.textContent = translate("buttonCheckFormats");
                });
        }

        function handleSendToJd() {
            if (!currentVideoId || !authenticated || !sendJdBtn || !jdQualitySelect.value) return;
            sendJdBtn.disabled = true;
            sendJdBtn.textContent = translate("sendingToJd");
            setAdminStatus(translate("sendingToJdHelp"), "loading");
            fetcher("/admin/jdownloader", {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRF-Token": getCsrfToken ? getCsrfToken() : ""
                },
                body: JSON.stringify({
                    video_id: currentVideoId,
                    format_id: jdQualitySelect.value,
                    title: currentVideoTitle || modalTitle.innerText || ""
                })
            })
                .then(parseResponse)
                .then(({ ok, status, data }) => {
                    if (status === 401 || data.code === "csrf_invalid") {
                        if (onAuthRequired) onAuthRequired();
                        throw new Error(translate("authSessionInvalid"));
                    }
                    if (!ok) throw new Error(data.error || translate("sendJdError"));
                    const resolution = data.height ? ` (${data.height}p)` : "";
                    setAdminStatus(`${translate("sendJdSuccess")}${resolution}`, "success");
                })
                .catch(error => setAdminStatus(error.message || translate("sendJdError"), "error"))
                .finally(() => {
                    sendJdBtn.disabled = !jdQualitySelect.value;
                    sendJdBtn.textContent = translate("buttonSendJd");
                });
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
            if (checkFormatsBtn && !checkFormatsBtn.disabled) {
                checkFormatsBtn.textContent = translate("buttonCheckFormats");
            }
            if (sendJdBtn && sendJdBtn.textContent !== translate("sendingToJd")) {
                sendJdBtn.textContent = translate("buttonSendJd");
            }
        }

        function setAuthState(authState) {
            authenticated = Boolean(authState && authState.authenticated);
            if (adminPanel) adminPanel.hidden = !authenticated;
            resetAdminUI();
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
            if (checkFormatsBtn) checkFormatsBtn.addEventListener("click", handleCheckFormats);
            if (sendJdBtn) sendJdBtn.addEventListener("click", handleSendToJd);
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
            refreshLanguage,
            setAuthState
        };
    }

    window.ModalController = ModalController;
})();
