/**
 * PF UTOPIA - 安逸烏托邦 - Interactive Map & Dashboard
 * Enhanced with visual effects, animations, and polished UI
 */

const DISCORD_CLIENT_ID = '921779959717048340';
const DISCORD_REDIRECT = 'https://utopia.ycair.space/callback.html';
const API_BASE = '/api';

let authToken = localStorage.getItem('utopia_token') || null;

class UtopiaApp {
  constructor() {
    // Canvas & DOM elements
    this.canvas = document.getElementById('map-canvas');
    this.ctx = this.canvas?.getContext('2d');
    this.container = document.getElementById('map-container');
    this.tooltip = document.getElementById('node-tooltip');
    this.minimap = document.getElementById('minimap-canvas');
    this.minimapCtx = this.minimap?.getContext('2d');
    this.minimapViewport = document.getElementById('minimap-viewport');
    
    // Map state
    this.img = new Image();
    this.config = null;
    this.playerNode = null;
    this.unlocked = [];
    this.traveling = null;
    
    // View state
    this.scale = 0.5;
    this.panX = 0;
    this.panY = 0;
    this.dragging = false;
    this.nodeHitboxes = [];
    
    // Animation state
    this.animationFrame = 0;
    this.lastTime = 0;
    this.hoveredNode = null;
    
    // Edge danger levels (can be loaded from API later)
    this.edgeDanger = {};
    
    this.init();
  }

  async init() {
    // Tab navigation
    document.querySelectorAll('.nav-tab').forEach(tab => {
      tab.addEventListener('click', () => this.switchPage(tab.dataset.page));
    });
    
    // Login button
    document.getElementById('login-btn').addEventListener('click', () => this.login());
    
    // Zoom controls
    document.getElementById('zoom-in')?.addEventListener('click', () => this.zoomTo(this.scale + 0.1));
    document.getElementById('zoom-out')?.addEventListener('click', () => this.zoomTo(this.scale - 0.1));
    
    // Check auth
    if (authToken) this.onLoggedIn();
    
    // Load map config
    const response = await fetch('map_config.json');
    this.config = await response.json();
    
    // Initialize edge danger levels (default to safe)
    for (const [from, to] of this.config.edges) {
      const key = `${from}-${to}`;
      this.edgeDanger[key] = this.calculateEdgeDanger(from, to);
    }
    
    // Load map image
    this.img.crossOrigin = 'anonymous';
    this.img.src = this.config.map.image;
    this.scale = this.config.map.display_scale;
    
    this.img.onload = () => {
      this.canvas.width = this.config.map.width * this.scale;
      this.canvas.height = this.config.map.height * this.scale;
      this.centerMap();
      this.buildHitboxes();
      this.initMinimap();
      this.startRenderLoop();
      if (authToken) this.loadPlayerData();
    };
    
    // Map interaction events
    if (this.container) {
      this.container.addEventListener('mousedown', e => this.onDragStart(e));
      this.container.addEventListener('mousemove', e => this.onDragMove(e));
      this.container.addEventListener('mouseup', () => this.onDragEnd());
      this.container.addEventListener('mouseleave', () => this.onDragEnd());
      this.container.addEventListener('wheel', e => this.onZoom(e), { passive: false });
      
      // Touch events for mobile
      this.container.addEventListener('touchstart', e => this.onTouchStart(e), { passive: false });
      this.container.addEventListener('touchmove', e => this.onTouchMove(e), { passive: false });
      this.container.addEventListener('touchend', () => this.onDragEnd());
    }
    
    window.addEventListener('resize', () => {
      this.updateMinimap();
    });
  }

  // Calculate danger level for edge (0 = safe, 1 = dangerous)
  calculateEdgeDanger(from, to) {
    const dangerousNodes = ['世界魔皇巢穴', '舊城邦'];
    if (dangerousNodes.includes(from) || dangerousNodes.includes(to)) {
      return 0.8;
    }
    const moderateNodes = ['翡翠森林', '搗蛋精靈之森'];
    if (moderateNodes.includes(from) || moderateNodes.includes(to)) {
      return 0.4;
    }
    return 0.1;
  }

  switchPage(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.getElementById('page-' + page)?.classList.add('active');
    document.querySelector(`[data-page="${page}"]`)?.classList.add('active');
    
    if (page === 'map') {
      this.centerMap();
    }
    if (page === 'market') this.loadMarket();
    if (page === 'ranking') this.loadRankings();
    if (page === 'profile') this.loadProfileFull();
  }

