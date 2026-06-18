"use strict";

// --- state ---------------------------------------------------------------
const HIDDEN_KEY = "flashcards.hidden"; // ids the user has moved to backlog

let allCards = [];       // every card from cards.json
let items = [];          // current rotation (active or backlog), in display order
let index = 0;
let flipped = false;

const $ = (id) => document.getElementById(id);

function loadHidden() {
  try { return new Set(JSON.parse(localStorage.getItem(HIDDEN_KEY)) || []); }
  catch { return new Set(); }
}
function saveHidden(set) {
  localStorage.setItem(HIDDEN_KEY, JSON.stringify([...set]));
}

// --- rotation building ---------------------------------------------------
function shuffle(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

function rebuild(resetIndex) {
  const hidden = loadHidden();
  const showBacklog = $("backlog").checked;
  items = allCards.filter((c) => hidden.has(c.id) === showBacklog);
  if ($("shuffle").checked) shuffle(items);
  if (resetIndex || index >= items.length) index = 0;
  $("move").textContent = showBacklog ? "Restore" : "Hide";
  render();
}

// --- rendering -----------------------------------------------------------
function render() {
  flipped = false;
  $("card").classList.remove("flipped");
  const showBacklog = $("backlog").checked;
  const mode = showBacklog ? "backlog" : "active";

  if (items.length === 0) {
    $("title").textContent = `(${mode}) — no cards`;
    $("category").textContent = "";
    $("content").textContent = "";
    $("face").textContent = "";
    return;
  }
  const card = items[index];
  $("title").textContent = `${card.id}    ${index + 1} of ${items.length}`;
  $("category").textContent = card.category ? `CATEGORY · ${card.category.toUpperCase()}` : "";
  $("content").textContent = card.front;
  $("face").textContent = "FRONT — tap to flip";
}

function flip() {
  if (items.length === 0) return;
  flipped = !flipped;
  const card = items[index];
  $("card").classList.toggle("flipped", flipped);
  $("content").textContent = flipped ? card.back : card.front;
  $("face").textContent = flipped ? "BACK — tap to flip" : "FRONT — tap to flip";
}

function next() { if (items.length) { index = (index + 1) % items.length; render(); } }
function prev() { if (items.length) { index = (index - 1 + items.length) % items.length; render(); } }

function toggleHidden() {
  if (items.length === 0) return;
  const id = items[index].id;
  const hidden = loadHidden();
  if (hidden.has(id)) hidden.delete(id); else hidden.add(id);
  saveHidden(hidden);
  const prevIndex = index;
  rebuild(false);
  if (items.length) { index = Math.min(prevIndex, items.length - 1); render(); }
}

// --- jump ----------------------------------------------------------------
function openJump() {
  if (items.length === 0) return;
  $("jumpLabel").textContent = `Go to card #  (1 – ${items.length})`;
  $("jumpInput").value = String(index + 1);
  $("jumpModal").classList.remove("hidden");
  $("jumpInput").focus();
  $("jumpInput").select();
}
function doJump() {
  const n = parseInt($("jumpInput").value, 10);
  if (!Number.isNaN(n)) { index = Math.max(0, Math.min(items.length - 1, n - 1)); render(); }
  $("jumpModal").classList.add("hidden");
}

// --- search --------------------------------------------------------------
function snippet(text, q) {
  const pos = text.toLowerCase().indexOf(q);
  if (pos === -1) return null;
  const start = Math.max(0, pos - 30);
  const end = Math.min(text.length, pos + q.length + 50);
  let s = text.slice(start, end).replace(/\n/g, " ").trim();
  if (start > 0) s = "…" + s;
  if (end < text.length) s = s + "…";
  return s;
}

function refreshSearch() {
  const q = $("searchInput").value.trim().toLowerCase();
  const box = $("searchResults");
  box.innerHTML = "";
  if (!q) { $("searchCount").textContent = `${items.length} cards — type to search`; return; }
  let matches = 0;
  for (const card of items) {
    let hit = null, field = "";
    for (const [name, val] of [["Category", card.category], ["Front", card.front], ["Back", card.back]]) {
      const s = snippet(val || "", q);
      if (s) { hit = s; field = name; break; }
    }
    if (!hit) continue;
    matches++;
    const el = document.createElement("button");
    el.className = "result";
    el.innerHTML = `<span class="rid">${card.id}</span>${field}: ${escapeHtml(hit)}`;
    el.addEventListener("click", () => {
      const i = items.indexOf(card);
      if (i >= 0) { index = i; render(); }
      $("searchModal").classList.add("hidden");
    });
    box.appendChild(el);
  }
  $("searchCount").textContent = `${matches} match${matches === 1 ? "" : "es"}`;
}

function escapeHtml(s) {
  return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function openSearch() {
  if (items.length === 0) return;
  $("searchInput").value = "";
  $("searchModal").classList.remove("hidden");
  refreshSearch();
  $("searchInput").focus();
}

// --- wiring --------------------------------------------------------------
function wire() {
  $("card").addEventListener("click", flip);
  $("flip").addEventListener("click", (e) => { e.stopPropagation(); flip(); });
  $("next").addEventListener("click", next);
  $("prev").addEventListener("click", prev);
  $("move").addEventListener("click", toggleHidden);
  $("shuffle").addEventListener("change", () => rebuild(true));
  $("backlog").addEventListener("change", () => rebuild(true));

  $("jump").addEventListener("click", openJump);
  $("jumpGo").addEventListener("click", doJump);
  $("jumpClose").addEventListener("click", () => $("jumpModal").classList.add("hidden"));
  $("jumpInput").addEventListener("keydown", (e) => { if (e.key === "Enter") doJump(); });

  $("search").addEventListener("click", openSearch);
  $("searchInput").addEventListener("input", refreshSearch);
  $("searchClose").addEventListener("click", () => $("searchModal").classList.add("hidden"));

  // close modals by tapping the backdrop
  for (const m of [$("searchModal"), $("jumpModal")]) {
    m.addEventListener("click", (e) => { if (e.target === m) m.classList.add("hidden"); });
  }

  // keyboard (handy when testing in a desktop browser)
  document.addEventListener("keydown", (e) => {
    if (!$("searchModal").classList.contains("hidden") || !$("jumpModal").classList.contains("hidden")) {
      if (e.key === "Escape") { $("searchModal").classList.add("hidden"); $("jumpModal").classList.add("hidden"); }
      return;
    }
    if (e.key === " ") { e.preventDefault(); flip(); }
    else if (e.key === "ArrowRight" || e.key === "d") next();
    else if (e.key === "ArrowLeft" || e.key === "a") prev();
    else if (e.key === "g") openJump();
    else if (e.key === "f" || e.key === "/") { e.preventDefault(); openSearch(); }
    else if (e.key === "b") { $("backlog").checked = !$("backlog").checked; rebuild(true); }
  });
}

// --- boot ----------------------------------------------------------------
async function boot() {
  wire();
  try {
    const res = await fetch("cards.json", { cache: "no-cache" });
    allCards = await res.json();
  } catch (err) {
    $("title").textContent = "Failed to load cards.json";
    return;
  }
  rebuild(true);

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }
}

boot();
