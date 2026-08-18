/* ToomMED live chat UX
   Uses the backend streaming endpoint so the UI can show real progress.
   The timer proves the request is still alive; once the first token arrives,
   the status changes from Thinking to Generating.
*/

(function () {
    "use strict";

    function install() {
        const input = document.getElementById("msg-input");
        const send = document.getElementById("send-btn");
        const messages = document.getElementById("messages");

        if (!input || !send || !messages) {
            console.error("ToomMED: chat elements not found.");
            return;
        }

        const patientId = () => window.currentPatientId;

        function scrollToBottom() {
            messages.scrollTop = messages.scrollHeight;
        }

        function addUserMessage(text) {
            const row = document.createElement("div");
            row.className = "message user";
            row.innerHTML = `
                <div class="message-content">
                    <div class="message-bubble"></div>
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
                        <div class="live-thinking">
                            <span class="live-spinner">✚</span>
                            <span class="live-status">ToomMED is thinking...</span>
                            <span class="live-time">0s</span>
                        </div>
                    </div>
                </div>
            `;
            messages.appendChild(row);
            scrollToBottom();
            return row;
        }

        function addAssistantMessage() {
            const row = document.createElement("div");
            row.className = "message assistant";
            row.innerHTML = `
                <div class="message-avatar">✚</div>
                <div class="message-content">
                    <div class="message-bubble"></div>
                    <div class="message-label">ToomMED</div>
                </div>
            `;
            messages.appendChild(row);
            return row;
        }

        async function reliableSendMessage() {
            const text = input.value.trim();
            const id = patientId();

            if (!text) return;
            if (!id) {
                alert("Select a patient first.");
                return;
            }

            input.value = "";
            input.style.height = "auto";
            input.disabled = true;
            send.disabled = true;

            const empty = document.getElementById("empty-state");
            if (empty) empty.remove();

            addUserMessage(text);
            const thinking = addThinkingMessage();
            const status = thinking.querySelector(".live-status");
            const timerLabel = thinking.querySelector(".live-time");
            const started = Date.now();
            let timer = setInterval(() => {
                timerLabel.textContent = `${Math.floor((Date.now() - started) / 1000)}s`;
                scrollToBottom();
            }, 250);

            try {
                const response = await fetch(`/patients/${id}/chat`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "text/plain"
                    },
                    body: JSON.stringify({ message: text, stream: true })
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(errorText || `HTTP ${response.status}`);
                }

                if (!response.body) {
                    throw new Error("Streaming is not supported by this browser.");
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let reply = "";
                let gotFirstToken = false;
                let assistantRow = null;
                let assistantBubble = null;

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value, { stream: true });
                    if (!chunk) continue;

                    if (!gotFirstToken) {
                        gotFirstToken = true;
                        status.textContent = "ToomMED is generating...";
                        thinking.querySelector(".live-spinner").classList.add("generating");
                    }

                    reply += chunk;

                    if (!assistantRow) {
                        assistantRow = addAssistantMessage();
                        assistantBubble = assistantRow.querySelector(".message-bubble");
                    }

                    assistantBubble.textContent = reply;
                    scrollToBottom();
                }

                const finalChunk = decoder.decode();
                if (finalChunk) {
                    reply += finalChunk;
                    if (!assistantRow) {
                        assistantRow = addAssistantMessage();
                        assistantBubble = assistantRow.querySelector(".message-bubble");
                    }
                    assistantBubble.textContent = reply;
                }

                thinking.remove();

                if (!assistantRow) {
                    assistantRow = addAssistantMessage();
                    assistantRow.querySelector(".message-bubble").textContent = "No response received.";
                }

                const lower = reply.toLowerCase();
                if (lower.includes("emergency")) {
                    const banner = document.getElementById("emergency-banner");
                    if (banner) banner.classList.add("visible");
                    assistantRow.classList.add("emergency");
                }

                scrollToBottom();

                if (typeof window.loadFacts === "function") {
                    window.loadFacts().catch(console.error);
                }

            } catch (error) {
                thinking.remove();
                const row = addAssistantMessage();
                row.querySelector(".message-avatar").textContent = "!";
                row.querySelector(".message-bubble").textContent =
                    `Unable to get a response. ${error.message}`;
                console.error("ToomMED chat error:", error);
                scrollToBottom();
            } finally {
                clearInterval(timer);
                input.disabled = false;
                send.disabled = false;
                input.focus();
            }
        }

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

        console.log("ToomMED live streaming chat installed.");
    }

    const style = document.createElement("style");
    style.textContent = `
        .thinking-bubble { padding: 11px 14px !important; }
        .live-thinking {
            display: flex;
            align-items: center;
            gap: 9px;
            min-height: 25px;
            color: var(--muted);
            font-size: 11px;
            white-space: nowrap;
        }
        .live-spinner {
            width: 25px;
            height: 25px;
            border-radius: 8px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: var(--primary-soft);
            color: var(--primary);
            font-size: 15px;
            animation: toommed-spin 0.9s linear infinite;
        }
        .live-spinner.generating { animation-duration: .45s; }
        .live-status { font-weight: 600; }
        .live-time {
            color: var(--muted-light);
            min-width: 22px;
            font-variant-numeric: tabular-nums;
        }
        @keyframes toommed-spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(style);

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", install);
    } else {
        install();
    }
})();
