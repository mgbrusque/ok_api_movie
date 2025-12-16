const AppUtils = (function () {
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

    function applyImgFallback(imgEl, fallbackUrl) {
        if (!imgEl) return;
        imgEl.addEventListener("error", () => {
            if (imgEl.dataset.fallbackApplied === "1") return;
            imgEl.dataset.fallbackApplied = "1";
            if (fallbackUrl) {
                imgEl.src = fallbackUrl;
            }
        });
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

    return {
        createIdStore,
        applyImgFallback,
        safeFetch,
        buildFormBody,
        getQueryParam,
        safePushState
    };
})();

window.AppUtils = AppUtils;
