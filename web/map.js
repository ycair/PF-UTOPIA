const DISCORD_CLIENT_ID='921779959717048340';
const DISCORD_REDIRECT='https://utopia.ycair.space/callback.html';
const API_BASE='/api';
let authToken=localStorage.getItem('utopia_token')||null;

class UtopiaApp{
  constructor(){
    this.canvas=document.getElementById('map-canvas');this.ctx=this.canvas?.getContext('2d');
    this.container=document.getElementById('map-container');this.tooltip=document.getElementById('node-tooltip');
    this.img=new Image();this.config=null;this.playerNode=null;this.unlocked=[];this.traveling=null;
    this.scale=0.5;this.panX=0;this.panY=0;this.dragging=false;this.nodeHitboxes=[];
    this.init();
  }
  async init(){
    document.querySelectorAll('.nav-tab').forEach(t=>t.addEventListener('click',()=>this.switchPage(t.dataset.page)));
    document.getElementById('login-btn').addEventListener('click',()=>this.login());
    if(authToken)this.onLoggedIn();
    const r=await fetch('map_config.json');this.config=await r.json();
    this.img.src=this.config.map.image;this.scale=this.config.map.display_scale;
    this.img.onload=()=>{
      this.canvas.width=this.config.map.width*this.scale;this.canvas.height=this.config.map.height*this.scale;
      this.centerMap();this.buildHitboxes();this.render();if(authToken)this.loadPlayerData();
    };
    if(this.container){
      this.container.addEventListener('mousedown',e=>this.onDragStart(e));
      this.container.addEventListener('mousemove',e=>this.onDragMove(e));
      this.container.addEventListener('mouseup',()=>this.onDragEnd());
      this.container.addEventListener('mouseleave',()=>this.onDragEnd());
      this.container.addEventListener('wheel',e=>this.onZoom(e),{passive:false});
    }
    window.addEventListener('resize',()=>this.render());
  }
  switchPage(page){
    document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(t=>t.classList.remove('active'));
    document.getElementById('page-'+page)?.classList.add('active');
    document.querySelector(`[data-page="${page}"]`)?.classList.add('active');
    if(page==='map'){this.centerMap();this.render()}
    if(page==='market')this.loadMarket();
    if(page==='ranking')this.loadRankings();
    if(page==='profile')this.loadProfileFull();
  }
  login(){window.location.href=`https://discord.com/api/oauth2/authorize?client_id=${DISCORD_CLIENT_ID}&redirect_uri=${encodeURIComponent(DISCORD_REDIRECT)}&response_type=code&scope=identify`}
  onLoggedIn(){document.getElementById('login-btn').classList.add('hidden');document.getElementById('user-greeting').classList.remove('hidden');document.getElementById('user-greeting').textContent='👤 已登入'}
  centerMap(){if(!this.container||!this.canvas)return;this.panX=(this.container.clientWidth-this.canvas.width)/2;this.panY=(this.container.clientHeight-this.canvas.height)/2}
  buildHitboxes(){this.nodeHitboxes=[];for(const[n,d]of Object.entries(this.config.nodes))this.nodeHitboxes.push({name:n,px:d.px*this.scale,py:d.py*this.scale,emoji:d.emoji,radius:18})}
  onDragStart(e){this.dragging=true;this.dragStartX=e.clientX;this.dragStartY=e.clientY;this.dragPanX=this.panX;this.dragPanY=this.panY}
  onDragMove(e){if(!this.dragging)return;this.panX=this.dragPanX+(e.clientX-this.dragStartX);this.panY=this.dragPanY+(e.clientY-this.dragStartY);this.render();if(this.container){const r=this.container.getBoundingClientRect();this.checkHitboxHover(e.clientX-r.left,e.clientY-r.top)}}
  onDragEnd(){this.dragging=false}
  onZoom(e){e.preventDefault();const o=this.scale;this.scale=Math.max(0.2,Math.min(1.5,this.scale+(e.deltaY>0?-0.05:0.05)));if(this.scale===o)return;const r=this.container.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top,ratio=this.scale/o;this.panX=mx-ratio*(mx-this.panX);this.panY=my-ratio*(my-this.panY);this.canvas.width=this.config.map.width*this.scale;this.canvas.height=this.config.map.height*this.scale;this.buildHitboxes();this.render()}
  checkHitboxHover(mx,my){const wx=mx-this.panX,wy=my-this.panY;let hit=null;for(const hb of this.nodeHitboxes){if((wx-hb.px)**2+(wy-hb.py)**2<hb.radius*hb.radius){hit=hb;break}}if(hit){this.tooltip.classList.remove('hidden');this.tooltip.style.left=(hit.px+this.panX+22)+'px';this.tooltip.style.top=(hit.py+this.panY-24)+'px';this.tooltip.textContent=hit.emoji+' '+hit.name+(this.playerNode===hit.name?' ⭐':'');this.container.style.cursor='pointer'}else if(!this.dragging){this.tooltip.classList.add('hidden');this.container.style.cursor='grab'}}
  render(){if(!this.ctx||!this.img.complete)return;const ctx=this.ctx,cw=this.canvas.width,ch=this.canvas.height;this.canvas.style.left=this.panX+'px';this.canvas.style.top=this.panY+'px';ctx.clearRect(0,0,cw,ch);ctx.drawImage(this.img,0,0,cw,ch);
    for(const[f,t]of this.config.edges){if(!this.unlocked.includes(f)&&!this.unlocked.includes(t))continue;const n1=this.config.nodes[f],n2=this.config.nodes[t];if(!n1||!n2)continue;ctx.strokeStyle='rgba(200,200,200,0.25)';ctx.lineWidth=1;ctx.setLineDash([4,6]);ctx.beginPath();ctx.moveTo(n1.px*this.scale,n1.py*this.scale);ctx.lineTo(n2.px*this.scale,n2.py*this.scale);ctx.stroke();ctx.setLineDash([])}
    for(const[n,d]of Object.entries(this.config.nodes)){const px=d.px*this.scale,py=d.py*this.scale,u=this.unlocked.includes(n),p=this.playerNode===n;if(!u){ctx.fillStyle='rgba(5,5,10,0.88)';ctx.beginPath();ctx.arc(px,py,15,0,Math.PI*2);ctx.fill();ctx.fillStyle='#555';ctx.font='9px "Press Start 2P"';ctx.textAlign='center';ctx.fillText('???',px,py+3);continue}
    ctx.shadowBlur=0;if(p){ctx.shadowColor='#4ac8ff';ctx.shadowBlur=20;ctx.strokeStyle='#4ac8ff';ctx.lineWidth=3;ctx.beginPath();ctx.arc(px,py,18,0,Math.PI*2);ctx.stroke();ctx.shadowBlur=0}
    ctx.fillStyle='#fff';ctx.font='18px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(d.emoji,px,py);ctx.fillStyle='rgba(0,0,0,0.7)';ctx.fillRect(px-40,py+14,80,12);ctx.fillStyle='#ddd';ctx.font='7px "Press Start 2P"';ctx.fillText(n,px,py+22)}
    requestAnimationFrame(()=>this.render())}
  async apiGet(path){const h={};if(authToken)h['Authorization']='Bearer '+authToken;try{const r=await fetch(API_BASE+path,{headers:h});if(r.status===401){authToken=null;localStorage.removeItem('utopia_token')}return r.ok?r.json():null}catch{return null}}
  async loadPlayerData(){const d=await this.apiGet('/me');if(!d)return;this.playerNode=d.current_node_name||'烏托邦主城';this.unlocked=d.unlocked_nodes||Object.keys(this.config.nodes);document.getElementById('user-greeting').textContent='👤 '+(d.username||'冒險者')}
  async loadProfileFull(){const el=document.getElementById('profile-full');if(!authToken){el.innerHTML='<p>請先 Discord 登入</p>';return}const d=await this.apiGet('/me');if(!d){el.innerHTML='<p>無法載入</p>';return}el.innerHTML=[`📛 <strong>${d.username}</strong>`,`⚔️ ATK: <strong>${d.attack}</strong> | 🛡️ DEF: <strong>${d.defense}</strong>`,`❤️ HP: <strong>${d.current_hp}/${d.hp}</strong>`,`💪 體力: <strong>${d.stamina}pt</strong>`,`🪙 安幣: <strong>${(d.an_bi||0).toLocaleString()}</strong>`,`💴 托幣: <strong>${(d.tuo_bi||0).toLocaleString()}</strong>`,`💵 逸幣: <strong>${(d.yi_bi||0).toLocaleString()}</strong>`,`💶 烏幣: <strong>${(d.wu_bi||0).toLocaleString()}</strong>`,`📍 <strong>${d.current_node_name||'未知'}</strong>`].map(l=>`<div class="stat-line">${l}</div>`).join('')}
  async loadMarket(){const s=await this.apiGet('/stocks');const me=document.getElementById('market-data');if(s)me.innerHTML=s.map(x=>`<div class="market-row"><span>${x.emoji} ${x.name}</span><span class="${x.change>=0?'up':'down'}">${x.current_price.toLocaleString()} (${x.change>=0?'+':''}${x.change}%)</span></div>`).join('');const p=await this.apiGet('/shop/prices');const sh=document.getElementById('shop-data');if(p)sh.innerHTML=p.map(x=>`<div class="market-row"><span>${x.emoji} ${x.name}</span><span>${x.price.toLocaleString()} 托幣</span></div>`).join('')}
  async loadRankings(){const pw=await this.apiGet('/rankings/power');document.getElementById('rank-power').innerHTML=pw?pw.map((r,i)=>`<div class="rank-row"><span class="rank-pos">${i+1}.</span><span class="rank-name">${r.username}</span><span class="rank-val">${r.score.toLocaleString()} 分</span></div>`).join(''):'<p>無法載入</p>';const wl=await this.apiGet('/rankings/wealth');document.getElementById('rank-wealth').innerHTML=wl?wl.map((r,i)=>`<div class="rank-row"><span class="rank-pos">${i+1}.</span><span class="rank-name">${r.username}</span><span class="rank-val">${r.an_bi.toLocaleString()} 安幣</span></div>`).join(''):'<p>無法載入</p>'}
}
new UtopiaApp();