  login() {
    window.location.href = `https://discord.com/api/oauth2/authorize?client_id=${DISCORD_CLIENT_ID}&redirect_uri=${encodeURIComponent(DISCORD_REDIRECT)}&response_type=code&scope=identify`;
  }

  onLoggedIn() {
    document.getElementById('login-btn').classList.add('hidden');
    document.getElementById('user-greeting').classList.remove('hidden');
    document.getElementById('user-name').textContent = '已登入';
  }

  centerMap() {
    if (!this.container || !this.canvas) return;
    this.panX = (this.container.clientWidth - this.canvas.width) / 2;
    this.panY = (this.container.clientHeight - this.canvas.height) / 2;
    this.updateMinimap();
  }

  buildHitboxes() {
    this.nodeHitboxes = [];
    for (const [name, data] of Object.entries(this.config.nodes)) {
      this.nodeHitboxes.push({
        name,
        px: data.px * this.scale,
        py: data.py * this.scale,
        emoji: data.emoji,
        radius: 22 * this.scale
      });
    }
  }

  initMinimap() {
    if (!this.minimap || !this.minimapCtx) return;
    
    const ratio = this.config.map.width / this.config.map.height;
    this.minimap.width = 160;
    this.minimap.height = 160 / ratio;
    
    // Draw map thumbnail
    this.minimapCtx.drawImage(this.img, 0, 0, this.minimap.width, this.minimap.height);
    this.minimapCtx.fillStyle = 'rgba(0,0,0,0.3)';
    this.minimapCtx.fillRect(0, 0, this.minimap.width, this.minimap.height);
    
    this.updateMinimap();
  }

  updateMinimap() {
    if (!this.minimapViewport || !this.container || !this.minimap) return;
    
    const mapW = this.config.map.width * this.scale;
    const mapH = this.config.map.height * this.scale;
    const viewW = this.container.clientWidth;
    const viewH = this.container.clientHeight;
    
    const scaleX = this.minimap.width / mapW;
    const scaleY = this.minimap.height / mapH;
    
    const vpX = Math.max(0, -this.panX) * scaleX;
    const vpY = Math.max(0, -this.panY) * scaleY;
    const vpW = Math.min(viewW, mapW) * scaleX;
    const vpH = Math.min(viewH, mapH) * scaleY;
    
    this.minimapViewport.style.left = vpX + 'px';
    this.minimapViewport.style.top = vpY + 'px';
    this.minimapViewport.style.width = vpW + 'px';
    this.minimapViewport.style.height = vpH + 'px';
    
    // Update zoom level display
    const zoomLevel = document.getElementById('zoom-level');
    if (zoomLevel) {
      zoomLevel.textContent = Math.round(this.scale * 100) + '%';
    }
  }

  // Touch events
  onTouchStart(e) {
    if (e.touches.length === 1) {
      e.preventDefault();
      const touch = e.touches[0];
      this.dragging = true;
      this.dragStartX = touch.clientX;
      this.dragStartY = touch.clientY;
      this.dragPanX = this.panX;
      this.dragPanY = this.panY;
    }
  }

  onTouchMove(e) {
    if (!this.dragging || e.touches.length !== 1) return;
    e.preventDefault();
    const touch = e.touches[0];
    this.panX = this.dragPanX + (touch.clientX - this.dragStartX);
    this.panY = this.dragPanY + (touch.clientY - this.dragStartY);
    this.updateMinimap();
  }

  onDragStart(e) {
    this.dragging = true;
    this.dragStartX = e.clientX;
    this.dragStartY = e.clientY;
    this.dragPanX = this.panX;
    this.dragPanY = this.panY;
  }

  onDragMove(e) {
    const rect = this.container.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    
    this.checkHitboxHover(mx, my);
    
    if (!this.dragging) return;
    this.panX = this.dragPanX + (e.clientX - this.dragStartX);
    this.panY = this.dragPanY + (e.clientY - this.dragStartY);
    this.updateMinimap();
  }

  onDragEnd() {
    this.dragging = false;
  }

  onZoom(e) {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.05 : 0.05;
    const rect = this.container.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    this.zoomAt(delta, mx, my);
  }

  zoomTo(newScale) {
    const rect = this.container.getBoundingClientRect();
    const mx = rect.width / 2;
    const my = rect.height / 2;
    const delta = newScale - this.scale;
    this.zoomAt(delta, mx, my);
  }

