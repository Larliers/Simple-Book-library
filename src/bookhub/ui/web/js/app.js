"use strict";

const State = {
  bridge: null,
  strings: {},
  nav: [],
  pages: {},
  settings: {},
  currentPage: "",
  viewMode: "grid",
  selected: {},
  searchQuery: "",
  suggestOpen: false,
  theme: { mode: "auto", autoEnabled: true, nightStart: "22:00", dayResume: "07:00", checkFrequency: 5, transitionMinutes: 3 },
  themeTimer: null,
  renderGen: 0,
  renderTimer: null,
};

const COMIC_PAGES = new Set(["comic", "comic_fav"]);
const LIST_ONLY = new Set(["text_novel"]);

function t(key, fallback) {
  const value = State.strings[key];
  return value !== undefined ? value : (fallback !== undefined ? fallback : key);
}

function fmt(str, params) {
  return String(str).replace(/\{(\w+)\}/g, (m, k) => (params && params[k] !== undefined ? params[k] : m));
}

function $(id) { return document.getElementById(id); }

function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

function elem(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

/* ---------- bootstrap ---------- */
function initChannel() {
  new QWebChannel(qt.webChannelTransport, (channel) => {
    State.bridge = channel.objects.bridge;
    wireSignals();
    loadBootstrap();
  });
}

function wireSignals() {
  const b = State.bridge;
  b.resourcesChanged.connect((json) => {
    const data = safeParse(json);
    if (data && data.pages) {
      State.pages = data.pages;
      if (State.currentPage !== "settings") scheduleRenderPage();
      refreshDetailIfSelected();
    }
  });
  b.toast.connect((json) => { const d = safeParse(json); if (d) showToast(d.title, d.message, d.kind); });
  b.scanProgress.connect((json) => { const d = safeParse(json); if (d) updateScanProgress(d); });
  b.scanState.connect((json) => { const d = safeParse(json); if (d) updateScanState(d); });
  b.settingsChanged.connect((json) => { const d = safeParse(json); if (d) { State.settings = d; if (d.theme) applyThemeConfig(d.theme); if (State.currentPage === "settings") renderSettings(); } });
  b.errorLogsChanged.connect((text) => { const box = document.getElementById("errorLogBox"); if (box) box.textContent = text; });
}

function safeParse(json) { try { return JSON.parse(json); } catch (e) { return null; } }

function loadBootstrap() {
  State.bridge.getBootstrap((json) => {
    const data = safeParse(json);
    if (!data) return;
    State.strings = data.strings || {};
    State.nav = data.nav || [];
    State.pages = data.pages || {};
    State.settings = data.settings || {};
    State.errorLogs = data.errorLogs || "";
    if (State.settings.theme) State.theme = Object.assign(State.theme, State.settings.theme);
    applyStaticStrings();
    applyFont();
    renderNav();
    applyThemeConfig(State.theme);
    startThemeEngine();
    selectPage("library");
  });
}

window.__reloadBootstrap = loadBootstrap;

function applyStaticStrings() {
  document.querySelectorAll("[data-str]").forEach((node) => {
    node.textContent = t(node.getAttribute("data-str"));
  });
  const search = $("searchInput");
  search.setAttribute("placeholder", t("topbar.search_placeholder"));
}

function applyFont() {
  const family = State.settings.fontFamily;
  if (family) {
    document.documentElement.style.setProperty(
      "--font",
      '"' + family + '", Inter, "Segoe UI", "Microsoft YaHei", Arial, sans-serif'
    );
  }
  const size = State.settings.searchFontSize;
  if (size) $("searchInput").style.fontSize = size + "px";
}

/* ---------- navigation ---------- */
function renderNav() {
  const list = $("navList");
  clear(list);
  State.nav.forEach((item) => {
    const btn = elem("button", "nav-btn", item.label);
    btn.dataset.page = item.page;
    btn.addEventListener("click", () => selectPage(item.page));
    list.appendChild(btn);
  });
}

function selectPage(page) {
  // Same-page nav click: avoid wiping/rebuilding hundreds of cards.
  if (page === State.currentPage && page !== "settings") return;
  State.currentPage = page;
  document.querySelectorAll(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.page === page));
  $("settingsBtn").classList.toggle("active", page === "settings");
  const detail = $("detailPanel");
  if (page === "settings") {
    detail.classList.add("hidden");
    renderSettings();
    return;
  }
  detail.classList.remove("hidden");
  // sync search box to page context
  const isText = page === "text_novel";
  $("searchInput").setAttribute("placeholder", isText ? t("topbar.search_text_placeholder") : t("topbar.search_placeholder"));
  scheduleRenderPage();
  renderDetailEmpty();
}

function scheduleRenderPage() {
  State.renderGen += 1;
  const gen = State.renderGen;
  if (State.renderTimer) {
    clearTimeout(State.renderTimer);
    State.renderTimer = null;
  }
  // Yield so nav/topbar paint before heavy content rebuild (esp. comic waterfall).
  State.renderTimer = setTimeout(() => {
    State.renderTimer = null;
    if (gen !== State.renderGen) return;
    renderPage(gen);
  }, 0);
}

/* ---------- page rendering ---------- */
function currentPageData() { return State.pages[State.currentPage] || { items: [], mode: "grid_or_list" }; }

function renderPage(expectedGen) {
  const gen = expectedGen != null ? expectedGen : State.renderGen;
  const page = State.currentPage;
  const data = currentPageData();
  const titleItem = State.nav.find((n) => n.page === page);
  $("pageTitle").textContent = (data.mode === "collection_detail" && data.collectionName) ? data.collectionName : (titleItem ? titleItem.label : page);
  const count = (data.items || []).length;
  $("pageSubtitle").textContent = fmt(t("page.count", "{count} items"), { count });

  renderPageTools(page, data);

  const area = $("contentArea");
  if (gen !== State.renderGen) return;
  clear(area);
  area.classList.remove("view-enter"); void area.offsetWidth; area.classList.add("view-enter");

  const showViewToggle = !COMIC_PAGES.has(page) && !LIST_ONLY.has(page) && data.mode !== "collections";
  $("viewModeToggle").style.display = showViewToggle ? "" : "none";

  if (!count) {
    area.appendChild(buildEmpty(t("empty.default", "Nothing here yet.")));
    return;
  }

  if (page === "text_novel") { renderTable(area, data.items, page); return; }
  if (data.mode === "collections") { renderCollections(area, data.items); return; }
  if (COMIC_PAGES.has(page)) { renderComic(area, data, gen); return; }
  if (State.viewMode === "list") { renderTable(area, data.items, page); return; }
  renderGrid(area, data.items, page, data.mode === "collection_detail", gen);
}

