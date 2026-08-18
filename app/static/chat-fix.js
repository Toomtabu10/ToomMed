/* ToomMED UI enhancement
   Leaves the existing chat implementation completely intact.
   Adds a guaranteed visible thinking indicator while a message is being generated.
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

        let thinking = null;
        let thinkingTimer = null;

        function showThinking() {
            if (thinking) return;

            thinking = document.createElement("div");
            thinking.id = "toommed-thinking-status";
            thinking.innerHTML = `
                <span class="toommed-thinking-icon">✚</span>
                <span>ToomMED is thinking<span class="thinking-dots">...</span></span>
            `;

            const composer = document.querySelector(".composer-area");
            if (composer) {
                composer.parentElement.insertBefore(thinking, composer);
            } else {
                messages.appendChild(thinking);
            }

            requestAnimationFrame(() => {
                if (thinking) thinking.classList.add("visible");
            });
        }

        function hideThinking() {
            if (thinkingTimer) {
                clearTimeout(thinkingTimer);
                thinkingTimer = null;
            }
            if (!thinking) return;
            thinking.classList.remove("visible");
            const old = thinking;
            thinking = null;
            setTimeout(() => old.remove(), 180);
        }

        function startThinking() {
            showThinking();

            // If the model responds extremely quickly, keep the indicator visible
            // long enough for the user to actually see it.
            thinkingTimer = setTimeout(() => {}, 120);
        }

        function finishThinking() {
            hideThinking();
        }

        // Mouse/click sending: capture before the existing onclick runs.
        send.addEventListener("click", function () {
            if (input.value.trim() && !send.disabled) {
                startThinking();
            }
        }, true);

        // Enter sending: capture before the existing keydown handler runs.
        input.addEventListener("keydown", function (event) {
            if (event.key === "Enter" && !event.shiftKey && input.value.trim() && !send.disabled) {
                startThinking();
            }
        }, true);

        // The existing sendMessage() creates an assistant bubble. Watch for
        // its first real text and remove the status at that point.
        const observer = new MutationObserver(function () {
            if (!thinking) return;

            const assistantRows = messages.querySelectorAll(".message.assistant");
            if (!assistantRows.length) return;

            const last = assistantRows[assistantRows.length - 1];
            const bubble = last.querySelector(".message-bubble");

            // The built-in thinking bubble has no text. Once Ollama sends the
            // first real chunk, the bubble contains actual response text.
            if (bubble && bubble.textContent.trim()) {
                finishThinking();
            }
        });

        observer.observe(messages, {
            childList: true,
            subtree: true,
            characterData: true
        });

        // Also hide it when the send button becomes enabled again.
        const buttonObserver = new MutationObserver(function () {
            if (thinking && !send.disabled) {
                finishThinking();
            }
        });
        buttonObserver.observe(send, {
            attributes: true,
            attributeFilter: ["disabled"]
        });

        console.log("ToomMED thinking indicator installed.");
    }

    const style = document.createElement("style");
    style.textContent = `
        #toommed-thinking-status {
            width: min(820px, 84%);
            margin: 0 auto;
            min-height: 38px;
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 7px 13px;
            color: var(--muted);
            font-size: 11px;
            opacity: 0;
            transform: translateY(5px);
            transition: opacity .18s ease, transform .18s ease;
            pointer-events: none;
        }

        #toommed-thinking-status.visible {
            opacity: 1;
            transform: translateY(0);
        }

        .toommed-thinking-icon {
            width: 28px;
            height: 28px;
            flex: 0 0 28px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 9px;
            background: var(--primary-soft);
            color: var(--primary);
            font-size: 16px;
            font-weight: 700;
            animation: toommed-thinking-spin 1s linear infinite;
        }

        .thinking-dots {
            display: inline-block;
            width: 18px;
            text-align: left;
            animation: toommed-thinking-pulse 1s steps(4, end) infinite;
        }

        @keyframes toommed-thinking-spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        @keyframes toommed-thinking-pulse {
            0% { opacity: .25; }
            50% { opacity: 1; }
            100% { opacity: .25; }
        }
    `;

    document.head.appendChild(style);

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", install);
    } else {
        install();
    }
})();
