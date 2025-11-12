document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("userForm");
    const resultBox = document.getElementById("resultMessage");
    const submitButton = form.querySelector("button[type='submit']");

    const showMessage = (message, type = "success") => {
        resultBox.textContent = message;
        resultBox.className = `alert alert-${type}`;
        resultBox.classList.remove("d-none");
    };

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const payload = {
            username: document.getElementById("username").value.trim(),
            password: document.getElementById("password").value,
            name: document.getElementById("name").value.trim() || null,
            email: document.getElementById("email").value.trim() || null,
            phone: document.getElementById("phone").value.trim() || null,
            status: document.getElementById("status").value,
        };

        const manualToken = document.getElementById("token").value.trim();
        const storedToken = window.localStorage?.getItem("accessToken") || "";
        const token = manualToken || storedToken;
        if (!token) {
            showMessage("Access Token이 필요합니다. 로그인 후 토큰을 입력하세요.", "warning");
            return;
        }

        submitButton.disabled = true;
        submitButton.textContent = "등록 중...";

        try {
            const response = await fetch("/users", {
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