function renderPageTools(page, data) {
  const tools = $("pageHeadTools");
  clear(tools);
  if (data.mode === "collection_detail") {
    const back = elem("button", "ghost-btn", t("common.back", "Back"));
    back.addEventListener("click", () => {
      State.bridge.closeCollection((json) => { const d = safeParse(json); if (d) { State.pages.collections = d; scheduleRenderPage(); } });
    });
    tools.appendChild(back);
    return;
  }
  if (data.mode === "collections") {
    const add = elem("button", "primary-btn", t("common.new_list", "New List"));
    add.addEventListener("click", openNewCollectionModal);
    tools.appendChild(add);
    return;
  }
  if (page === "favorites") {
    const wrap = elem("div", "page-sort");
    wrap.appendChild(elem("span", "small-note", t("favorites.sort.label", "Sort")));
    const seg = elem("div", "segmented");
    [["desc", "favorites.sort.added_desc", "Added Time: Newest First"],
     ["asc", "favorites.sort.added_asc", "Added Time: Oldest First"]].forEach(([value, key, fb]) => {
      const btn = elem("button", (data.sort || "desc") === value ? "active" : null, t(key, fb));
      btn.addEventListener("click", () => {
        State.bridge.setPageSort("favorites", value, (json) => {
          const d = safeParse(json);
          if (d) { State.pages.favorites = d; scheduleRenderPage(); }
        });
      });
      seg.appendChild(btn);
    });
    wrap.appendChild(seg);
    tools.appendChild(wrap);
    return;
  }
  if (page === "comic" || page === "comic_fav") {
    const wrap = elem("div", "page-sort");
    wrap.appendChild(elem("span", "small-note", t("comic.sort.label", "Sort")));
    const sel = elem("select", "sort-select");
    [
      ["folder_mtime_desc", "comic.sort.folder_mtime_desc", "Folder Date: Newest First"],
      ["folder_mtime_asc", "comic.sort.folder_mtime_asc", "Folder Date: Oldest First"],
      ["folder_name_asc", "comic.sort.folder_name_asc", "Folder Name: A-Z"],
      ["folder_name_desc", "comic.sort.folder_name_desc", "Folder Name: Z-A"],
    ].forEach(([value, key, fb]) => {
      const opt = elem("option", null, t(key, fb));
      opt.value = value;
      if ((data.sort || "folder_mtime_desc") === value) opt.selected = true;
      sel.appendChild(opt);
    });
    sel.addEventListener("change", () => {
      State.bridge.setPageSort(page, sel.value, (json) => {
        const d = safeParse(json);
        if (d) { State.pages[page] = d; State._comicPage = 1; scheduleRenderPage(); }
      });
    });
    wrap.appendChild(sel);
    tools.appendChild(wrap);
  }
}

function renderGrid(area, items, page, isCollectionDetail, gen) {
  const grid = elem("div", "cover-grid");
  area.appendChild(grid);
  const CHUNK = 36;
  let index = 0;
  const appendChunk = () => {
    if (gen != null && gen !== State.renderGen) return;
    const end = Math.min(index + CHUNK, items.length);
    const frag = document.createDocumentFragment();
    for (; index < end; index++) {
      const item = items[index];
      const card = elem("article", "book-card");
      if (State.selected[page] === item.id) card.classList.add("selected");
      card.appendChild(buildCover(item, "cover"));
      card.addEventListener("click", () => selectResource(page, item.id, card));
      card.addEventListener("dblclick", () => State.bridge.openResource(page, item.id));
      card.addEventListener("contextmenu", (e) => { e.preventDefault(); openContextMenu(e, page, item, isCollectionDetail); });
      frag.appendChild(card);
    }
    grid.appendChild(frag);
    if (index < items.length) requestAnimationFrame(appendChunk);
  };
  appendChunk();
}

function renderCollections(area, items) {
  const grid = elem("div", "cover-grid with-meta");
  items.forEach((item) => {
    const card = elem("article", "book-card");
    card.appendChild(buildCover(item, "cover"));
    card.appendChild(elem("div", "card-title", item.title));
    card.appendChild(elem("div", "card-meta", item.meta || ""));
    const openCol = () => {
      State.bridge.openCollection(item.collectionId, (json) => {
        const d = safeParse(json);
        if (d) { State.pages.collections = d; scheduleRenderPage(); }
      });
    };
    card.addEventListener("click", openCol);
    card.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      openCollectionCardMenu(e, item, openCol);
    });
    grid.appendChild(card);
  });
  area.appendChild(grid);
}

function renderComic(area, data, gen) {
  let items = data.items || [];
  const isPagination = data.viewMode === "pagination";
  let pageSize = data.pageSize || 48;
  if (!State._comicPage) State._comicPage = 1;
  let totalPages = 1;
  if (isPagination) {
    totalPages = Math.max(1, Math.ceil(items.length / pageSize));
    if (State._comicPage > totalPages) State._comicPage = totalPages;
    const start = (State._comicPage - 1) * pageSize;
    items = items.slice(start, start + pageSize);
  }
  renderGrid(area, items, State.currentPage, false, gen);
  if (isPagination) {
    const bar = elem("div", "detail-actions");
    bar.style.justifyContent = "flex-end";
    const prev = elem("button", "ghost-btn", t("comic.pagination.prev", "Prev"));
    const label = elem("span", "small-note", fmt(t("comic.pagination.status", "Page {current}/{total}"), { current: State._comicPage, total: totalPages }));
    const next = elem("button", "ghost-btn", t("comic.pagination.next", "Next"));
    prev.disabled = State._comicPage <= 1;
    next.disabled = State._comicPage >= totalPages;
    prev.addEventListener("click", () => { State._comicPage--; scheduleRenderPage(); });
    next.addEventListener("click", () => { State._comicPage++; scheduleRenderPage(); });
    bar.appendChild(prev); bar.appendChild(label); bar.appendChild(next);
    area.appendChild(bar);
  }
}

