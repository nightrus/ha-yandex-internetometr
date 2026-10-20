/* Yandex Internetometr card — bundled with the yandex_internetometr integration. */

const CARD_VERSION = "1.0.0";
const PLATFORM = "yandex_internetometr";
// Config key -> [domain, translation_key] of this integration's entities.
const ROLES = {
  download: ["sensor", "download"],
  upload: ["sensor", "upload"],
  ping: ["sensor", "ping"],
  refresh: ["button", "run_now"],
  interval: ["number", "update_interval"],
};

// Entities are found through the registry, so renamed entity_ids keep working.
const discover = (hass) => {
  const found = {};
  for (const e of Object.values(hass?.entities || {})) {
    if (e.platform !== PLATFORM) continue;
    for (const [key, [domain, tk]] of Object.entries(ROLES)) {
      if (e.translation_key === tk && e.entity_id.startsWith(domain + ".")) found[key] = e.entity_id;
    }
  }
  return found;
};

const STYLE = `
  :host { display: block; }
  ha-card { overflow: hidden; }
  .head {
    display: flex; align-items: center; gap: 12px;
    padding: 12px 16px 10px;
    border-bottom: 3px solid #e2001a;
  }
  .logo {
    flex: none; width: 34px; height: 34px; border-radius: 8px;
    display: grid; place-items: center;
    background: #e2001a; color: #fff;
  }
  .logo ha-icon { --mdc-icon-size: 22px; }
  .title { flex: 1; min-width: 0; }
  .title .label {
    font-size: 10px; letter-spacing: .14em; text-transform: uppercase;
    color: var(--secondary-text-color);
  }
  .title .name {
    font-size: 19px; font-weight: 700; letter-spacing: .03em; text-transform: uppercase;
    color: var(--primary-text-color);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .clock, .num {
    font-family: "DejaVu Sans Mono", "Roboto Mono", ui-monospace, monospace;
    font-variant-numeric: tabular-nums;
  }
  .clock {
    font-size: 26px; font-weight: 700; color: #ffb000;
    text-shadow: 0 0 8px rgba(255,176,0,.4);
  }
  .clock .colon { animation: blink 1s steps(1) infinite; }
  @keyframes blink { 50% { opacity: .15; } }

  .tiles { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .tile {
    display: flex; flex-direction: column; align-items: center; text-align: center;
    padding: 12px 6px 12px; min-width: 0; cursor: pointer;
  }
  .tile + .tile { border-left: 1px solid var(--divider-color, rgba(127,127,127,.2)); }
  .tile .cap {
    display: flex; align-items: center; gap: 5px;
    font-size: 11px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase;
    color: var(--secondary-text-color);
  }
  .tile .cap ha-icon { --mdc-icon-size: 16px; color: #ffb000; }
  .num {
    margin-top: 6px; font-size: 32px; font-weight: 700; line-height: 1.05; color: #ffb000;
    text-shadow: 0 0 6px rgba(255,176,0,.3);
  }
  .unit { font-size: 11px; color: var(--secondary-text-color); letter-spacing: .06em; }
  .grade { margin-top: 6px; font-size: 11.5px; font-weight: 600; }
  /* value and its grade share the grade colour */
  .tile.good { --g: #4cc35a; }
  .tile.fine { --g: #9be27a; }
  .tile.ok { --g: #d9a441; }
  .tile.bad { --g: #ff5a5a; }
  .tile[class*=" "] .num { color: var(--g); text-shadow: 0 0 6px color-mix(in srgb, var(--g) 35%, transparent); }
  .grade { color: var(--g); }
  .measuring .num { animation: blink 1s steps(1) infinite; }

  .foot {
    display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-wrap: wrap;
    padding: 8px 12px 10px 16px; font-size: 11.5px; color: var(--secondary-text-color);
    border-top: 1px solid var(--divider-color, rgba(127,127,127,.2));
  }
  .foot .when b { color: var(--primary-text-color); font-weight: 600; }
  .ctl { display: flex; align-items: center; gap: 8px; }
  .step {
    display: inline-flex; align-items: center; gap: 2px;
    border: 1px solid var(--divider-color, rgba(127,127,127,.3)); border-radius: 8px; padding: 1px;
  }
  .step span { min-width: 54px; text-align: center; color: var(--primary-text-color); }
  button {
    font: inherit; color: inherit; background: none; border: 0; cursor: pointer;
    display: inline-flex; align-items: center; justify-content: center;
  }
  .step button { width: 24px; height: 24px; border-radius: 6px; }
  .step button:hover { background: rgba(127,127,127,.15); }
  .step button[disabled] { opacity: .35; cursor: default; }
  .run {
    gap: 5px; padding: 5px 10px; border-radius: 8px;
    background: #1e9be9; color: #fff; font-weight: 600; font-size: 12px;
  }
  .run:hover { background: #158bd6; }
  .run[disabled] { opacity: .6; cursor: default; }
  .run ha-icon, .step ha-icon { --mdc-icon-size: 16px; }
  .warn { padding: 16px; color: var(--error-color, #ff5a5a); }

  :host([narrow]) .num { font-size: 24px; }
  :host([narrow]) .head { padding: 10px 12px 8px; }
  :host([narrow]) .title .name { font-size: 16px; }
  :host([narrow]) .clock { font-size: 22px; }
`;

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const num = (st) => {
  const v = Number(st?.state);
  return st && Number.isFinite(v) ? v : null;
};

