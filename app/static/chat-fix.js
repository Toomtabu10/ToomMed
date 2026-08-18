/* ToomMED live chat: thinking timer + true progressive streaming. */
(function () {
  "use strict";

  function install() {
    const input = document.getElementById("msg-input");
    const send = document.getElementById("send-btn");
    const messages = document.getElementById("messages");
    if (!input || !send || !messages) return;

    function getPatientId() {
      try { return typeof currentPatientId !== "undefined" ? currentPatientId : null; }
      catch (_) { return null; }
    }

    /* Keep compatibility with the original index.html code. */
    window.scrollMessages = function () {
      messages.scrollTo({ top: messages.scrollHeight, behavior: "smooth" });
    };

    function scroll() {
      messages.scrollTop = messages.scrollHeight;
    }

    function message(role, text) {
      const row = document.createElement("div");
      row.className = `message ${role}`;
      row.innerHTML = `<div class="message-avatar">${role === "assistant" ? "✚" : ""}</div><div class="message-content"><div class="message-bubble"></div><div class="message-label">${role === "assistant" ? "ToomMED" : "You"}</div></div>`;
      row.querySelector(".message-bubble").textContent = text;
      messages.appendChild(row);
      scroll();
      return row;
    }

    function thinking() {
      const row = document.createElement("div");
      row.className = "message assistant thinking-message";
      row.innerHTML = `<div class="message-avatar">✚</div><div class="message-content"><div class="message-bubble"><div class="live-thinking"><span class="live-spinner">✚</span><span class="live-status">ToomMED is thinking...</span><span class="live-time">0s</span></div></div></div>`;
      messages.appendChild(row);
      scroll();

      const status = row.querySelector(".live-status");
      const time = row.querySelector(".live-time");
      const spinner = row.querySelector(".live-spinner");
      const started = Date.now();
      const timer = setInterval(() => {
        time.textContent = `${Math.floor((Date.now() - started) / 1000)}s`;
        scroll();
      }, 250);

      return {
        row,
        status,
        spinner,
        stop() { clearInterval(timer); }
      };
    }

    async function sendMessage() {
      const text = input.value.trim();
      const id = getPatientId();
      if (!text || !id || send.disabled) return;

      input.value = "";
      input.style.height = "auto";
      input.disabled = true;
      send.disabled = true;

      const empty = document.getElementById("empty-state");
      if (empty) empty.remove();

      message("user", text);
      const t = thinking();
      let assistantRow = null;
      let assistantBubble = null;
      let reply = "";
      let gotToken = false;

      try {
        const res = await fetch(`/patients/${id}/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Accept": "text/plain"
          },
          body: JSON.stringify({ message: text, stream: true })
        });

        if (!res.ok) {
          throw new Error(`${res.status}: ${await res.text()}`);
        }

        if (!res.body) {
          throw new Error("No streaming response body received.");
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder("utf-8");

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          if (!chunk) continue;

          if (!gotToken) {
            gotToken = true;
            t.status.textContent = "ToomMED is generating...";
            t.spinner.classList.add("generating");
          }

          reply += chunk;

          if (!assistantRow) {
            assistantRow = message("assistant", "");
            assistantBubble = assistantRow.querySelector(".message-bubble");
          }

          assistantBubble.textContent = reply;
          scroll();
        }

        reply += decoder.decode();

        if (!assistantRow) {
          assistantRow = message("assistant", reply || "No response received.");
          assistantBubble = assistantRow.querySelector(".message-bubble");
        } else {
          assistantBubble.textContent = reply;
        }

        if (reply.toLowerCase().includes("emergency")) {
          const banner = document.getElementById("emergency-banner");
          if (banner) banner.classList.add("visible");
          assistantRow.classList.add("emergency");
        }

        scroll();

        if (typeof loadFacts === "function") {
          loadFacts().catch(console.error);
        }
      } catch (err) {
        console.error("ToomMED chat error:", err);
        message("assistant", `Unable to get a response. ${err.message}`);
      } finally {
        t.stop();
        t.row.remove();
        input.disabled = false;
        send.disabled = false;
        input.focus();
      }
    }

    /* Replace the button handler. */
    send.onclick = sendMessage;

    /*
     * The original index.html has its own keydown listener.
     * Capture this event first and stop it so the old handler cannot
     * call the obsolete sendMessage()/scrollMessages path a second time.
     */
    input.addEventListener("keydown", e => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        e.stopImmediatePropagation();
        sendMessage();
      }
    }, true);

    input.oninput = () => {
      input.style.height = "auto";
      input.style.height = Math.min(input.scrollHeight, 130) + "px";
    };

    console.log("ToomMED live streaming chat installed.");
  }

  const style = document.createElement("style");
  style.textContent = `
    .thinking-message .message-bubble { padding:11px 14px !important; }
    .live-thinking { display:flex; align-items:center; gap:9px; min-height:25px; color:var(--muted); font-size:11px; white-space:nowrap; }
    .live-spinner { width:25px; height:25px; border-radius:8px; display:inline-flex; align-items:center; justify-content:center; background:var(--primary-soft); color:var(--primary); font-size:15px; animation:toommed-spin .9s linear infinite; }
    .live-spinner.generating { animation-duration:.45s; }
    .live-status { font-weight:600; }
    .live-time { color:var(--muted-light); min-width:25px; font-variant-numeric:tabular-nums; }
    @keyframes toommed-spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
  `;
  document.head.appendChild(style);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", install);
  } else {
    install();
  }
})();