function renderTable(area, items, page) {
  const table = elem("table", "table");
  const thead = elem("thead");
  const htr = elem("tr");
  [t("detail.cover", "Cover"), t("detail.title", "Title"), t("detail.author", "Author"), t("detail.tags", "Tags"), t("detail.path", "Path")]
    .forEach((h) => htr.appendChild(elem("th", null, h)));
  thead.appendChild(htr);
  table.appendChild(thead);
  const tbody = elem("tbody");
  items.forEach((item) => {
    const tr = elem("tr");
    if (State.selected[page] === item.id) tr.classList.add("selected");
    const coverTd = elem("td");
    if (item.cover) { const img = elem("img", "mini-cover"); img.src = item.cover; coverTd.appendChild(img); }
    tr.appendChild(coverTd);
    tr.appendChild(elem("td", null, item.title));
    tr.appendChild(elem("td", null, item.author || ""));
    tr.appendChild(elem("td", null, (item.tags || []).join(", ")));
    tr.appendChild(elem("td", null, item.path || ""));
    tr.addEventListener("click", () => selectResource(page, item.id, tr));
    tr.addEventListener("dblclick", () => State.bridge.openResource(page, item.id));
    tr.addEventListener("contextmenu", (e) => { e.preventDefault(); openContextMenu(e, page, item, false); });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  area.appendChild(table);
}

function buildCover(item, cls) {
  if (item.cover) {
    const img = elem("img", cls);
    img.src = item.cover;
    img.alt = item.title || "";
    img.loading = "lazy";
    img.onerror = () => { img.replaceWith(buildCoverFallback(item, cls)); };
    return img;
  }
  return buildCoverFallback(item, cls);
}

function buildCoverFallback(item, cls) {
  const box = elem("div", cls === "cover" ? "cover-fallback" : "detail-cover-fallback");
  box.appendChild(elem("span", null, item.title || ""));
  return box;
}

function wrapDetailCover(item) {
  const slot = elem("div", "detail-cover-slot");
  slot.appendChild(buildCover(item, "detail-cover"));
  return slot;
}

function buildEmpty(text) { return elem("div", "empty-state", text); }

/* ---------- selection & detail ---------- */
function selectResource(page, id, node) {
  State.selected[page] = id;
  const container = node.parentElement;
  if (container) container.querySelectorAll(".selected").forEach((n) => n.classList.remove("selected"));
  node.classList.add("selected");
  State.bridge.getDetail(page, id, (json) => { const d = safeParse(json); renderDetail(d); });
}

function refreshDetailIfSelected() {
  const id = State.selected[State.currentPage];
  if (id) State.bridge.getDetail(State.currentPage, id, (json) => renderDetail(safeParse(json)));
}

function renderDetailEmpty() {
  $("detailEmpty").classList.remove("hidden");
  $("detailContent").classList.add("hidden");
}

function renderDetail(d) {
  if (!d || !d.id) { renderDetailEmpty(); return; }
  const empty = $("detailEmpty");
  const content = $("detailContent");
  empty.classList.add("hidden");
  content.classList.remove("hidden");
  clear(content);
  content.appendChild(wrapDetailCover(d));
  content.appendChild(elem("h2", null, d.title));

  const meta = elem("div", "detail-meta");
  const isComic = COMIC_PAGES.has(State.currentPage);
  if (d.author) meta.appendChild(buildDetailBlock(t("detail.author", "Author"), d.author));
  if (d.publisher && d.publisher.toLowerCase() !== "unknown") meta.appendChild(buildDetailBlock(t("detail.publisher", "Publisher"), d.publisher));
  if (isComic && d.imageCount) meta.appendChild(buildDetailBlock(t("detail.images", "Images"), String(d.imageCount)));
  if (d.tags && d.tags.length) meta.appendChild(buildDetailBlock(t("detail.tags", "Tags"), d.tags.join("、")));
  if (d.bookCollections && d.bookCollections.length) {
    meta.appendChild(buildDetailBlock(t("detail.collections", "Collections"), d.bookCollections.map((c) => c.name).join("、")));
  }
  if (d.path) meta.appendChild(buildDetailBlock(t("detail.file", "File"), d.path));
  if (d.info) meta.appendChild(buildDetailBlock(t("detail.preview", "Text Preview"), d.info));
  content.appendChild(meta);

  const actions = elem("div", "detail-actions");
  const openBtn = elem("button", "primary-btn", t("detail.open", "Open"));
  openBtn.addEventListener("click", () => State.bridge.openResource(State.currentPage, d.id));
  actions.appendChild(openBtn);
  const favBtn = elem("button", "ghost-btn", d.isFavorite ? t("detail.favorite_remove", "Remove from Favorites") : t("detail.favorite_add", "Add to Favorites"));
  favBtn.addEventListener("click", () => State.bridge.toggleFavorite(State.currentPage, d.id, () => refreshDetailIfSelected()));
  actions.appendChild(favBtn);
  if (!isComic) {
    const qa = elem("button", "ghost-btn", t("detail.quick_add", "Quick Add"));
    qa.addEventListener("click", () => openQuickAddModal(d));
    actions.appendChild(qa);
  }
  const coverBtn = elem("button", "ghost-btn", t("detail.edit_cover", "Edit Cover"));
  coverBtn.addEventListener("click", () => State.bridge.editCover(d.id));
  actions.appendChild(coverBtn);
  if (State.currentPage === "library" || State.currentPage === "text_novel" || isComic) {
    const removeBtn = elem("button", "danger-btn", t("menu.remove_library", "Remove from Library"));
    removeBtn.addEventListener("click", () => confirmRemoveFromLibrary(State.currentPage, d));
    actions.appendChild(removeBtn);
  }
  content.appendChild(actions);
}

function buildDetailBlock(label, value) {
  const block = elem("div", "detail-block");
  const strong = elem("strong", null, label + "：");
  block.appendChild(strong);
  block.appendChild(document.createTextNode(value));
  return block;
}

/* ---------- context menu ---------- */
function positionContextMenu(event) {
  const menu = $("contextMenu");
  menu.classList.remove("hidden");
  const mw = menu.offsetWidth, mh = menu.offsetHeight;
  let x = event.clientX, y = event.clientY;
  if (x + mw > window.innerWidth) x = window.innerWidth - mw - 8;
  if (y + mh > window.innerHeight) y = window.innerHeight - mh - 8;
  menu.style.left = x + "px";
  menu.style.top = y + "px";
}

function menuAction(label, fn, danger) {
  const btn = elem("button", danger ? "danger-btn" : null, label);
  btn.addEventListener("click", () => { hideContextMenu(); fn(); });
  $("contextMenu").appendChild(btn);
  return btn;
}

function openCollectionCardMenu(event, item, openCol) {
  const menu = $("contextMenu");
  clear(menu);
  menuAction(t("menu.collection_open", "Open"), openCol);
  menu.appendChild(elem("hr"));
  menuAction(t("menu.collection_rename", "Rename"), () => openRenameCollectionModal(item));
  menuAction(t("menu.collection_delete", "Delete"), () => openDeleteCollectionModal(item), true);
  positionContextMenu(event);
}

function openContextMenu(event, page, item, isCollectionDetail) {
  const menu = $("contextMenu");
  clear(menu);
  const isComic = COMIC_PAGES.has(page);
  const isFavorites = page === "favorites";
  menuAction(
    isComic ? t("menu.open_cover", "Open Cover") : t("menu.open_external", "Open External"),
    () => State.bridge.openResource(page, item.id)
  );
  if (!isComic) {
    menuAction(t("menu.open_folder", "Open Folder"), () => State.bridge.openFolder(item.id));
  }
  if (isComic) {
    const favLabel = page === "comic_fav"
      ? t("menu.comic_fav_remove", "Remove from Comic Fav")
      : t("menu.comic_fav_add", "Add to Comic Fav");
    menuAction(favLabel, () => State.bridge.toggleFavorite(page, item.id, () => {}));
    menuAction(t("menu.edit_cover", "Edit Cover..."), () => State.bridge.editCover(item.id));
    menu.appendChild(elem("hr"));
    menuAction(
      t("menu.remove_library", "Remove from Library"),
      () => confirmRemoveFromLibrary(page, item),
      true
    );
  } else {
    menuAction(t("menu.quick_add", "Quick Add Tag / Collection"), () => openQuickAddModal(item));
    menuAction(t("menu.edit_cover", "Edit Cover..."), () => State.bridge.editCover(item.id));
    const favLabel = isFavorites
      ? t("menu.favorite_remove", "Remove from Favorites")
      : t("menu.favorite_add", "Add to Favorites");
    menuAction(favLabel, () => State.bridge.toggleFavorite(page, item.id, () => {}));
    if (isCollectionDetail) {
      const cid = currentPageData().collectionId;
      menu.appendChild(elem("hr"));
      menuAction(
        t("menu.collection_remove", "Remove from Collection"),
        () => State.bridge.removeFromCollection(item.id, cid),
        true
      );
    }
    if (page === "library" || page === "text_novel" || page === "favorites") {
      menu.appendChild(elem("hr"));
      menuAction(
        t("menu.remove_library", "Remove from Library"),
        () => confirmRemoveFromLibrary(page, item),
        true
      );
    }
  }
  positionContextMenu(event);
}

function confirmRemoveFromLibrary(page, item) {
  openModal((modal, close) => {
    modalHeader(modal, t("library.remove.confirm_title", "Remove from Library"), close);
    modal.appendChild(elem("p", "small-note", fmt(
      t("library.remove.confirm_text", "Remove “{title}” from the library database?\nFiles on disk will not be deleted."),
      { title: item.title || item.id || "" }
    )));
    const actions = elem("div", "modal-actions");
    const cancel = elem("button", "ghost-btn", t("common.cancel", "Cancel"));
    cancel.addEventListener("click", close);
    const confirm = elem("button", "danger-btn", t("menu.remove_library", "Remove from Library"));
    confirm.addEventListener("click", () => {
      State.bridge.removeFromLibrary(page, item.id, (ok) => {
        close();
        if (ok) {
          if (State.selected[page] === item.id) {
            delete State.selected[page];
            renderDetailEmpty();
          }
          scheduleRenderPage();
        }
      });
    });
    actions.appendChild(cancel);
    actions.appendChild(confirm);
    modal.appendChild(actions);
  });
}

function hideContextMenu() { $("contextMenu").classList.add("hidden"); }
document.addEventListener("click", (e) => { if (!$("contextMenu").contains(e.target)) hideContextMenu(); });
document.addEventListener("scroll", hideContextMenu, true);
// Block Chromium default menu globally; card handlers still call preventDefault + custom menu.
document.addEventListener("contextmenu", (e) => {
  if ($("contextMenu").contains(e.target)) return;
  if (e.target.closest && e.target.closest(".book-card, .table tbody tr, .context-menu")) return;
  e.preventDefault();
  hideContextMenu();
}, true);

/* ---------- toasts ---------- */
function showToast(title, message, kind) {
  const stack = $("toastStack");
  const toast = elem("div", "toast");
  toast.appendChild(elem("span", "toast-dot"));
  const body = elem("div", "toast-body");
  body.appendChild(elem("strong", null, title || ""));
  if (message) body.appendChild(elem("div", "toast-msg", message));
  toast.appendChild(body);
  stack.appendChild(toast);
  setTimeout(() => {
    toast.classList.add("leaving");
    setTimeout(() => toast.remove(), 240);
  }, 5200);
}

/* ---------- scan progress ---------- */
function updateScanState(d) {
  State._scanRunning = d.running;
  const btn = $("scanBtn");
  if (d.running) { btn.textContent = t("topbar.scanning", "Scanning..."); btn.disabled = true; }
  else { btn.textContent = t("topbar.scan", "Scan"); btn.disabled = false; }
  const bar = document.getElementById("scanProgressBar");
  if (bar && !d.running) bar.style.width = "0%";
}

function updateScanProgress(d) {
  const bar = document.getElementById("scanProgressBar");
  if (!bar) return;
  const pct = d.total > 0 ? Math.min(100, Math.round((d.current / d.total) * 100)) : 0;
  bar.style.width = pct + "%";
  const label = document.getElementById("scanProgressLabel");
  if (label) label.textContent = fmt("{cur}/{tot} · {lbl}", { cur: d.current, tot: d.total, lbl: d.label || "" });
}

/* ---------- modals ---------- */
function openModal(build) {
  const overlay = $("overlay");
  clear(overlay);
  overlay.classList.remove("hidden");
  const modal = elem("div", "modal");
  build(modal, closeModal);
  overlay.appendChild(modal);
  overlay.onclick = (e) => { if (e.target === overlay) closeModal(); };
}
function closeModal() { const o = $("overlay"); o.classList.add("hidden"); clear(o); o.onclick = null; }

function modalHeader(modal, title, onClose) {
  const head = elem("div", "modal-title");
  head.appendChild(elem("h3", null, title));
  const x = elem("button", "close-x", "×");
  x.addEventListener("click", onClose);
  head.appendChild(x);
  modal.appendChild(head);
}

function openNewCollectionModal() {
  openModal((modal, close) => {
    modalHeader(modal, t("common.new_list", "New List"), close);
    const field = elem("div", "field");
    const input = elem("input");
    input.placeholder = t("quick_add.new_collection_placeholder", "New collection name...");
    field.appendChild(input);
    modal.appendChild(field);
    const actions = elem("div", "modal-actions");
    const cancel = elem("button", "ghost-btn", t("common.cancel", "Cancel"));
    cancel.addEventListener("click", close);
    const confirm = elem("button", "primary-btn", t("common.confirm", "Confirm"));
    confirm.addEventListener("click", () => {
      const name = input.value.trim();
      if (!name) return;
      State.bridge.createCollection(name, () => {
        close();
        State.bridge.closeCollection((json) => {
          const d = safeParse(json);
          if (d) { State.pages.collections = d; if (State.currentPage === "collections") scheduleRenderPage(); }
        });
      });
    });
    actions.appendChild(cancel); actions.appendChild(confirm);
    modal.appendChild(actions);
    input.focus();
  });
}

function openRenameCollectionModal(item) {
  openModal((modal, close) => {
    modalHeader(modal, t("collections.rename_title", "Rename Collection"), close);
    const field = elem("div", "field");
    const input = elem("input");
    input.value = item.title || "";
    input.placeholder = t("collections.rename_placeholder", "New name...");
    field.appendChild(input);
    modal.appendChild(field);
    const actions = elem("div", "modal-actions");
    const cancel = elem("button", "ghost-btn", t("common.cancel", "Cancel"));
    cancel.addEventListener("click", close);
    const confirm = elem("button", "primary-btn", t("common.confirm", "Confirm"));
    confirm.addEventListener("click", () => {
      const name = input.value.trim();
      if (!name) return;
      State.bridge.renameCollection(item.collectionId, name, () => {
        close();
        State.bridge.closeCollection((json) => {
          const d = safeParse(json);
          if (d) { State.pages.collections = d; if (State.currentPage === "collections") scheduleRenderPage(); }
        });
      });
    });
    actions.appendChild(cancel); actions.appendChild(confirm);
    modal.appendChild(actions);
    input.focus();
    input.select();
  });
}

function openDeleteCollectionModal(item) {
  openModal((modal, close) => {
    modalHeader(modal, t("collections.delete_title", "Delete Collection"), close);
    modal.appendChild(elem("p", "small-note", t("collections.delete_msg", "Delete this collection? Books will not be removed from the library.")));
    modal.appendChild(elem("p", "small-note", item.title || ""));
    const actions = elem("div", "modal-actions");
    const cancel = elem("button", "ghost-btn", t("common.cancel", "Cancel"));
    cancel.addEventListener("click", close);
    const confirm = elem("button", "danger-btn", t("menu.collection_delete", "Delete"));
    confirm.addEventListener("click", () => {
      State.bridge.deleteCollection(item.collectionId, () => {
        close();
        State.bridge.closeCollection((json) => {
          const d = safeParse(json);
          if (d) { State.pages.collections = d; if (State.currentPage === "collections") scheduleRenderPage(); }
        });
      });
    });
    actions.appendChild(cancel); actions.appendChild(confirm);
    modal.appendChild(actions);
  });
}

function openQuickAddModal(item) {
  openModal((modal, close) => {
    modalHeader(modal, t("detail.quick_add", "Quick Add"), close);
    modal.appendChild(elem("p", "small-note", item.title || ""));

    if (!Array.isArray(item.tags)) item.tags = [];
    const workingTags = item.tags.slice();

    const tagField = elem("div", "field");
    tagField.appendChild(elem("label", null, t("detail.tags", "Tags")));
    const tagInput = elem("input");
    tagInput.placeholder = t("quick_add.tag_placeholder", "Type tag...");
    tagField.appendChild(tagInput);

    const currentChips = elem("div", "chip-row");
    const recentWrap = elem("div", "chip-row");
    recentWrap.classList.add("recent-tags");

    const renderCurrentChips = () => {
      clear(currentChips);
      workingTags.forEach((tag) => {
        const chip = elem("span", "chip");
        chip.appendChild(document.createTextNode(tag));
        const x = elem("span", "chip-x", "×");
        x.addEventListener("click", () => {
          State.bridge.removeTag(item.id, tag);
          const idx = workingTags.indexOf(tag);
          if (idx >= 0) workingTags.splice(idx, 1);
          item.tags = workingTags.slice();
          renderCurrentChips();
        });
        chip.appendChild(x);
        currentChips.appendChild(chip);
      });
    };

    const addTagValue = (value) => {
      const tag = String(value || "").trim();
      if (!tag || workingTags.includes(tag)) return;
      State.bridge.addTag(item.id, tag);
      workingTags.push(tag);
      item.tags = workingTags.slice();
      renderCurrentChips();
    };

    tagInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        addTagValue(tagInput.value);
        tagInput.value = "";
      }
    });
    tagField.appendChild(currentChips);
    tagField.appendChild(elem("div", "kicker mt", t("quick_add.recent_tags", "Recent tags")));
    tagField.appendChild(recentWrap);
    modal.appendChild(tagField);

    State.bridge.getTags((tjson) => {
      const allTags = safeParse(tjson) || [];
      clear(recentWrap);
      allTags.slice(0, 12).forEach((tag) => {
        const chip = elem("button", "chip chip-btn", tag);
        chip.type = "button";
        chip.addEventListener("click", () => addTagValue(tag));
        recentWrap.appendChild(chip);
      });
    });

    modal.appendChild(elem("hr", "modal-divider"));

    const collField = elem("div", "field");
    collField.appendChild(elem("label", null, t("detail.collections", "Collections")));
    const searchInput = elem("input");
    searchInput.placeholder = t("quick_add.collection_placeholder", "Search collections...");
    collField.appendChild(searchInput);
    const list = elem("div", "list-stack mt");
    collField.appendChild(list);
    modal.appendChild(collField);

    const initialMembers = new Set();
    const pendingMembers = new Set();
    let allCollections = [];

    const renderCollectionRows = () => {
      const q = searchInput.value.trim().toLowerCase();
      clear(list);
      allCollections
        .filter((coll) => !q || String(coll.name || "").toLowerCase().includes(q))
        .forEach((coll) => {
          const row = elem("div", "list-item list-item-action");
          row.appendChild(elem("span", null, coll.name));
          const isMember = pendingMembers.has(coll.id);
          const btn = elem(
            "button",
            isMember ? "ghost-btn list-action-btn is-added" : "ghost-btn list-action-btn is-add",
            isMember ? t("quick_add.added", "Added") : t("quick_add.add", "Add")
          );
          btn.type = "button";
          btn.addEventListener("click", (e) => {
            e.stopPropagation();
            if (pendingMembers.has(coll.id)) pendingMembers.delete(coll.id);
            else pendingMembers.add(coll.id);
            renderCollectionRows();
          });
          row.appendChild(btn);
          list.appendChild(row);
        });
    };

    searchInput.addEventListener("input", renderCollectionRows);

    State.bridge.getCollections((cjson) => {
      allCollections = safeParse(cjson) || [];
      State.bridge.getDetail(State.currentPage, item.id, (djson) => {
        const detail = safeParse(djson) || {};
        (detail.bookCollections || []).forEach((c) => {
          initialMembers.add(c.id);
          pendingMembers.add(c.id);
        });
        renderCollectionRows();
      });
    });

    const actions = elem("div", "modal-actions");
    const cancel = elem("button", "ghost-btn", t("common.cancel", "Cancel"));
    cancel.addEventListener("click", () => { close(); refreshDetailIfSelected(); });
    const confirm = elem("button", "primary-btn", t("quick_add.confirm", "Confirm add"));
    confirm.addEventListener("click", () => {
      const ids = new Set([...initialMembers, ...pendingMembers]);
      ids.forEach((cid) => {
        const want = pendingMembers.has(cid);
        const was = initialMembers.has(cid);
        if (want !== was) State.bridge.setCollectionMembership(item.id, cid, want);
      });
      close();
      refreshDetailIfSelected();
    });
    actions.appendChild(cancel);
    actions.appendChild(confirm);
    modal.appendChild(actions);
    renderCurrentChips();
    tagInput.focus();
  });
}