  zoomAt(delta, mx, my) {
    const oldScale = this.scale;
    this.scale = Math.max(0.25, Math.min(1.2, this.scale + delta));
    if (this.scale === oldScale) return;
    
    const ratio = this.scale / oldScale;
    this.panX = mx - ratio * (mx - this.panX);
    this.panY = my - ratio * (my - this.panY);
    
    this.canvas.width = this.config.map.width * this.scale;
    this.canvas.height = this.config.map.height * this.scale;
    this.buildHitboxes();
    this.updateMinimap();
  }

  checkHitboxHover(mx, my) {
    const wx = mx - this.panX;
    const wy = my - this.panY;
    
    let hit = null;
    for (const hb of this.nodeHitboxes) {
      const dx = wx - hb.px;
      const dy = wy - hb.py;
      if (dx * dx + dy * dy < hb.radius * hb.radius * 1.5) {
        hit = hb;
        break;
      }
    }
    
    this.hoveredNode = hit;
    
    if (hit) {
      this.showTooltip(hit);
      this.container.style.cursor = 'pointer';
    } else if (!this.dragging) {
      this.tooltip.classList.add('hidden');
      this.container.style.cursor = 'grab';
    }
  }

  showTooltip(node) {
    const tooltip = this.tooltip;
    const isUnlocked = this.unlocked.includes(node.name) || this.unlocked.length === 0;
    const isCurrentLocation = this.playerNode === node.name;
    
    tooltip.classList.remove('hidden');
    
    // Position tooltip
    let left = node.px + this.panX + 30;
    let top = node.py + this.panY - 20;
    
    // Keep tooltip in bounds
    const tooltipRect = tooltip.getBoundingClientRect();
    const containerRect = this.container.getBoundingClientRect();
    
    if (left + 150 > containerRect.width) {
      left = node.px + this.panX - 170;
    }
    if (top < 10) {
      top = 10;
    }
    
    tooltip.style.left = left + 'px';
    tooltip.style.top = top + 'px';
    
    // Update tooltip content
    const iconEl = tooltip.querySelector('.tooltip-icon');
    const nameEl = tooltip.querySelector('.tooltip-name');
    const statusEl = tooltip.querySelector('.tooltip-status');
    
    if (iconEl) iconEl.textContent = node.emoji;
    if (nameEl) nameEl.textContent = node.name;
    
    if (statusEl) {
      if (!isUnlocked) {
        statusEl.textContent = '[ 尚未探索 ]';
        statusEl.className = 'tooltip-status locked';
      } else if (isCurrentLocation) {
        statusEl.textContent = '[ 目前所在地 ]';
        statusEl.className = 'tooltip-status current';
      } else {
        statusEl.textContent = '[ 已探索 ]';
        statusEl.className = 'tooltip-status';
      }
    }
  }

  startRenderLoop() {
    const render = (timestamp) => {
      this.animationFrame++;
      this.lastTime = timestamp;
      this.render();
      requestAnimationFrame(render);
    };
    requestAnimationFrame(render);
  }

  render() {
    if (!this.ctx || !this.img.complete) return;
    
    const ctx = this.ctx;
    const cw = this.canvas.width;
    const ch = this.canvas.height;
    
    // Update canvas position
    this.canvas.style.left = this.panX + 'px';
    this.canvas.style.top = this.panY + 'px';
    
    // Clear canvas
    ctx.clearRect(0, 0, cw, ch);
    
    // Draw map image
    ctx.drawImage(this.img, 0, 0, cw, ch);
    
    // Draw edges (roads) between nodes
    this.renderEdges(ctx);
    
    // Draw nodes
    this.renderNodes(ctx);
  }

