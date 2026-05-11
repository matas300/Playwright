"use strict";

const elScanBtn = document.getElementById("btn-scan");
const elResults = document.getElementById("results");
const elProgress = document.getElementById("progress");
const elProgressFill = document.getElementById("progress-fill");
const elProgressLabel = document.getElementById("progress-label");
const elScanStatus = document.getElementById("scan-status");
const elFilters = document.getElementById("filters");
const elLoginBtn = document.getElementById("btn-login");
const elTierStats = document.getElementById("tier-stats");

let pollTimer = null;

const ALLOWED_HOSTS = new Set([
  "www.facebook.com",
  "facebook.com",
  "m.facebook.com",
  "mbasic.facebook.com",
  "scontent.fbcdn.net",
  "scontent.xx.fbcdn.net",
]);

function safeUrl(url) {
  if (typeof url !== "string") return null;
  try {
    const u = new URL(url);
    if (u.protocol !== "https:" && u.protocol !== "http:") return null;
    if (!ALLOWED_HOSTS.has(u.host) && !u.host.endsWith(".fbcdn.net") && !u.host.endsWith(".facebook.com")) {
      return null;
    }
    return u.toString();
  } catch {
    return null;
  }
}

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "dataset") for (const [dk, dv] of Object.entries(v)) node.dataset[dk] = dv;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const c of children) {
    if (c == null) continue;
    if (typeof c === "string") node.appendChild(document.createTextNode(c));
    else node.appendChild(c);
  }
  return node;
}

function tierEmoji(t) {
  return { S: "⭐", A: "⭐", B: "👍", C: "🤷", D: "🟡", E: "🔴", over_budget: "💸" }[t] || "·";
}

function renderCard(p) {
  const card = el("article", { class: "card", dataset: { id: p.id } });

  const photos = (p.photo_urls || []).map(safeUrl).filter(Boolean).slice(0, 4);
  if (photos[0]) {
    card.appendChild(el("img", { class: "photo", src: photos[0], alt: "", loading: "lazy" }));
  } else {
    card.appendChild(el("div", { class: "photo" }));
  }
  if (photos.length > 1) {
    const strip = el("div", { class: "photo-strip" });
    for (const u of photos.slice(1)) strip.appendChild(el("img", { src: u, alt: "", loading: "lazy" }));
    card.appendChild(strip);
  }

  const body = el("div", { class: "body" });

  const priceText = p.price_eur ? `€${p.price_eur}/mese` : "💰 prezzo non trovato";
  const badge = el("span", { class: `tier-badge tier-${p.tier}` }, `${tierEmoji(p.tier)} ${p.tier}`);
  body.appendChild(el("div", {}, badge, " ", priceText));

  const datesText = p.date_start && p.date_end
    ? `📅 ${p.date_start} → ${p.date_end}`
    : "📅 date non trovate";
  const nbText = p.neighborhood ? `📍 ${p.neighborhood}` : "📍 quartiere non riconosciuto";
  body.appendChild(el("div", { class: "meta" }, `${datesText} · ${nbText}`));

  body.appendChild(el("div", { class: "text-it" }, p.text_translated || "[traduzione non disponibile]"));
  body.appendChild(el("div", { class: "text-lt" }, p.text_original || ""));

  const actions = el("div", { class: "actions" });
  const fbUrl = safeUrl(p.url);
  if (fbUrl) {
    actions.appendChild(el("a", { class: "fb-link", href: fbUrl, target: "_blank", rel: "noopener noreferrer" }, "🔗 FB"));
  }
  const toggleBtn = el("button", {
    onclick: () => {
      card.classList.toggle("show-lt");
      toggleBtn.textContent = card.classList.contains("show-lt") ? "Nascondi LT" : "Mostra LT";
    },
  }, "Mostra LT");
  actions.appendChild(toggleBtn);

  const ignoreBtn = el("button", {
    onclick: async () => {
      await fetch(`/api/posts/${encodeURIComponent(p.id)}/ignore`, { method: "POST" });
      card.style.opacity = "0";
      setTimeout(() => card.remove(), 200);
    },
  }, "✖ Ignora");
  actions.appendChild(ignoreBtn);

  body.appendChild(actions);
  card.appendChild(body);
  return card;
}

async function refreshTierStats() {
  if (!elTierStats) return;
  try {
    const r = await fetch("/api/debug/stats");
    const s = await r.json();
    const tc = s.tier_counts || {};
    const order = ["S", "A", "B", "C", "D", "E", "over_budget", "skip"];
    const emoji = { S: "⭐", A: "⭐", B: "👍", C: "🤷", D: "🟡", E: "🔴", over_budget: "💸", skip: "⏭" };
    const parts = order.filter(t => tc[t]).map(t => `${emoji[t]}${t}:${tc[t]}`);
    const other = Object.keys(tc).filter(k => !order.includes(k)).map(k => `${k}:${tc[k]}`);
    elTierStats.textContent = "📊 " + [...parts, ...other].join(" · ");
  } catch (e) {
    elTierStats.textContent = "";
  }
}

async function refreshPosts() {
  const tiers = [...document.querySelectorAll(".filter-tier:checked")].map(e => e.value);
  const includeIgnored = document.getElementById("filter-include-ignored").checked;
  const priceMin = parseInt(document.getElementById("filter-price-min").value) || 0;
  const priceMax = parseInt(document.getElementById("filter-price-max").value) || 99999;
  const allowedNbTiers = new Set([...document.querySelectorAll(".filter-tier-nb:checked")].map(e => e.value));

  const url = `/api/posts?tiers=${encodeURIComponent(tiers.join(","))}&include_ignored=${includeIgnored}`;
  const r = await fetch(url);
  let posts = await r.json();

  posts = posts.filter(p => {
    if (p.price_eur != null && (p.price_eur < priceMin || p.price_eur > priceMax)) return false;
    if (p.neighborhood_tier && !allowedNbTiers.has(p.neighborhood_tier)) return false;
    return true;
  });

  elResults.replaceChildren(...posts.map(renderCard));
}

async function pollStatus() {
  const r = await fetch("/api/status");
  const s = await r.json();
  if (s.status === "running") {
    elProgress.style.display = "block";
    const pct = s.progress_total ? (s.progress_current / s.progress_total * 100).toFixed(0) : 0;
    elProgressFill.style.width = `${pct}%`;
    elProgressLabel.textContent = `Scansionando ${s.progress_current}/${s.progress_total}: ${s.current_group_name} — ${s.posts_new} nuovi`;
    elScanBtn.disabled = true;
  } else {
    elProgress.style.display = "none";
    elScanBtn.disabled = false;
    if (s.status === "done") {
      elScanStatus.textContent = `✅ Completato — ${s.posts_new} nuovi su ${s.posts_found}`;
      await refreshTierStats();
      await refreshPosts();
      clearInterval(pollTimer);
      pollTimer = null;
    } else if (s.status === "error") {
      elScanStatus.textContent = `❌ Errore: ${s.error_message || "sconosciuto"}`;
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }
}

elScanBtn?.addEventListener("click", async () => {
  const r = await fetch("/api/scan", { method: "POST" });
  if (r.ok) {
    pollTimer = setInterval(pollStatus, 2000);
    pollStatus();
  }
});

elLoginBtn?.addEventListener("click", async () => {
  await fetch("/api/login", { method: "POST" });
  alert("Apri il Chrome che si è appena lanciato e fai login. La sessione si salva da sola.");
});

elFilters?.addEventListener("change", refreshPosts);

refreshTierStats();
refreshPosts();