/* ---------- settings ---------- */
const SETTINGS_SECTIONS = [
  ["general", "settings.nav.general"],
  ["appearance", "settings.nav.appearance"],
  ["paths", "settings.nav.paths"],
  ["tasks", "settings.nav.tasks"],
  ["errors", "settings.nav.errors"],
];

function renderSettings() {
  $("pageTitle").textContent = t("settings.title", "Settings");
  $("pageSubtitle").textContent = "";
  clear($("pageHeadTools"));
  $("viewModeToggle").style.display = "none";
  const area = $("contentArea");
  clear(area);
  area.classList.remove("view-enter"); void area.offsetWidth; area.classList.add("view-enter");

  const grid = elem("div", "settings-grid");
  const nav = elem("div", "settings-nav");
  const panel = elem("div");
  panel.style.minWidth = "0";
  if (!State._settingsSection) State._settingsSection = "general";
  SETTINGS_SECTIONS.forEach(([id, key]) => {
    const btn = elem("button", State._settingsSection === id ? "active" : null, t(key));
    btn.addEventListener("click", () => { State._settingsSection = id; renderSettings(); });
    nav.appendChild(btn);
  });
  grid.appendChild(nav);
  grid.appendChild(panel);
  area.appendChild(grid);

  const section = State._settingsSection;
  if (section === "general") renderSettingsGeneral(panel);
  else if (section === "appearance") renderSettingsAppearance(panel);
  else if (section === "paths") renderSettingsPaths(panel);
  else if (section === "tasks") renderSettingsTasks(panel);
  else renderSettingsErrors(panel);
}