  renderEdges(ctx) {
    const allUnlocked = this.unlocked.length === 0;
    
    for (const [from, to] of this.config.edges) {
      const fromUnlocked = allUnlocked || this.unlocked.includes(from);
      const toUnlocked = allUnlocked || this.unlocked.includes(to);
      
      // Only show edges for discovered paths
      if (!fromUnlocked && !toUnlocked) continue;
      
      const n1 = this.config.nodes[from];
      const n2 = this.config.nodes[to];
      if (!n1 || !n2) continue;
      
      const x1 = n1.px * this.scale;
      const y1 = n1.py * this.scale;
      const x2 = n2.px * this.scale;
      const y2 = n2.py * this.scale;
      
      // Get danger level for color
      const key = `${from}-${to}`;
      const danger = this.edgeDanger[key] || 0.1;
      
      // Color based on danger (green = safe, red = dangerous)
      const r = Math.floor(80 + danger * 175);
      const g = Math.floor(200 - danger * 150);
      const b = Math.floor(80 - danger * 50);
      
      // Draw road line
      ctx.save();
      ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, 0.4)`;
      ctx.lineWidth = 3 * this.scale;
      ctx.setLineDash([8 * this.scale, 6 * this.scale]);
      ctx.lineDashOffset = -this.animationFrame * 0.3;
      
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
      
      ctx.restore();
    }
  }

  renderNodes(ctx) {
    const allUnlocked = this.unlocked.length === 0;
    const time = this.animationFrame * 0.05;
    
    for (const [name, data] of Object.entries(this.config.nodes)) {
      const px = data.px * this.scale;
      const py = data.py * this.scale;
      const isUnlocked = allUnlocked || this.unlocked.includes(name);
      const isPlayer = this.playerNode === name;
      const isHovered = this.hoveredNode?.name === name;
      
      ctx.save();
      
      if (!isUnlocked) {
        // Fog of war - dark mist
        const gradient = ctx.createRadialGradient(px, py, 0, px, py, 35 * this.scale);
        gradient.addColorStop(0, 'rgba(5, 5, 10, 0.95)');
        gradient.addColorStop(0.7, 'rgba(5, 5, 10, 0.8)');
        gradient.addColorStop(1, 'rgba(5, 5, 10, 0)');
        
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(px, py, 40 * this.scale, 0, Math.PI * 2);
        ctx.fill();
        
        // Mystery marker
        ctx.fillStyle = '#444';
        ctx.font = `bold ${12 * this.scale}px "Press Start 2P"`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('???', px, py);
        
        ctx.restore();
        continue;
      }
      
      // Player position - glowing beacon effect
      if (isPlayer) {
        // Outer pulsing ring
        const pulseSize = 1 + Math.sin(time * 2) * 0.15;
        const pulseAlpha = 0.4 + Math.sin(time * 2) * 0.2;
        
        ctx.strokeStyle = `rgba(74, 200, 255, ${pulseAlpha})`;
        ctx.lineWidth = 3 * this.scale;
        ctx.beginPath();
        ctx.arc(px, py, 28 * this.scale * pulseSize, 0, Math.PI * 2);
        ctx.stroke();
        
        // Inner glow
        const innerGlow = ctx.createRadialGradient(px, py, 0, px, py, 22 * this.scale);
        innerGlow.addColorStop(0, 'rgba(74, 200, 255, 0.3)');
        innerGlow.addColorStop(1, 'rgba(74, 200, 255, 0)');
        
        ctx.fillStyle = innerGlow;
        ctx.beginPath();
        ctx.arc(px, py, 22 * this.scale, 0, Math.PI * 2);
        ctx.fill();
      }
      
      // Hover effect
      if (isHovered && !isPlayer) {
        const hoverGlow = ctx.createRadialGradient(px, py, 0, px, py, 25 * this.scale);
        hoverGlow.addColorStop(0, 'rgba(201, 168, 76, 0.25)');
        hoverGlow.addColorStop(1, 'rgba(201, 168, 76, 0)');
        
        ctx.fillStyle = hoverGlow;
        ctx.beginPath();
        ctx.arc(px, py, 25 * this.scale, 0, Math.PI * 2);
        ctx.fill();
        
        ctx.strokeStyle = 'rgba(201, 168, 76, 0.6)';
        ctx.lineWidth = 2 * this.scale;
        ctx.beginPath();
        ctx.arc(px, py, 20 * this.scale, 0, Math.PI * 2);
        ctx.stroke();
      }
      
      // Node marker - glowing pin effect
      const markerGlow = ctx.createRadialGradient(px, py - 5 * this.scale, 0, px, py, 18 * this.scale);
      markerGlow.addColorStop(0, 'rgba(255, 255, 255, 0.15)');
      markerGlow.addColorStop(1, 'rgba(255, 255, 255, 0)');
      
      ctx.fillStyle = markerGlow;
      ctx.beginPath();
      ctx.arc(px, py, 18 * this.scale, 0, Math.PI * 2);
      ctx.fill();
      
      // Emoji icon
      ctx.font = `${20 * this.scale}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(data.emoji, px, py);
      
      // Node name label
      const labelY = py + 24 * this.scale;
      const labelPadding = 6 * this.scale;
      const fontSize = 7 * this.scale;
      
      ctx.font = `${fontSize}px "Press Start 2P"`;
      const textWidth = ctx.measureText(name).width;
      
      // Label background
      ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
      ctx.beginPath();
      ctx.roundRect(
        px - textWidth / 2 - labelPadding,
        labelY - fontSize / 2 - labelPadding / 2,
        textWidth + labelPadding * 2,
        fontSize + labelPadding,
        3 * this.scale
      );
      ctx.fill();
      
      // Label border
      ctx.strokeStyle = isPlayer ? 'rgba(74, 200, 255, 0.5)' : 'rgba(201, 168, 76, 0.3)';
      ctx.lineWidth = 1;
      ctx.stroke();
      
      // Label text
      ctx.fillStyle = isPlayer ? '#4ac8ff' : '#ddd';
      ctx.fillText(name, px, labelY);
      
      ctx.restore();
    }
  }

  // API Methods
  async apiGet(path) {
    const headers = {};
    if (authToken) headers['Authorization'] = 'Bearer ' + authToken;
    
    try {
      const response = await fetch(API_BASE + path, { headers });
      if (response.status === 401) {
        authToken = null;
        localStorage.removeItem('utopia_token');
      }
      return response.ok ? response.json() : null;
    } catch {
      return null;
    }
  }

  async loadPlayerData() {
    const data = await this.apiGet('/me');
    if (!data) return;
    
    this.playerNode = data.current_node_name || '烏托邦主城';
    this.unlocked = data.unlocked_nodes || Object.keys(this.config.nodes);
    
    document.getElementById('user-name').textContent = data.username || '冒險者';
  }

  async loadProfileFull() {
    const el = document.getElementById('profile-full');
    
    if (!authToken) {
      el.innerHTML = '<div class="loading">請先 Discord 登入</div>';
      return;
    }
    
    const data = await this.apiGet('/me');
    if (!data) {
      el.innerHTML = '<div class="loading">無法載入資料</div>';
      return;
    }
    
    const hpPercent = Math.round((data.current_hp / data.hp) * 100);
    const staminaPercent = Math.min(100, (data.stamina / 100) * 100);
    
    el.innerHTML = `
      <div class="profile-header">
        <div class="profile-avatar">&#x1F9D9;</div>
        <div class="profile-info">
          <div class="profile-name">${data.username || '冒險者'}</div>
          <div class="profile-title">烏托邦冒險者</div>
        </div>
      </div>
      
      <div class="stat-bar-container">
        <div class="stat-bar-label">
          <span class="stat-bar-name"><span>&#x2764;</span> 生命值</span>
          <span class="stat-bar-value">${data.current_hp} / ${data.hp}</span>
        </div>
        <div class="stat-bar">
          <div class="stat-bar-fill hp" style="width: ${hpPercent}%"></div>
        </div>
      </div>
      
      <div class="stat-bar-container">
        <div class="stat-bar-label">
          <span class="stat-bar-name"><span>&#x1F4AA;</span> 體力</span>
          <span class="stat-bar-value">${data.stamina} pt</span>
        </div>
        <div class="stat-bar">
          <div class="stat-bar-fill stamina" style="width: ${staminaPercent}%"></div>
        </div>
      </div>
      
      <div class="stat-group">
        <div class="stat-group-title"><span>&#x2694;</span> 戰鬥數值</div>
        <div class="stat-grid">
          <div class="stat-item">
            <span class="stat-icon">&#x2694;</span>
            <div class="stat-content">
              <div class="stat-label">攻擊力</div>
              <div class="stat-value">${data.attack || 0}</div>
            </div>
          </div>
          <div class="stat-item">
            <span class="stat-icon">&#x1F6E1;</span>
            <div class="stat-content">
              <div class="stat-label">防禦力</div>
              <div class="stat-value">${data.defense || 0}</div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="stat-group">
        <div class="stat-group-title"><span>&#x1FA99;</span> 貨幣資產</div>
        <div class="currency-grid">
          <div class="currency-item">
            <span class="currency-icon">&#x1FA99;</span>
            <div class="currency-info">
              <div class="currency-name">安幣</div>
              <div class="currency-value">${(data.an_bi || 0).toLocaleString()}</div>
            </div>
          </div>
          <div class="currency-item">
            <span class="currency-icon">&#x1F4B4;</span>
            <div class="currency-info">
              <div class="currency-name">托幣</div>
              <div class="currency-value">${(data.tuo_bi || 0).toLocaleString()}</div>
            </div>
          </div>
          <div class="currency-item">
            <span class="currency-icon">&#x1F4B5;</span>
            <div class="currency-info">
              <div class="currency-name">逸幣</div>
              <div class="currency-value">${(data.yi_bi || 0).toLocaleString()}</div>
            </div>
          </div>
          <div class="currency-item">
            <span class="currency-icon">&#x1F4B6;</span>
            <div class="currency-info">
              <div class="currency-name">烏幣</div>
              <div class="currency-value">${(data.wu_bi || 0).toLocaleString()}</div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="location-display">
        <span class="location-icon">&#x1F4CD;</span>
        <div class="location-info">
          <div class="location-label">目前位置</div>
          <div class="location-name">${data.current_node_name || '未知'}</div>
        </div>
      </div>
    `;
  }

  async loadMarket() {
    // Load stocks
    const stocks = await this.apiGet('/stocks');
    const marketEl = document.getElementById('market-data');
    
    if (stocks && stocks.length > 0) {
      marketEl.innerHTML = stocks.map(stock => {
        const isUp = stock.change >= 0;
        return `
          <div class="market-row">
            <div class="market-item">
              <span class="market-icon">${stock.emoji || '&#x1F422;'}</span>
              <span class="market-name">${stock.name}</span>
            </div>
            <div class="market-price">
              <span class="market-value">${stock.current_price.toLocaleString()}</span>
              <span class="market-change ${isUp ? 'up' : 'down'}">
                <span class="market-trend">${isUp ? '&#x25B2;' : '&#x25BC;'}</span>
                ${isUp ? '+' : ''}${stock.change}%
              </span>
            </div>
          </div>
        `;
      }).join('');
    } else {
      marketEl.innerHTML = '<div class="loading">無法載入股市資料</div>';
    }
    
    // Load shop prices
    const prices = await this.apiGet('/shop/prices');
    const shopEl = document.getElementById('shop-data');
    
    if (prices && prices.length > 0) {
      shopEl.innerHTML = prices.map(item => `
        <div class="market-row">
          <div class="market-item">
            <span class="market-icon">${item.emoji || '&#x1F4E6;'}</span>
            <span class="market-name">${item.name}</span>
          </div>
          <div class="market-price">
            <span class="market-value">${item.price.toLocaleString()} 托幣</span>
          </div>
        </div>
      `).join('');
    } else {
      shopEl.innerHTML = '<div class="loading">無法載入物價資料</div>';
    }
  }

  async loadRankings() {
    // Power rankings
    const power = await this.apiGet('/rankings/power');
    const powerEl = document.getElementById('rank-power');
    
    if (power && power.length > 0) {
      powerEl.innerHTML = power.map((player, index) => {
        const medals = ['&#x1F947;', '&#x1F948;', '&#x1F949;'];
        const topClass = index < 3 ? `top-${index + 1}` : '';
        
        return `
          <div class="rank-row ${topClass}">
            <span class="rank-pos">
              ${index < 3 
                ? `<span class="rank-medal">${medals[index]}</span>` 
                : `<span class="rank-number">${index + 1}.</span>`
              }
            </span>
            <span class="rank-name">${player.username}</span>
            <span class="rank-val">${player.score.toLocaleString()} 分</span>
          </div>
        `;
      }).join('');
    } else {
      powerEl.innerHTML = '<div class="loading">無法載入排行榜</div>';
    }
    
    // Wealth rankings
    const wealth = await this.apiGet('/rankings/wealth');
    const wealthEl = document.getElementById('rank-wealth');
    
    if (wealth && wealth.length > 0) {
      wealthEl.innerHTML = wealth.map((player, index) => {
        const medals = ['&#x1F947;', '&#x1F948;', '&#x1F949;'];
        const topClass = index < 3 ? `top-${index + 1}` : '';
        
        return `
          <div class="rank-row ${topClass}">
            <span class="rank-pos">
              ${index < 3 
                ? `<span class="rank-medal">${medals[index]}</span>` 
                : `<span class="rank-number">${index + 1}.</span>`
              }
            </span>
            <span class="rank-name">${player.username}</span>
            <span class="rank-val">${player.an_bi.toLocaleString()} 安幣</span>
          </div>
        `;
      }).join('');
    } else {
      wealthEl.innerHTML = '<div class="loading">無法載入排行榜</div>';
    }
  }
}

// Initialize app
new UtopiaApp();
