/* ContractFlow CRM — Main JavaScript */

/* ── Signature pad ────────────────────────────────────────── */
function initSignaturePad(canvasId, clearBtnId, hiddenInputId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let drawing = false;
  let lastX = 0, lastY = 0;

  function getPos(e) {
    const rect = canvas.getBoundingClientRect();
    if (e.touches) {
      return {
        x: e.touches[0].clientX - rect.left,
        y: e.touches[0].clientY - rect.top,
      };
    }
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }

  function startDraw(e) {
    e.preventDefault();
    drawing = true;
    const pos = getPos(e);
    lastX = pos.x; lastY = pos.y;
  }

  function draw(e) {
    if (!drawing) return;
    e.preventDefault();
    const pos = getPos(e);
    ctx.beginPath();
    ctx.moveTo(lastX, lastY);
    ctx.lineTo(pos.x, pos.y);
    ctx.strokeStyle = '#e2e8f6';
    ctx.lineWidth   = 2.5;
    ctx.lineCap     = 'round';
    ctx.lineJoin    = 'round';
    ctx.stroke();
    lastX = pos.x; lastY = pos.y;
  }

  function stopDraw() {
    drawing = false;
    if (hiddenInputId) {
      document.getElementById(hiddenInputId).value = canvas.toDataURL();
    }
  }

  canvas.addEventListener('mousedown',  startDraw);
  canvas.addEventListener('mousemove',  draw);
  canvas.addEventListener('mouseup',    stopDraw);
  canvas.addEventListener('mouseleave', stopDraw);
  canvas.addEventListener('touchstart', startDraw, { passive: false });
  canvas.addEventListener('touchmove',  draw,       { passive: false });
  canvas.addEventListener('touchend',   stopDraw);

  const clearBtn = document.getElementById(clearBtnId);
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (hiddenInputId) document.getElementById(hiddenInputId).value = '';
    });
  }
}

/* ── Mark-read AJAX helper ────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function () {

  /* Notification read via AJAX */
  document.querySelectorAll('.mark-read-btn').forEach(btn => {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      fetch(this.dataset.url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      })
        .then(r => r.json())
        .then(data => {
          if (data.status !== 'ok') return;
          const item = this.closest('.notification-item');
          if (item) item.classList.remove('unread');
          const badge = document.querySelector('.notification-count');
          if (badge) {
            let c = parseInt(badge.textContent) - 1;
            badge.textContent = c <= 0 ? '' : c;
            if (c <= 0) badge.style.display = 'none';
          }
        });
    });
  });

  /* Confirm before destructive actions */
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', function (e) {
      if (!confirm(this.dataset.confirm)) e.preventDefault();
    });
  });

  /* Auto-submit filter selects */
  document.querySelectorAll('.auto-filter').forEach(el => {
    el.addEventListener('change', function () {
      this.closest('form').submit();
    });
  });

});