function settingCard(title) {
  const card = elem("div", "settings-card");
  if (title) card.appendChild(elem("h3", null, title));
  return card;
}

function selectField(labelKey, key, options, current) {
  const field = elem("div", "field");
  field.appendChild(elem("label", null, t(labelKey)));
  const sel = elem("select");
  options.forEach(([value, label]) => {
    const opt = elem("option", null, label);
    opt.value = value;
    if (String(value) === String(current)) opt.selected = true;
    sel.appendChild(opt);
  });
  sel.addEventListener("change", () => State.bridge.setSetting(key, String(sel.value)));
  field.appendChild(sel);
  return field;
}

function switchField(labelKey, key, checked) {
  const field = elem("div", "field field-inline");
  const label = elem("label", null, t(labelKey));
  label.style.marginBottom = "0";
  const sw = elem("label", "switch");
  const input = elem("input"); input.type = "checkbox"; input.checked = !!checked;
  input.addEventListener("change", () => State.bridge.setSetting(key, input.checked ? "true" : "false"));
  sw.appendChild(input);
  sw.appendChild(elem("span", "track"));
  field.appendChild(label);
  field.appendChild(sw);
  return field;
}

function textField(labelKey, key, value, type) {
  const field = elem("div", "field");
  field.appendChild(elem("label", null, t(labelKey)));
  const input = elem("input");
  input.type = type || "text";
  input.value = value || "";
  input.addEventListener("change", () => State.bridge.setSetting(key, String(input.value)));
  field.appendChild(input);
  return field;
}