const fmt = (v) => (v === null ? "—" : v >= 100 ? String(Math.round(v)) : v.toFixed(1).replace(".", ","));

// Rough grades for a home connection.
const gradeSpeed = (v) => (v === null ? null
  : v >= 300 ? ["good", "отлично"] : v >= 50 ? ["fine", "хорошо"] : ["bad", "медленно"]);
const gradePing = (v) => (v === null ? null
  : v <= 20 ? ["good", "отлично"] : v <= 40 ? ["fine", "хорошо"]
  : v <= 80 ? ["ok", "нормально"] : ["bad", "высокий"]);

const createCardClass = (Base) => class YaInternetometrCard extends Base {
  setConfig(config) {
    this._userConfig = config;
    this._config = { ...(this._hass ? discover(this._hass) : {}), ...config };
    this._discovered = !!this._hass?.entities;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
    }
    this._render();
  }

  set hass(hass) {
    if (!this._discovered && hass.entities) {
      this._discovered = true;
      this._config = { ...discover(hass), ...this._userConfig };
    }
    const c = this._config;
    const keys = [c.download, c.upload, c.ping, c.refresh, c.interval].filter(Boolean);
    const changed = !this._hass || keys.some((k) => hass.states[k] !== this._hass.states[k]);
    this._hass = hass;
    if (changed) this._render();
  }

  connectedCallback() {
    this._timer = setInterval(() => this._render(), 15000);
    this._resize = new ResizeObserver(([e]) => this.toggleAttribute("narrow", e.contentRect.width < 420));
    this._resize.observe(this);
  }

  disconnectedCallback() {
    clearInterval(this._timer);
    this._resize?.disconnect();
  }

  getCardSize() {
    return 4;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }

  static getStubConfig() {
    return {};
  }

  _onClick(ev) {
    const el = ev.target.closest("[data-act]");
    if (!el || el.disabled || !this._hass) return;
    const c = this._config;
    const act = el.dataset.act;
    if (act === "run") {
      this._hass.callService("button", "press", { entity_id: c.refresh });
    } else if (act === "more") {
      this.dispatchEvent(new CustomEvent("hass-more-info",
        { detail: { entityId: el.dataset.entity }, bubbles: true, composed: true }));
    } else if (act === "minus" || act === "plus") {
      const st = this._hass.states[c.interval];
      const step = Number(st?.attributes?.step) || 5;
      const min = Number(st?.attributes?.min ?? 0);
      const max = Number(st?.attributes?.max ?? 60);
      const cur = Number(st?.state) || 0;
      const value = Math.min(max, Math.max(min, cur + (act === "plus" ? step : -step)));
      if (value !== cur) {
        this._hass.callService("number", "set_value", { entity_id: c.interval, value });
      }
    }
  }

  _clock() {
    const tz = this._hass?.config?.time_zone;
    const parts = new Intl.DateTimeFormat("ru-RU", {
      hour: "2-digit", minute: "2-digit", hour12: false, ...(tz ? { timeZone: tz } : {}),
    }).formatToParts(new Date());
    const h = parts.find((p) => p.type === "hour")?.value ?? "--";
    const m = parts.find((p) => p.type === "minute")?.value ?? "--";
    return `${h}<span class="colon">:</span>${m}`;
  }

  _tile(entity, icon, caption, unit, grade) {
    const st = this._hass.states[entity];
    const v = num(st);
    const g = grade(v);
    return `
      <div class="tile${g ? " " + g[0] : ""}" data-act="more" data-entity="${esc(entity)}">
        <div class="cap"><ha-icon icon="${icon}"></ha-icon>${caption}</div>
        <div class="num">${fmt(v)}</div>
        <div class="unit">${unit}</div>
        ${g ? `<div class="grade">${g[1]}</div>` : ""}
      </div>`;
  }

  _render() {
    if (!this.shadowRoot || !this._config || !this._hass) return;
    const c = this._config;
    const s = this._hass.states;
    if (!s[c.download] && !s[c.upload] && !s[c.ping]) {
      this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card><div class="warn">
        Сенсоры интеграции «Яндекс Интернетометр» не найдены</div></ha-card>`;
      return;
    }

    const btn = s[c.refresh];
    const measuring = btn?.attributes?.in_progress === true;
    const last = s[c.download]?.attributes?.measured_at
      || s[c.download]?.last_updated || s[c.ping]?.last_updated;
    const tz = this._hass.config?.time_zone;
    const fmtOpts = { hour: "2-digit", minute: "2-digit", ...(tz ? { timeZone: tz } : {}) };
    const lastDate = last ? new Date(last) : null;
    const today = lastDate && lastDate.toDateString() === new Date().toDateString();
    const when = !lastDate ? "—" : today
      ? lastDate.toLocaleTimeString("ru-RU", fmtOpts)
      : lastDate.toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", ...fmtOpts });

    const iv = s[c.interval];
    const ivVal = Number(iv?.state);
    const ivMin = Number(iv?.attributes?.min ?? 0);
    const ivMax = Number(iv?.attributes?.max ?? 60);
    const ivText = !iv ? "" : ivVal > 0 ? `${ivVal} мин` : "выкл";

    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <ha-card class="${measuring ? "measuring" : ""}">
        <div class="head">
          <div class="logo"><ha-icon icon="mdi:speedometer"></ha-icon></div>
          <div class="title">
            <div class="label">Интернет · ${measuring ? "идёт замер…" : "скорость соединения"}</div>
            <div class="name">${esc(c.title || "Интернетометр")}</div>
          </div>
          <div class="clock">${this._clock()}</div>
        </div>
        <div class="tiles">
          ${this._tile(c.download, "mdi:download", "Загрузка", "Мбит/с", gradeSpeed)}
          ${this._tile(c.upload, "mdi:upload", "Отдача", "Мбит/с", gradeSpeed)}
          ${this._tile(c.ping, "mdi:timer-outline", "Пинг", "мс", gradePing)}
        </div>
        <div class="foot">
          <span class="when">замер <b>${esc(when)}</b></span>
          <span class="ctl">
            ${iv ? `<span class="step" title="Интервал автоматического замера">
              <button data-act="minus" ${ivVal <= ivMin ? "disabled" : ""}><ha-icon icon="mdi:minus"></ha-icon></button>
              <span>${ivText}</span>
              <button data-act="plus" ${ivVal >= ivMax ? "disabled" : ""}><ha-icon icon="mdi:plus"></ha-icon></button>
            </span>` : ""}
            ${btn ? `<button class="run" data-act="run" ${measuring ? "disabled" : ""}>
              <ha-icon icon="mdi:refresh"></ha-icon>${measuring ? "Замер…" : "Измерить"}</button>` : ""}
          </span>
        </div>
      </ha-card>`;
  }
};

