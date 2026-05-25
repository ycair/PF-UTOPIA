# v0.dev Prompt — PF UTOPIA Web Dashboard

## Project Overview
PF UTOPIA (安逸烏托邦) is a Discord-based MMORPG text game with 14 interconnected nodes on a pixel-art world map. Players explore, fight, trade, pray, and invest through Discord slash commands. This website is the companion dashboard where players view the world map, check their stats, browse the market, and see rankings.

The aesthetic is **retro 16-bit pixel RPG journal** — think classic JRPG menu screens, dark backgrounds, gold/amber accents, pixel-perfect rendering.

## What We Have (Functional, Not Pretty)
All files are in `web/`:

| File | Purpose |
|------|---------|
| `index.html` | Main HTML with tab navigation (map, profile, market, ranking) + Discord login button |
| `style.css` | Functional CSS (dark theme, pixel font, basic layout) |
| `map.js` | Interactive canvas map (pan/zoom, node markers, player position glow) + tab switching + API fetchers |
| `callback.html` | Discord OAuth callback handler |
| `map_config.json` | 14 node pixel coordinates + 14 edge definitions |
| `assets/map.png` | **The hero image** — 2528×1696 hand-drawn pixel art world map (9MB) |
| `assets/elements.png` | Individual sprite elements (3.6MB) |

### API Endpoints (Running on Same Server)
All return JSON, require `Authorization: Bearer <jwt>` header (except auth):

| Endpoint | Returns |
|----------|---------|
| `GET /api/me` | Player stats: username, ATK, DEF, HP, current_hp, stamina, 5 currencies, current_node_name, unlocked_nodes |
| `GET /api/stocks` | 6 stock prices with % change |
| `GET /api/shop/prices` | 10 material sell prices with emoji |
| `GET /api/rankings/power` | Top 10 by combat score |
| `GET /api/rankings/wealth` | Top 10 by an_bi wealth |
| `GET /api/auth/callback?code=` | Exchange Discord OAuth code for JWT |

### Discord OAuth Flow
1. User clicks "Discord 登入" → redirected to Discord OAuth
2. Discord redirects to `/callback.html?code=xxx`
3. Callback calls `/api/auth/callback?code=xxx`
4. Gets JWT token → stored in localStorage → all API calls use it

## What We Need From v0.dev

### 1. Map Page (`#page-map`) — THE HERO
The map is the homepage. `assets/map.png` is displayed on a canvas. Currently functional but needs visual magic:
- Node markers should look like glowing pins/beacons on the map, not just emoji text
- Player position should be a prominent animated marker (pulsing glow ring + player sprite)
- Fog of war for undiscovered nodes: dark mist overlay with "???" that clears when explored
- Road lines between nodes with danger-level coloring (red=high danger, green=safe)
- Tooltip on hover should look like an in-game dialogue box (dark panel with gold border)
- A minimap or zoom indicator in the corner

### 2. Top Navigation Bar
Current: functional tabs. Needed:
- PF UTOPIA brand logo/title with pixel-art styling
- Tab buttons with pixel borders, active state with glow
- Discord login button → after login, show player avatar + name
- Subtle background pattern or border decoration

### 3. Profile Page (`#page-profile`)
Show all player stats in a character sheet style:
- Character name prominently displayed
- HP bar (colored segments showing current/max)
- Stats grouped: Combat (ATK/DEF), Vitals (HP/Stamina), Currencies (5 types with icons)
- Current location with node name
- 元神/修為 levels if present

### 4. Market Page (`#page-market`)
Two panels side by side:
- **Stocks**: 6 turtle stocks with price, % change, colored arrows (green up/red down)
- **Shop Prices**: 10 materials with current sell price, trend indicator

### 5. Rankings Page (`#page-ranking`)
Two columns:
- Combat Power ranking (🥇🥈🥉 medals for top 3)
- Wealth ranking

### Visual Design Direction
```
Tone: Dark fantasy pixel RPG journal
Colors: Deep charcoal bg (#0a0a0f), warm gold accents (#c9a84c), teal highlights (#3a8a7a)
Font: 'Press Start 2P' for headers, pixel-readable for body
Effects: Subtle glow on interactive elements, pixel-perfect borders (2px solid)
Animations: Gentle pulse on player marker, smooth page transitions, hover glows
Spatial: Clean grid-based layout, generous padding, distinct panel separation
```

### Technical Constraints
- Keep existing HTML structure (`#page-map`, `#page-profile`, etc.) — IDs must stay
- Keep existing JavaScript API calls (`apiGet()`, `loadPlayerData()`, etc.) — function signatures must stay
- Keep existing Discord OAuth flow unchanged
- Keep `map_config.json` format unchanged
- Canvas-based map rendering is fine to redesign completely
- All files are vanilla HTML/CSS/JS — no React/Vue frameworks
- The site must remain a single-page app (SPA) without page reloads

### File Structure to Return
Please provide updated versions of:
- `index.html` — keep same structure, enhance visuals
- `style.css` — complete redesign
- `map.js` — keep same API/logic, enhance map rendering
- Do NOT change `callback.html`, `map_config.json`, or `assets/`