function renderSettingsGeneral(panel) {
  const s = State.settings;
  const card = settingCard(t("settings.nav.general", "General"));
  const grid = elem("div", "form-grid");
  grid.appendChild(selectField("settings.language", "language", [["en", "English"], ["zh-cn", "简体中文"]], s.language));
  grid.appendChild(selectField("settings.search_font", "searchFontSize", [[12,"12"],[15,"15"],[18,"18"],[20,"20"]], s.searchFontSize));
  grid.appendChild(selectField("settings.scan_depth", "scanDepth", [[1,"1"],[2,"2"],[3,"3"]], s.scanDepth));
  grid.appendChild(selectField("settings.hash", "hashStrategy", [["size_mtime", t("settings.hash.fast", "Fast")], ["sha256", t("settings.hash.strict", "Strict")], ["quick", t("settings.hash.quick", "Quick")]], s.hashStrategy));
  grid.appendChild(selectField("settings.card_spacing", "cardSpacing", [[10,"10"],[14,"14"],[18,"18"],[22,"22"]], s.cardSpacing));
  grid.appendChild(selectField("settings.text_preview_chars", "textPreviewChars", [[500,"500"],[1000,"1000"],[2000,"2000"]], s.textPreviewChars));
  grid.appendChild(selectField("settings.comic_view_mode", "comicViewMode", [["waterfall", t("settings.comic_view_waterfall", "Waterfall")],["pagination", t("settings.comic_view_pagination", "Pagination")]], s.comicViewMode));
  grid.appendChild(selectField("settings.comic_page_size", "comicPageSize", [[24,"24"],[48,"48"],[72,"72"],[96,"96"]], s.comicPageSize));
  grid.appendChild(selectField("settings.comic.thumbnail_workers", "comicThumbnailWorkers", [
    ["auto", t("settings.comic.workers.auto", "Auto")],
    ["2", "2"], ["4", "4"], ["6", "6"], ["8", "8"], ["12", "12"], ["16", "16"],
  ], s.comicThumbnailWorkers || "auto"));
  card.appendChild(grid);
  const toggles = elem("div", "form-grid");
  toggles.appendChild(switchField("settings.scan_startup", "scanOnStartup", s.scanOnStartup));
  toggles.appendChild(switchField("settings.auto_scan", "autoScanOnPathChange", s.autoScanOnPathChange));
  toggles.appendChild(switchField("settings.comic.placeholder_copy", "comicPlaceholderCopy", s.comicPlaceholderCopy));
  toggles.appendChild(switchField("settings.comic.auto_thumb_after_scan", "autoGenerateComicThumbs", s.autoGenerateComicThumbs));
  card.appendChild(toggles);
  panel.appendChild(card);
}

function renderSettingsAppearance(panel) {
  const s = State.settings;
  const fontCard = settingCard(t("settings.nav.appearance", "Appearance & Theme"));
  const grid = elem("div", "form-grid");
  grid.appendChild(selectField("settings.font_source", "fontSource", [["system", t("settings.font_source.system", "System")],["project", t("settings.font_source.project", "Project fonts")]], s.fontSource));
  const fontOptions = [["", t("settings.font_family.default", "(default)")]].concat((s.projectFonts || []).map((f) => [f, f]));
  grid.appendChild(selectField("settings.font_family", "fontFamily", fontOptions, s.fontFamily));
  grid.appendChild(selectField("settings.cover_border_width", "coverBorderWidth", [[1,"1"],[2,"2"],[3,"3"],[4,"4"]], s.coverBorderWidth));
  grid.appendChild(textField("settings.cover_border_color", "coverBorderColor", s.coverBorderColor, "text"));
  fontCard.appendChild(grid);
  panel.appendChild(fontCard);

  const themeCard = settingCard(t("settings.night.title", "Night mode"));
  themeCard.appendChild(elem("p", "small-note", t("settings.night.desc", "Read local time periodically and transition between day and night UI.")));
  const seg = elem("div", "segmented");
  [["auto","theme.auto"],["day","theme.day"],["night","theme.night"]].forEach(([mode, key]) => {
    const btn = elem("button", State.theme.mode === mode ? "active" : null, t(key));
    btn.addEventListener("click", () => { setThemeMode(mode); renderSettings(); });
    seg.appendChild(btn);
  });
  const segWrap = elem("div", "field");
  segWrap.appendChild(elem("label", null, t("settings.night.mode", "Theme mode")));
  segWrap.appendChild(seg);
  themeCard.appendChild(segWrap);

  const tgrid = elem("div", "form-grid");
  tgrid.appendChild(switchField("settings.night.auto", "__themeAuto", State.theme.autoEnabled));
  tgrid.querySelector("input").addEventListener("change", (e) => { State.theme.autoEnabled = e.target.checked; persistTheme(); startThemeEngine(); });
  tgrid.appendChild(themeTimeField("settings.night.start", "nightStart", State.theme.nightStart));
  tgrid.appendChild(themeTimeField("settings.night.resume", "dayResume", State.theme.dayResume));
  tgrid.appendChild(themeSelectField("settings.night.frequency", "checkFrequency", [[1,"1"],[5,"5"],[15,"15"],[30,"30"]], State.theme.checkFrequency));
  tgrid.appendChild(themeSelectField("settings.night.transition", "transitionMinutes", [[1,"1"],[3,"3"],[5,"5"],[10,"10"]], State.theme.transitionMinutes));
  themeCard.appendChild(tgrid);
  panel.appendChild(themeCard);
}

