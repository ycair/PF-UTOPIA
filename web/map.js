class UtopiaMap {
  constructor() {
    this.canvas = document.getElementById('map-canvas');
    this.ctx = this.canvas.getContext('2d');
    this.container = document.getElementById('map-container');
    this.tooltip = document.getElementById('node-tooltip');

    this.img = new Image();
    this.config = null;
    this.playerData = null;
    this.playerNode = '烏托邦主城';
    this.unlocked = ['烏托邦主城', '競技場', '彩券中心', '投資交易所', '女僕教堂', '初始草原'];
    this.traveling = null;

    this.scale = 0.5;
    this.panX = 0;
    this.panY = 0;
    this.dragging = false;
    this.dragStartX = 0;
    this.dragStartY = 0;
    this.dragPanX = 0;
    this.dragPanY = 0;

    this.nodeHitboxes = [];
    this.init();
  }

  async init() {
    const resp = await fetch('map_config.json');
    this.config = await resp.json();
    this.img.src = this.config.map.image;
    this.scale = this.config.map.display_scale;

    this.img.onload = () => {
      this.canvas.width = this.config.map.width * this.scale;
      this.canvas.height = this.config.map.height * this.scale;
      this.centerMap();
      this.buildHitboxes();
      this.render();
      this.loadPlayerData();
    };

    this.container.addEventListener('mousedown', e => this.onDragStart(e));
    this.container.addEventListener('mousemove', e => this.onDragMove(e));
    this.container.addEventListener('mouseup', () => this.onDragEnd());
    this.container.addEventListener('mouseleave', () => this.onDragEnd());
    this.container.addEventListener('wheel', e => this.onZoom(e), {passive: false});
    window.addEventListener('resize', () => this.render());
  }

  centerMap() {
    const cw = this.container.clientWidth;
    const ch = this.container.clientHeight;
    this.panX = (cw - this.canvas.width) / 2;
    this.panY = (ch - this.canvas.height) / 2;
  }

  buildHitboxes() {
    this.nodeHitboxes = [];
    for (const [name, data] of Object.entries(this.config.nodes)) {
      this.nodeHitboxes.push({
        name,
        px: data.px * this.scale,
        py: data.py * this.scale,
        emoji: data.emoji,
        radius: 14,
      });
    }
  }

  onDragStart(e) {
    this.dragging = true;
    this.dragStartX = e.clientX;
    this.dragStartY = e.clientY;
    this.dragPanX = this.panX;
    this.dragPanY = this.panY;
  }

  onDragMove(e) {
    if (!this.dragging) return;
    this.panX = this.dragPanX + (e.clientX - this.dragStartX);
    this.panY = this.dragPanY + (e.clientY - this.dragStartY);
    this.render();

    const mx = e.clientX - this.container.getBoundingClientRect().left;
    const my = e.clientY - this.container.getBoundingClientRect().top;
    this.checkHitboxHover(mx, my);
  }

  onDragEnd() {
    this.dragging = false;
  }

  onZoom(e) {
    e.preventDefault();
    const oldScale = this.scale;
    const delta = e.deltaY > 0 ? -0.05 : 0.05;
    this.scale = Math.max(0.2, Math.min(1.5, this.scale + delta));
    if (this.scale === oldScale) return;

    const rect = this.container.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const ratio = this.scale / oldScale;
    this.panX = mx - ratio * (mx - this.panX);
    this.panY = my - ratio * (my - this.panY);

    this.canvas.width = this.config.map.width * this.scale;
    this.canvas.height = this.config.map.height * this.scale;
    this.buildHitboxes();
    this.render();
  }

  checkHitboxHover(mx, my) {
    const worldX = mx - this.panX;
    const worldY = my - this.panY;
    let hit = null;
    for (const hb of this.nodeHitboxes) {
      const dx = worldX - hb.px;
      const dy = worldY - hb.py;
      if (dx * dx + dy * dy < hb.radius * hb.radius) {
        hit = hb;
        break;
      }
    }
    if (hit) {
      this.tooltip.classList.remove('hidden');
      this.tooltip.style.left = (hit.px + this.panX + 18) + 'px';
      this.tooltip.style.top = (hit.py + this.panY - 20) + 'px';
      this.tooltip.textContent = hit.emoji + ' ' + hit.name;
      if (this.playerNode === hit.name) {
        this.tooltip.textContent += ' ⭐';
      }
      this.container.style.cursor = 'pointer';
    } else if (!this.dragging) {
      this.tooltip.classList.add('hidden');
      this.container.style.cursor = 'grab';
    }
  }

  render() {
    const ctx = this.ctx;
    const cw = this.canvas.width;
    const ch = this.canvas.height;

    this.canvas.style.left = this.panX + 'px';
    this.canvas.style.top = this.panY + 'px';

    ctx.clearRect(0, 0, cw, ch);
    ctx.drawImage(this.img, 0, 0, cw, ch);

    for (const [name, data] of Object.entries(this.config.nodes)) {
      const px = data.px * this.scale;
      const py = data.py * this.scale;
      const isUnlocked = this.unlocked.includes(name);
      const isPlayer = this.playerNode === name;

      if (!isUnlocked) {
        ctx.fillStyle = 'rgba(5,5,10,0.88)';
        ctx.beginPath();
        ctx.arc(px, py, 14, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#444';
        ctx.font = '10px "Press Start 2P"';
        ctx.textAlign = 'center';
        ctx.fillText('???', px, py + 4);
        continue;
      }

      if (isPlayer) {
        ctx.shadowColor = '#4ac8ff';
        ctx.shadowBlur = 14;
        ctx.strokeStyle = '#4ac8ff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(px, py, 16, 0, Math.PI * 2);
        ctx.stroke();
        ctx.shadowBlur = 0;

        const t = Date.now() / 800;
        const pulse = 0.6 + 0.4 * Math.sin(t);
        ctx.fillStyle = `rgba(74,200,255,${pulse * 0.3})`;
        ctx.beginPath();
        ctx.arc(px, py, 16, 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.fillStyle = '#fff';
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(data.emoji, px, py);
    }

    for (const [from, to] of this.config.edges) {
      if (!this.unlocked.includes(from) && !this.unlocked.includes(to)) continue;
      const n1 = this.config.nodes[from];
      const n2 = this.config.nodes[to];
      if (!n1 || !n2) continue;
      ctx.strokeStyle = 'rgba(200,200,200,0.3)';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 6]);
      ctx.beginPath();
      ctx.moveTo(n1.px * this.scale, n1.py * this.scale);
      ctx.lineTo(n2.px * this.scale, n2.py * this.scale);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    if (this.traveling) {
      const fromNode = this.config.nodes[this.playerNode];
      const toNode = this.config.nodes[this.traveling.target];
      if (fromNode && toNode) {
        const progress = this.traveling.progress;
        const tx = fromNode.px + (toNode.px - fromNode.px) * progress;
        const ty = fromNode.py + (toNode.py - fromNode.py) * progress;
        ctx.fillStyle = '#4ac8ff';
        ctx.shadowColor = '#4ac8ff';
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.arc(tx * this.scale, ty * this.scale, 6, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
      }
    }
  }

  async loadPlayerData() {
    try {
      const resp = await fetch('/api/me');
      if (resp.ok) {
        const data = await resp.json();
        this.playerNode = data.current_node_name || '烏托邦主城';
        this.unlocked = data.unlocked_nodes || this.unlocked;
        this.traveling = data.traveling || null;
        this.renderPlayerCard(data);
        this.render();
      }
    } catch {
      this.renderMockData();
    }
    this.render();
  }

  renderMockData() {
    document.getElementById('player-info').innerHTML = `
      <div class="stat-line">📛 <strong>冒險者</strong></div>
      <div class="stat-line">⚔️ ATK: <strong>15</strong> | 🛡️ DEF: <strong>8</strong></div>
      <div class="stat-line">❤️ HP: <strong>100/100</strong></div>
      <div class="stat-line">💪 體力: <strong>150pt</strong></div>
      <div class="stat-line">📍 <strong>烏托邦主城</strong></div>
    `;
  }

  renderPlayerCard(data) {
    const name = data.username || '冒險者';
    const atk = data.attack || 10;
    const def = data.defense || 5;
    const hp = data.current_hp || data.hp || 100;
    const maxHp = data.hp || 100;
    const stamina = data.stamina || 150;
    const node = data.current_node_name || '未知';
    const an_bi = (data.an_bi || 0).toLocaleString();
    const tuo_bi = (data.tuo_bi || 0).toLocaleString();

    document.getElementById('player-info').innerHTML = `
      <div class="stat-line">📛 <strong>${name}</strong></div>
      <div class="stat-line">⚔️ ATK: <strong>${atk}</strong> | 🛡️ DEF: <strong>${def}</strong></div>
      <div class="stat-line">❤️ HP: <strong>${hp}/${maxHp}</strong></div>
      <div class="stat-line">💪 體力: <strong>${stamina}pt</strong></div>
      <div class="stat-line">🪙 安幣: <strong>${an_bi}</strong></div>
      <div class="stat-line">💴 托幣: <strong>${tuo_bi}</strong></div>
      <div class="stat-line">📍 <strong>${node}</strong></div>
    `;
  }

  showNodeInfo(name) {
    const data = this.config.nodes[name];
    if (!data) return;
    const panel = document.getElementById('node-info');
    const nameEl = document.getElementById('node-name');
    const detail = document.getElementById('node-detail');
    panel.classList.remove('hidden');
    nameEl.textContent = data.emoji + ' ' + name;

    const isUnlocked = this.unlocked.includes(name);
    if (!isUnlocked) {
      detail.innerHTML = '<div class="node-stat">🔒 尚未探索此區域</div>';
      return;
    }

    const isSafe = ['烏托邦主城', '競技場', '彩券中心', '投資交易所', '女僕教堂', '大士爺廟'].includes(name);
    const typeLabel = isSafe ? '🛡️ 安全區' : '⚔️ 危險區';
    detail.innerHTML = `
      <div class="node-stat">${typeLabel}</div>
      ${name === '舊城邦' ? '<div class="node-stat">☢️ 輻射：防禦力 -50%</div>' : ''}
      ${name === '大士爺廟' ? '<div class="node-stat">🛡️ 鬼王庇佑</div>' : ''}
    `;
  }
}

const map = new UtopiaMap();

document.getElementById('map-container').addEventListener('click', (e) => {
  if (map.dragging) return;
  const rect = map.container.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;
  const wx = mx - map.panX;
  const wy = my - map.panY;
  for (const hb of map.nodeHitboxes) {
    const dx = wx - hb.px;
    const dy = wy - hb.py;
    if (dx * dx + dy * dy < hb.radius * hb.radius) {
      map.showNodeInfo(hb.name);
      return;
    }
  }
});

document.getElementById('map-container').addEventListener('mousemove', (e) => {
  if (map.dragging) return;
  const rect = map.container.getBoundingClientRect();
  map.checkHitboxHover(e.clientX - rect.left, e.clientY - rect.top);
});