/*
 * browser_mod and hui-element load the @webcomponents/scoped-custom-element-registry
 * polyfill, which replaces window.customElements and window.HTMLElement. An element
 * registered before the swap is invisible to the new registry ("Custom element doesn't
 * exist"), and one extending the native HTMLElement is refused by the polyfilled
 * define. So build the class from the live globals and retry after the polyfill
 * had a chance to load; get() guards make repeat passes no-ops.
 */
function defineInternetometrCard() {
  const reg = window.customElements;
  if (!reg) return;
  if (!reg.get("yandex-internetometr-card")) {
    reg.define("yandex-internetometr-card", createCardClass(window.HTMLElement));
  }
}

defineInternetometrCard();
if (!window.__yandexInternetometrCardScheduled) {
  window.__yandexInternetometrCardScheduled = true;
  const retry = () => {
    try {
      defineInternetometrCard();
    } catch (_) {
      /* a concurrent registry swap is harmless; the next pass settles it */
    }
  };
  Promise.resolve().then(retry);
  requestAnimationFrame(retry);
  setTimeout(retry, 0);
  setTimeout(retry, 1000);
  setTimeout(retry, 5000);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "yandex-internetometr-card")) window.customCards.push({
  type: "yandex-internetometr-card",
  name: "Интернетометр",
  description: "Скорость интернета (интеграция «Яндекс Интернетометр»)",
  preview: true,
});

console.info(`%c YANDEX-INTERNETOMETR-CARD %c ${CARD_VERSION} `,
  "background:#e2001a;color:#fff;font-weight:700", "background:#12306b;color:#fff");
