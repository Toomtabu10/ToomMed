/* ToomMED chat reliability fix
   Uses the existing non-streaming API response for browser compatibility.
   Also provides a rotating medical icon while Ollama is thinking.
*/

(function () {
    "use strict";

    function install() {
        const input = document.getElementById("msg-input");
        const send = document.getElementById("send-btn");
        const messages = document.getElementById("messages");

        if (!input || !send || !messages) {
            console.error("ToomMED chat fix: required elements not found.");
            return;
        }

        function scrollToBottom() {
            messages.scrollTop = messages.scrollHeight;
        }

        function addUserMessage(text) {
            const row = document.createElement("div");
            row.className = "message user";
            row.innerHTML = `
                <div class="message-avatar"></div>
                <div class="message-content">
                    <div class="message-bubble"></div>
                    <div class="message-label">You</div>
                </div>
            `;
            row.querySelector(".message-bubble").textContent = text;
            messages.appendChild(row);
            scrollToBottom();
        }

        function addThinkingMessage() {
            const row = document.createElement("div");
            row.className = "message assistant thinking-message";
            row.innerHTML = `
                <div class="message-avatar thinking-avatar">✚</div>
                <div class="message-content">
                    <div class="message-bubble thinking-bubble">
                        <div class="thinking-indicator">
                            <span class="thinking-spinner">✚</span>
                            <span class="thinking-text">ToomMED is thinking...</span>
                        </div>
                    </div>
                </div>
            `;
            messages.appendChild(row);
            scrollToBottom();
            return row;
        }

        async function reliableSendMessage() {
            const text = input.value.trim();
            const patientId = window.currentPatientId;

            if (!text || !patientId) {
                if (!patientId) alert("Select a patient first.");
                return;
            }

            input.value = "";
            input.style.height = "auto";
            send.disabled = true;
            input.disabled = true;

            const empty = document.getElementById("empty-state");
            if (empty) empty.remove();

            addUserMessage(text);
            const thinking = addThinkingMessage();
            const bubble = thinking.querySelector(".message-bubble");

            try {
                const response = await fetch(`/patients/${patientId}/chat`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    body: JSON.stringify({
                        message: text,
                        stream: false
                    })
                });

                const raw = await response.text();
                let data;

                try {
                    data = JSON.parse(raw);
                } catch (_) {
                    throw new Error(raw || `HTTP ${response.status}`);
                }

                if (!response.ok) {
                    throw new Error(data.detail || data.message || `HTTP ${response.status}`);
                }

                thinking.remove();

                const row = document.createElement("div");
                row.className = "message assistant";
                row.innerHTML = `
                    <div class="message-avatar">✚</div>
                    <div class="message-content">
                        <div class="message-bubble"></div>
                        <div class="message-label">ToomMED</div>
                    </div>
                `;
                row.querySelector(".message-bubble").textContent = data.reply || "No response received.";
                messages.appendChild(row);

                const reply = String(data.reply || "").toLowerCase();
                if (reply.includes("emergency")) {
                    const banner = document.getElementById("emergency-banner");
                    if (banner) banner.classList.add("visible");
                    row.classList.add("emergency");
                }

                scrollToBottom();

                // Refresh facts/history-related UI without disrupting the chat.
                if (typeof window.loadFacts === "function") {
                    window.loadFacts().catch(console.error);
                }

            } catch (error) {
                thinking.remove();

                const row = document.createElement("div");
                row.className = "message assistant";
                row.innerHTML = `
                    <div class="message-avatar">!</div>
                    <div class="message-content">
                        <div class="message-bubble"></div>
                        <div class="message-label">ToomMED</div>
                    </div>
                `;
                row.querySelector(".message-bubble").textContent =
                    `Unable to get a response. ${error.message}`;
                messages.appendChild(row);
                scrollToBottom();
                console.error("ToomMED chat error:", error);
            } finally {
                send.disabled = false;
                input.disabled = false;
                input.focus();
            }
        }

        // Replace the original handler rather than adding a second click handler.
        send.onclick = reliableSendMessage;

        input.onkeydown = function (event) {
            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                reliableSendMessage();
            }
        };

        input.oninput = function () {
            input.style.height = "auto";
            input.style.height = Math.min(input.scrollHeight, 130) + "px";
        };

        // Make currentPatientId accessible to this fix without changing application state.
        if (!Object.prototype.hasOwnProperty.call(window, "currentPatientId")) {
            try {
                Object.defineProperty(window, "currentPatientId", {
                    configurable: true,
                    get: function () {
                        return typeof currentPatientId !== "undefined" ? currentPatientId : null;
                    }
                });
            } catch (_) {}
        }

        console.log("ToomMED chat fix installed.");
    }

    const style = document.createElement("style");
    style.textContent = `
        .thinking-bubble {
            padding: 12px 15px !important;
        }
        .thinking-indicator {
            display: flex;
            align-items: center;
            gap: 9px;
            min-height: 24px;
            color: var(--muted);
            font-size: 12px;
        }
        .thinking-spinner {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 25px;
            height: 25px;
            border-radius: 8px;
            background: var(--primary-soft);
            color: var(--primary);
            font-size: 15px;
            animation: toommed-spin 1s linear infinite;
        }
        .thinking-text {
            animation: toommed-pulse 1.4s ease-in-out infinite;
        }
        @keyframes toommed-spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        @keyframes toommed-pulse {
            0%, 100% { opacity: .55; }
            50% { opacity: 1; }
        }
    `;
    document.head.appendChild(style);

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", install);
    } else {
        install();
    }
})();
