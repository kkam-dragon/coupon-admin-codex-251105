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
    const roles = JSON.parse(localStorage.getItem("userRoles") || "[]");
    if (!roles.includes("ADMIN")) {
        alert("관리자만 접근할 수 있는 페이지입니다. 메인 화면으로 이동합니다.");
        window.location.href = "sendCoupon.html";
        return;
    }

    const form = document.getElementById("userForm");
    const resultBox = document.getElementById("resultMessage");
    const submitButton = form.querySelector("button[type='submit']");

    const showMessage = (message, type = "success") => {
        resultBox.textContent = message;
        resultBox.className = `alert alert-${type}`;
        resultBox.classList.remove("d-none");
    };

    const inputFilters = {
        username: {
            pattern: /[^A-Za-z0-9]/g,
            maxLength: 15,
            message: "로그인 ID는 영문/숫자 조합 15자 이내여야 합니다.",
        },
        password: {
            pattern: /[^A-Za-z0-9!@#$%^&*()_+\-=\[\]{};':"\\|,.<>/?`~]/g,
            maxLength: 15,
            message: "비밀번호는 영문/숫자/특수문자 조합 15자 이내여야 합니다.",
        },
        name: {
            pattern: /[^A-Za-z가-힣]/g,
            maxLength: 15,
            message: "이름은 한글 또는 영문 15자 이내로 입력하세요.",
        },
        email: {
            pattern: /[^A-Za-z0-9@._-]/g,
            message: "이메일은 영문/숫자/@/./_/ -만 입력할 수 있습니다.",
        },
        phone: {
            pattern: /[^0-9]/g,
            message: "휴대폰 번호는 숫자만 입력할 수 있습니다.",
        },
    };

    const validators = {
        username: (value) => /^[A-Za-z0-9]{1,15}$/.test(value),
        password: (value) => /^[A-Za-z0-9!@#$%^&*()_+\-=\[\]{};':"\\|,.<>/?`~]{8,15}$/.test(value),
        name: (value) => !value || /^[A-Za-z가-힣]{1,15}$/.test(value),
        email: (value) => !value || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
        phone: (value) => !value || /^\d+$/.test(value),
    };

    const validate = (payload) => {
        if (!validators.username(payload.username)) {
            showMessage("로그인 ID는 영문/숫자 조합 15자 이내여야 합니다.", "warning");
            return false;
        }
        if (!validators.password(payload.password)) {
            showMessage("비밀번호는 영문/숫자/특수문자 구성 8~15자여야 합니다.", "warning");
            return false;
        }
        if (!validators.name(payload.name)) {
            showMessage("이름은 한글 또는 영문 15자 이내로 입력하세요.", "warning");
            return false;
        }
        if (!validators.email(payload.email)) {
            showMessage("올바른 이메일 형식이 아닙니다.", "warning");
            return false;
        }
        if (!validators.phone(payload.phone)) {
            showMessage("휴대폰 번호는 숫자만 입력할 수 있습니다.", "warning");
            return false;
        }
        return true;
    };

    const applyInputFilter = (fieldId, rule) => {
        const input = document.getElementById(fieldId);
        if (!input || !rule) {
            return;
        }
        let isComposing = false;
        const sanitize = () => {
            let value = input.value;
            const original = value;
            if (rule.pattern) {
                value = value.replace(rule.pattern, "");
            }
            if (rule.maxLength) {
                value = value.slice(0, rule.maxLength);
            }
            if (value !== original) {
                input.value = value;
                showMessage(rule.message, "warning");
            }
        };

        input.addEventListener("compositionstart", () => {
            isComposing = true;
        });
        input.addEventListener("compositionend", () => {
            isComposing = false;
            sanitize();
        });
        input.addEventListener("input", () => {
            if (isComposing) {
                return;
            }
            sanitize();
        });
    };

    Object.keys(inputFilters).forEach((key) => applyInputFilter(key, inputFilters[key]));

    const togglePasswordBtn = document.getElementById("togglePassword");
    const passwordInput = document.getElementById("password");
    if (togglePasswordBtn && passwordInput) {
        togglePasswordBtn.addEventListener("click", () => {
            const type = passwordInput.getAttribute("type") === "password" ? "text" : "password";
            passwordInput.setAttribute("type", type);
            togglePasswordBtn.querySelector("i")?.classList.toggle("fa-eye");
            togglePasswordBtn.querySelector("i")?.classList.toggle("fa-eye-slash");
        });
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const payload = {
            username: document.getElementById("username").value.trim(),
            password: document.getElementById("password").value,
            name: document.getElementById("name").value.trim(),
            email: document.getElementById("email").value.trim(),
            phone: document.getElementById("phone").value.trim(),
            status: document.getElementById("status").value,
        };

        if (!validate(payload)) {
            return;
        }

        payload.name = payload.name || null;
        payload.email = payload.email || null;
        payload.phone = payload.phone || null;

        const token = window.localStorage?.getItem("accessToken") || "";
        if (!token) {
            showMessage("로그인 정보가 만료되었습니다. 다시 로그인해 주세요.", "warning");
            return;
        }

        submitButton.disabled = true;
        submitButton.textContent = "등록 중...";

        try {
            const apiBase = resolveApiBase();
            const response = await fetch(`${apiBase}/users`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const data = await response.json().catch(() => ({}));
                throw new Error(data.detail || "사용자 등록에 실패했습니다.");
            }

            const data = await response.json();
            showMessage(`사용자(${data.username})가 등록되었습니다.`, "success");
            form.reset();
        } catch (error) {
            showMessage(error.message || "알 수 없는 오류가 발생했습니다.", "danger");
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = "사용자 등록";
        }
    });
});