function themeTimeField(labelKey, prop, value) {
  const field = elem("div", "field");
  field.appendChild(elem("label", null, t(labelKey)));
  const input = elem("input"); input.type = "time"; input.value = value;
  input.addEventListener("change", () => { State.theme[prop] = input.value; persistTheme(); startThemeEngine(); });
  field.appendChild(input);
  return field;
}

function themeSelectField(labelKey, prop, options, current) {
  const field = elem("div", "field");
  field.appendChild(elem("label", null, t(labelKey)));
  const sel = elem("select");
  options.forEach(([value, label]) => { const opt = elem("option", null, label); opt.value = value; if (String(value) === String(current)) opt.selected = true; sel.appendChild(opt); });
  sel.addEventListener("change", () => { State.theme[prop] = Number(sel.value); persistTheme(); startThemeEngine(); });
  field.appendChild(sel);
  return field;
}

function renderSettingsPaths(panel) {
  const s = State.settings;
  panel.appendChild(buildRootCard(t("settings.roots.library", "Library roots"), "library", (s.libraryRoots || []).map((p) => ({ path: p }))));
  panel.appendChild(buildRootCard(t("settings.roots.comic", "Comic roots"), "comic", (s.comicRoots || []).map((p) => ({ path: p }))));
  panel.appendChild(buildRootCard(t("settings.roots.text", "Text novel roots"), "text", (s.textRoots || []).map((r) => ({ path: r.path || r })), true));
}

function buildRootCard(title, kind, roots, withRules) {
  const card = settingCard(title);
  const add = elem("button", "ghost-btn path-add-btn", t("settings.roots.add", "Add folder"));
  add.addEventListener("click", () => State.bridge.addRoot(kind));
  card.appendChild(add);
  const list = elem("div", "path-list");
  roots.forEach((root) => {
    const row = elem("div", "path-row");
    const del = elem("button", "danger-btn", t("settings.roots.delete", "Delete"));
    del.addEventListener("click", () => confirmRemoveRoot(kind, root.path));
    row.appendChild(del);
    if (withRules) {
      const rules = elem("button", "ghost-btn", t("settings.roots.rules", "Rules"));
      rules.title = t("settings.roots.rules_hint", "Opens the native Text Rules editor for this folder");
      rules.addEventListener("click", () => State.bridge.openTextRules(root.path));
      row.appendChild(rules);
    }
    row.appendChild(elem("span", "path-text", root.path));
    list.appendChild(row);
  });
  card.appendChild(list);
  return card;
}

function confirmRemoveRoot(kind, path) {
  openModal((modal, close) => {
    modalHeader(modal, t("settings.delete_confirm_title", "Confirm Delete"), close);
    modal.appendChild(elem("p", "small-note", fmt(
      t("settings.delete_confirm_text", "Remove this folder from the library?\n{path}\nBooks under it will be removed from the database (files on disk are not deleted)."),
      { path }
    )));
    const actions = elem("div", "modal-actions");
    const cancel = elem("button", "ghost-btn", t("common.cancel", "Cancel"));
    cancel.addEventListener("click", close);
    const confirm = elem("button", "danger-btn", t("settings.roots.delete", "Delete"));
    confirm.addEventListener("click", () => {
      State.bridge.removeRoot(kind, path);
      close();
    });
    actions.appendChild(cancel);
    actions.appendChild(confirm);
    modal.appendChild(actions);
  });
}

function formatScanSummary(report) {
  if (!report || typeof report !== "object") return "";
  let text = fmt(t("settings.scan_summary_template", "Last scan: {updated_at}\nScope: {scope} | Added: {added} | Ignored unsupported: {ignored} | Name conflicts: {conflicts}\nRemoved missing: {removed_total} (library/text: {removed_books}, comic: {removed_comics})"), {
    updated_at: report.updated_at || report.finished_at || "—",
    scope: report.scope || report.trigger || "—",
    added: Number(report.added_count || 0) + Number(report.text_added_count || 0),
    ignored: report.ignored_unsupported_count || 0,
    conflicts: Array.isArray(report.name_conflicts) ? report.name_conflicts.length : (report.name_conflict_count || 0),
    removed_total: report.removed_missing_count || 0,
    removed_books: report.removed_missing_book_count || 0,
    removed_comics: report.removed_missing_comic_count || 0,
  });
  text += fmt(t("settings.text.scan_summary", "\nText Novel - scanned:{scanned} added:{added} updated:{updated}"), {
    scanned: report.text_scanned_count || 0,
    added: report.text_added_count || 0,
    updated: report.text_updated_count || 0,
  });
  text += fmt(t("settings.comic.scan_perf_summary", "\nComic - placeholders:{copied} thumbs queued:{queued} workers:{workers} downscaled:{downscaled}"), {
    copied: report.comic_placeholder_copied_count || 0,
    queued: report.comic_thumbnail_enqueued_count || 0,
    workers: report.comic_thumbnail_workers_used || "—",
    downscaled: report.comic_thumbnail_downscaled_count || 0,
  });
  return text;
}

