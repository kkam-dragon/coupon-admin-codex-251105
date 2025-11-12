const resolveApiBase = () => {
    const stored = window.API_BASE_URL || localStorage.getItem("apiBaseUrl");
    if (stored) {
        return stored.replace(/\/$/, "");
    }
    const origin = window.location.origin;
    if (origin.includes(":5500")) {
        return "http://localhost:8000";
    }
    if (origin.includes(":3000") || origin.includes(":8089")) {
        return "http://localhost:8089";
    }
    return origin.replace(/\/$/, "");
};

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("loginForm");
    const messageBox = document.getElementById("loginMessage");
    const submitBtn = document.getElementById("loginBtn");

    const showMessage = (text, type = "danger") => {
        messageBox.textContent = text;
        messageBox.className = `alert alert-${type}`;
        messageBox.classList.remove("d-none");
    };

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const username = document.getElementById("username").value.trim();
        const password = document.getElementById("password").value;
        if (!username || !password) {
            showMessage("아이디와 비밀번호를 모두 입력하세요.", "warning");
            return;
        }

        submitBtn.disabled = true;
        submitBtn.textContent = "로그인 중...";
        messageBox.classList.add("d-none");

        try {
            const apiBase = resolveApiBase();
            const response = await fetch(`${apiBase}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password }),
            });

            if (!response.ok) {
                const data = await response.json().catch(() => ({}));
                throw new Error(data.detail || "로그인에 실패했습니다.");
            }

            const data = await response.json();
            const { access_token, user } = data;
            localStorage.setItem("accessToken", access_token);
            localStorage.setItem("currentUser", JSON.stringify(user));
            localStorage.setItem("userRoles", JSON.stringify(user?.roles || []));
            window.location.href = "sendCoupon.html";
        } catch (error) {
            showMessage(error.message, "danger");
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = "로그인";
        }
    });
});
