(function () {
    function AuthController(options) {
        const { elements, fetcher, t } = options;
        let translate = t;
        let state = {
            authenticated: false,
            configured: true,
            username: null,
            csrfToken: ""
        };
        const listeners = [];

        const {
            loginBtn,
            logoutBtn,
            authUsername,
            loginModal,
            closeLoginBtn,
            loginForm,
            usernameInput,
            passwordInput,
            loginSubmitBtn,
            loginStatus
        } = elements;

        function errorKey(code) {
            const keys = {
                auth_not_configured: "authNotConfigured",
                too_many_attempts: "authTooManyAttempts",
                invalid_credentials: "authInvalidCredentials",
                csrf_invalid: "authSessionInvalid"
            };
            return keys[code] || "authGenericError";
        }

        function parseResponse(response) {
            return response.json()
                .catch(() => ({}))
                .then(data => ({ ok: response.ok, status: response.status, data }));
        }

        function notify() {
            const snapshot = Object.assign({}, state);
            listeners.forEach(listener => listener(snapshot));
        }

        function render() {
            if (loginBtn) loginBtn.hidden = state.authenticated;
            if (logoutBtn) logoutBtn.hidden = !state.authenticated;
            if (authUsername) {
                authUsername.hidden = !state.authenticated;
                authUsername.textContent = state.authenticated ? (state.username || "admin") : "";
            }
        }

        function setState(data) {
            state = {
                authenticated: Boolean(data && data.authenticated),
                configured: !data || data.configured !== false,
                username: data && data.username ? data.username : null,
                csrfToken: data && data.csrf_token ? data.csrf_token : state.csrfToken
            };
            render();
            notify();
        }

        function openLogin() {
            if (!loginModal) return;
            loginStatus.textContent = state.configured ? "" : translate("authNotConfigured");
            loginStatus.dataset.state = state.configured ? "" : "error";
            loginModal.style.display = "flex";
            loginModal.setAttribute("aria-hidden", "false");
            window.setTimeout(() => usernameInput && usernameInput.focus(), 0);
        }

        function closeLogin() {
            if (!loginModal) return;
            loginModal.style.display = "none";
            loginModal.setAttribute("aria-hidden", "true");
            if (passwordInput) passwordInput.value = "";
            if (loginStatus) {
                loginStatus.textContent = "";
                loginStatus.dataset.state = "";
            }
        }

        function refreshStatus() {
            return fetcher("/auth/status", { credentials: "same-origin" })
                .then(parseResponse)
                .then(({ ok, data }) => {
                    if (!ok) throw new Error("auth status failed");
                    setState(data);
                    return Object.assign({}, state);
                })
                .catch(() => {
                    setState({ authenticated: false, configured: true });
                    return Object.assign({}, state);
                });
        }

        function handleLogin(event) {
            event.preventDefault();
            if (!loginSubmitBtn) return;
            loginSubmitBtn.disabled = true;
            loginSubmitBtn.textContent = translate("authSigningIn");
            loginStatus.textContent = "";
            loginStatus.dataset.state = "";

            fetcher("/auth/login", {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRF-Token": state.csrfToken
                },
                body: JSON.stringify({
                    username: usernameInput.value.trim(),
                    password: passwordInput.value
                })
            })
                .then(parseResponse)
                .then(({ ok, data }) => {
                    if (!ok) {
                        const minutes = Math.max(1, Math.ceil(Number(data.retry_after || 0) / 60));
                        loginStatus.textContent = translate(errorKey(data.code)).replace("{minutes}", minutes);
                        loginStatus.dataset.state = "error";
                        if (data.csrf_token) state.csrfToken = data.csrf_token;
                        return;
                    }
                    setState(data);
                    closeLogin();
                })
                .catch(() => {
                    loginStatus.textContent = translate("authGenericError");
                    loginStatus.dataset.state = "error";
                })
                .finally(() => {
                    loginSubmitBtn.disabled = false;
                    loginSubmitBtn.textContent = translate("buttonLogin");
                });
        }

        function handleLogout() {
            fetcher("/auth/logout", {
                method: "POST",
                credentials: "same-origin",
                headers: { "X-CSRF-Token": state.csrfToken }
            })
                .then(parseResponse)
                .then(({ ok, data }) => {
                    if (!ok) throw new Error("logout failed");
                    setState(data);
                })
                .catch(() => window.alert(translate("authLogoutError")));
        }

        function bindEvents() {
            if (loginBtn) loginBtn.addEventListener("click", openLogin);
            if (logoutBtn) logoutBtn.addEventListener("click", handleLogout);
            if (closeLoginBtn) closeLoginBtn.addEventListener("click", closeLogin);
            if (loginForm) loginForm.addEventListener("submit", handleLogin);
            if (loginModal) {
                loginModal.addEventListener("click", event => {
                    if (event.target === loginModal) closeLogin();
                });
            }
            document.addEventListener("keydown", event => {
                if (event.key === "Escape" && loginModal && loginModal.style.display === "flex") {
                    closeLogin();
                }
            });
        }

        function subscribe(listener) {
            listeners.push(listener);
            listener(Object.assign({}, state));
        }

        function refreshLanguage(newT) {
            translate = newT;
        }

        bindEvents();
        render();
        refreshStatus();

        return {
            getCsrfToken: () => state.csrfToken,
            getState: () => Object.assign({}, state),
            openLogin,
            refreshLanguage,
            refreshStatus,
            subscribe
        };
    }

    window.AuthController = AuthController;
})();
