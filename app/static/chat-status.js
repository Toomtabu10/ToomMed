/* ToomMED chat status overlay - safe additive UI */
(() => {
  const style = document.createElement('style');
  style.textContent = `
    .toommed-thinking {
      display:flex;
      align-items:center;
      gap:9px;
      min-height:28px;
    }
    .toommed-spinner {
      width:22px;
      height:22px;
      display:inline-flex;
      align-items:center;
      justify-content:center;
      color:var(--primary,#147d73);
      font-size:20px;
      animation:toommed-spin .9s linear infinite;
      transform-origin:center;
    }
    @keyframes toommed-spin { to { transform:rotate(360deg); } }
    .toommed-status-text { font-size:12px; color:var(--muted,#728080); }
    .toommed-status-time { margin-left:4px; font-variant-numeric:tabular-nums; }
  `;
  document.head.appendChild(style);

  window.ToomMedThinking = {
    start(row) {
      const bubble = row?.querySelector('.message-bubble');
      if (!bubble) return () => {};
      const started = performance.now();
      let generating = false;
      let timer;
      const update = () => {
        const seconds = Math.floor((performance.now() - started) / 1000);
        const label = generating ? 'ToomMED is generating…' : 'ToomMED is thinking…';
        bubble.innerHTML = `<div class="toommed-thinking"><span class="toommed-spinner">✚</span><span class="toommed-status-text">${label}<span class="toommed-status-time">${seconds}s</span></span></div>`;
      };
      update();
      timer = setInterval(update, 1000);
      return {
        firstToken() { generating = true; update(); },
        stop() { clearInterval(timer); }
      };
    }
  };
})();