function renderSettingsTasks(panel) {
  const s = State.settings;
  const card = settingCard(t("settings.nav.tasks", "Scan & Tasks"));
  const progressWrap = elem("div", "settings-card");
  const bar = elem("div", "progress");
  const span = elem("span"); span.id = "scanProgressBar";
  bar.appendChild(span);
  progressWrap.appendChild(bar);
  const label = elem("p", "small-note"); label.id = "scanProgressLabel";
  progressWrap.appendChild(label);
  const scanRow = elem("div", "detail-actions");
  [["library","settings.tasks.scan_library"],["comic","settings.tasks.scan_comic"],["text","settings.tasks.scan_text"]].forEach(([scope, key]) => {
    const btn = elem("button", "primary-btn", t(key));
    btn.addEventListener("click", () => State.bridge.startScan(scope));
    scanRow.appendChild(btn);
  });
  card.appendChild(scanRow);

  const thumbRow = elem("div", "detail-actions");
  [["cleanup","library","settings.tasks.cleanup_library"],["regenerate","library","settings.tasks.regen_library"],
   ["cleanup","comic","settings.tasks.cleanup_comic"],["regenerate","comic","settings.tasks.regen_comic"]].forEach(([kind, scope, key]) => {
    const btn = elem("button", "ghost-btn", t(key));
    btn.addEventListener("click", () => State.bridge.startThumbnailTask(kind, scope));
    thumbRow.appendChild(btn);
  });
  card.appendChild(thumbRow);

  const fonts = elem("button", "ghost-btn", t("settings.tasks.reload_fonts", "Reload Fonts"));
  fonts.addEventListener("click", () => State.bridge.reloadFonts());
  card.appendChild(fonts);

  const summaryCard = settingCard(t("settings.scan_summary_title", "Last scan summary"));
  const summaryBox = elem("pre", "log-box");
  summaryBox.id = "scanSummaryBox";
  summaryBox.textContent = formatScanSummary(s.scanReport) || "—";
  summaryCard.appendChild(summaryBox);

  panel.appendChild(card);
  panel.appendChild(progressWrap);
  panel.appendChild(summaryCard);
}

function renderSettingsErrors(panel) {
  const card = settingCard(t("settings.nav.errors", "Error logs"));
  const refresh = elem("button", "ghost-btn", t("settings.errors.refresh", "Refresh"));
  refresh.addEventListener("click", () => State.bridge.getErrorLogs((text) => { box.textContent = text; }));
  card.appendChild(refresh);
  const box = elem("pre", "log-box"); box.id = "errorLogBox";
  box.textContent = State.errorLogs || "";
  card.appendChild(box);
  panel.appendChild(card);
}

/* ---------- theme engine ---------- */
function persistTheme() {
  State.bridge.setThemeSettings(JSON.stringify(State.theme));
}

function applyThemeConfig(theme) {
  if (theme) State.theme = Object.assign(State.theme, theme);
}

function parseTimeToMinutes(value, fallback) {
  const m = String(value || "").match(/^(\d{1,2}):(\d{2})$/);
  if (!m) return fallback;
  return Math.max(0, Math.min(23, +m[1])) * 60 + Math.max(0, Math.min(59, +m[2]));
}

function isNightNow(start, end, now) {
  if (start === end) return false;
  if (start < end) return now >= start && now < end;
  return now >= start || now < end;
}

function computedTheme() {
  const start = parseTimeToMinutes(State.theme.nightStart, 22 * 60);
  const end = parseTimeToMinutes(State.theme.dayResume, 7 * 60);
  const d = new Date();
  return isNightNow(start, end, d.getHours() * 60 + d.getMinutes()) ? "night" : "day";
}

function applyTheme(theme, transitionMs) {
  document.documentElement.style.setProperty("--active-theme-transition-duration", transitionMs + "ms");
  document.body.dataset.theme = theme === "night" ? "night" : "day";
  // Keep Qt WebEngine clear color in sync (avoids white flash on window activate).
  try {
    if (State.bridge && State.bridge.setPageBackgroundTheme) {
      State.bridge.setPageBackgroundTheme(theme === "night" ? "night" : "day");
    }
  } catch (e) {}
}

function setThemeMode(mode) {
  State.theme.mode = (mode === "day" || mode === "night") ? mode : "auto";
  if (State.theme.mode === "auto") { State.theme.autoEnabled = true; applyTheme(computedTheme(), 420); }
  else applyTheme(State.theme.mode, 420);
  persistTheme();
  startThemeEngine();
}

function startThemeEngine() {
  if (State.themeTimer) { clearInterval(State.themeTimer); State.themeTimer = null; }
  const mode = State.theme.mode || "auto";
  if (mode === "auto") applyTheme(computedTheme(), 420);
  else applyTheme(mode, 420);
  if (mode === "auto" && State.theme.autoEnabled) {
    const freq = Math.max(1, Number(State.theme.checkFrequency) || 5);
    State.themeTimer = setInterval(() => {
      applyTheme(computedTheme(), Math.max(1, Number(State.theme.transitionMinutes) || 3) * 60000);
    }, freq * 60000);
  }
}

/* ---------- top bar interactions ---------- */
function initTopbar() {
  const input = $("searchInput");
  let debounce = null;
  input.addEventListener("input", () => {
    if (State.currentPage === "settings") return;
    State.searchQuery = input.value;
    if (debounce) clearTimeout(debounce);
    debounce = setTimeout(commitSearch, 160);
    updateSuggestions();
  });
  input.addEventListener("focus", updateSuggestions);
  document.addEventListener("click", (e) => {
    if (!$("suggestions").contains(e.target) && e.target !== input) closeSuggestions();
  });
  $("scanBtn").addEventListener("click", () => State.bridge.startScan("all"));
  $("settingsBtn").addEventListener("click", () => selectPage("settings"));
  const importBtn = $("importBtn");
  if (importBtn) {
    importBtn.addEventListener("click", () => State.bridge.addRoot("library"));
  }
  document.querySelectorAll("#viewModeToggle button").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#viewModeToggle button").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      State.viewMode = btn.dataset.mode;
      if (State.currentPage !== "settings") scheduleRenderPage();
    });
  });
}

function searchContext() { return State.currentPage === "text_novel" ? "text_novel" : "library"; }

function commitSearch() {
  const ctx = searchContext();
  State.bridge.search(ctx, State.searchQuery, (json) => {
    const data = safeParse(json);
    if (!data) return;
    State.pages[ctx] = data;
    if (State.currentPage === ctx) scheduleRenderPage();
  });
}

function updateSuggestions() {
  const query = $("searchInput").value;
  if (State.currentPage === "settings" || COMIC_PAGES.has(State.currentPage) || State.currentPage === "collections") { closeSuggestions(); return; }
  State.bridge.getSuggestions(searchContext(), query, (json) => {
    const items = safeParse(json) || [];
    const box = $("suggestions");
    clear(box);
    if (!items.length) { closeSuggestions(); return; }
    items.forEach((s) => {
      const row = elem("div", "suggestion-row");
      row.appendChild(elem("span", "suggestion-kind", s.group));
      row.appendChild(elem("span", "suggestion-text", s.label + (s.description ? " — " + s.description : "")));
      row.addEventListener("click", () => {
        $("searchInput").value = s.query_value;
        State.searchQuery = s.query_value;
        commitSearch();
        closeSuggestions();
      });
      box.appendChild(row);
    });
    box.classList.add("open");
  });
}

function closeSuggestions() { $("suggestions").classList.remove("open"); }

/* ---------- boot ---------- */
document.addEventListener("DOMContentLoaded", () => {
  initTopbar();
  initChannel();
});
