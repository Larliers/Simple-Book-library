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
  searchQueries: { library: "", text_novel: "", comic: "", comic_collections: "" },
  suggestOpen: false,
  theme: { mode: "auto", autoEnabled: true, nightStart: "22:00", dayResume: "07:00", checkFrequency: 5, transitionMinutes: 3 },
  themeTimer: null,
  uiSkin: "glass",
  renderGen: 0,
  renderTimer: null,
  scrollPos: {},
  comicPageNum: { comic: 1, comic_collections: 1 },
  recommendations: null,
  recommendationsLoading: false,
  recommendationRequestId: 0,
  recommendationSelection: null,
  tagCatalog: null,
  tagDetail: null,
  tagLoading: false,
  tagRequestId: 0,
  tagOrder: "asc",
  tagSelection: null,
  resourceSelection: {
    scopeKey: "",
    order: [],
    selectedKeys: new Set(),
    anchorKey: "",
    focusKey: "",
  },
  recentTag: null,
  recentCollections: { collections: null, novel_collections: null, comic_collections: null },
  shortcutCaptureAction: "",
  _scanRunning: false,
  _taskKind: "scan",
};

const COLLECTION_PAGES = new Set(["collections", "novel_collections", "comic_collections"]);
const COMIC_PAGES = new Set(["comic", "comic_collections"]);
const SEARCH_PAGES = new Set(["library", "text_novel", "comic", "comic_collections"]);
const RANDOM_RECOMMENDATIONS_PAGE = "random_recommendations";
const TAG_MANAGER_PAGE = "tag_manager";
const SHORTCUT_MOUSE_TOKENS = new Set(["MouseBack", "MouseForward"]);
const SHORTCUT_MODIFIERS = ["Ctrl", "Alt", "Shift", "Meta"];
const SHORTCUT_SPECIAL_KEY_CODES = new Set([
  "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight",
  "Home", "End", "PageUp", "PageDown", "Insert", "Delete", "Backspace",
  "Backquote", "Minus", "Equal", "BracketLeft", "BracketRight", "Backslash",
  "Semicolon", "Quote", "Comma", "Period", "Slash",
  "NumpadAdd", "NumpadSubtract", "NumpadMultiply", "NumpadDivide", "NumpadDecimal",
]);
const RESERVED_SHORTCUT_TOKENS = new Set([
  "F5", "Ctrl+KeyR", "Ctrl+KeyW", "Ctrl+KeyQ",
  "Ctrl+Equal", "Ctrl+Shift+Equal", "Ctrl+Minus", "Ctrl+Digit0", "Ctrl+Numpad0",
  "Ctrl+NumpadAdd", "Ctrl+NumpadSubtract", "Alt+F4",
]);

function resourceSelectionKey(ref) {
  return `${String(ref && ref.sourcePage || "")}\u0000${String(ref && ref.id || "")}`;
}

function resourceSelectionScopeKey(page, data) {
  const payload = data || {};
  const parts = [String(page || ""), String(payload.mode || "")];
  if (payload.collectionId) parts.push(`collection:${payload.collectionId}`);
  if (payload.mode === "tag_detail") parts.push(`tag:${String(payload.tag || "")}`);
  if (payload.sort) parts.push(`sort:${String(payload.sort)}`);
  if (page === "comic" || page === "comic_collections") {
    parts.push(`comic-page:${Number(State.comicPageNum[page] || 1)}`);
  }
  if (State.searchQueries && Object.prototype.hasOwnProperty.call(State.searchQueries, page)) {
    parts.push(`query:${String(State.searchQueries[page] || "")}`);
  }
  return parts.join("|");
}

function clearResourceSelection() {
  State.resourceSelection.selectedKeys = new Set();
  State.resourceSelection.anchorKey = "";
  State.resourceSelection.focusKey = "";
  State.tagSelection = null;
  if (State.currentPage) delete State.selected[State.currentPage];
}

function configureResourceSelection(page, data, refs) {
  const order = (Array.isArray(refs) ? refs : [])
    .map((ref) => ({ sourcePage: String(ref.sourcePage || ""), id: String(ref.id || "") }))
    .filter((ref) => ref.sourcePage && ref.id);
  const scopeKey = resourceSelectionScopeKey(page, data);
  if (State.resourceSelection.scopeKey !== scopeKey) {
    clearResourceSelection();
    State.resourceSelection.scopeKey = scopeKey;
  }
  State.resourceSelection.order = order;
  const availableKeys = new Set(order.map(resourceSelectionKey));
  State.resourceSelection.selectedKeys = new Set(
    [...State.resourceSelection.selectedKeys].filter((key) => availableKeys.has(key))
  );
  if (!availableKeys.has(State.resourceSelection.anchorKey)) State.resourceSelection.anchorKey = "";
  if (!availableKeys.has(State.resourceSelection.focusKey)) State.resourceSelection.focusKey = "";
  return selectedResourceRefs();
}

function selectedResourceRefs() {
  return State.resourceSelection.order.filter((ref) => (
    State.resourceSelection.selectedKeys.has(resourceSelectionKey(ref))
  ));
}

function updateResourceSelection(ref, modifiers) {
  const key = resourceSelectionKey(ref);
  const orderedKeys = State.resourceSelection.order.map(resourceSelectionKey);
  const targetIndex = orderedKeys.indexOf(key);
  if (targetIndex < 0) return selectedResourceRefs();
  const event = modifiers || {};
  const ctrl = Boolean(event.ctrlKey || event.metaKey);
  const shift = Boolean(event.shiftKey);
  const selected = new Set(State.resourceSelection.selectedKeys);
  if (shift && State.resourceSelection.anchorKey) {
    const anchorIndex = orderedKeys.indexOf(State.resourceSelection.anchorKey);
    if (anchorIndex >= 0) {
      const start = Math.min(anchorIndex, targetIndex);
      const end = Math.max(anchorIndex, targetIndex);
      if (!ctrl) selected.clear();
      orderedKeys.slice(start, end + 1).forEach((itemKey) => selected.add(itemKey));
    }
  } else if (ctrl) {
    if (selected.has(key)) selected.delete(key);
    else selected.add(key);
    State.resourceSelection.anchorKey = key;
  } else {
    selected.clear();
    selected.add(key);
    State.resourceSelection.anchorKey = key;
  }
  if (!shift && !State.resourceSelection.anchorKey) State.resourceSelection.anchorKey = key;
  State.resourceSelection.focusKey = key;
  State.resourceSelection.selectedKeys = selected;
  return selectedResourceRefs();
}

function selectAllResourcesInScope() {
  State.resourceSelection.selectedKeys = new Set(
    State.resourceSelection.order.map(resourceSelectionKey)
  );
  if (!State.resourceSelection.anchorKey && State.resourceSelection.order.length) {
    State.resourceSelection.anchorKey = resourceSelectionKey(State.resourceSelection.order[0]);
  }
  if (State.resourceSelection.order.length) {
    State.resourceSelection.focusKey = resourceSelectionKey(
      State.resourceSelection.order[State.resourceSelection.order.length - 1]
    );
  }
  return selectedResourceRefs();
}

function isShortcutKeyCode(code) {
  return /^(Key[A-Z]|Digit[0-9]|Numpad[0-9]|F(?:[1-9]|1[0-9]|2[0-4]))$/.test(code)
    || SHORTCUT_SPECIAL_KEY_CODES.has(code);
}

function isBindableShortcutToken(inputToken) {
  const token = String(inputToken || "");
  if (SHORTCUT_MOUSE_TOKENS.has(token)) return true;
  if (!token || RESERVED_SHORTCUT_TOKENS.has(token)) return false;
  const parts = token.split("+");
  const code = parts.pop();
  const modifiers = parts;
  const expectedModifiers = SHORTCUT_MODIFIERS.filter((name) => modifiers.includes(name));
  return modifiers.join("+") === expectedModifiers.join("+") && isShortcutKeyCode(code || "");
}

function shortcutTokenFromMouseEvent(event) {
  const button = Number(event && event.button);
  if (button === 3) return "MouseBack";
  if (button === 4) return "MouseForward";
  const which = Number(event && event.which);
  if (which === 4) return "MouseBack";
  if (which === 5) return "MouseForward";
  const buttons = Number(event && event.buttons);
  if (buttons & 8) return "MouseBack";
  if (buttons & 16) return "MouseForward";
  return "";
}

function shortcutTokenFromKeyboardEvent(event) {
  const code = String(event && event.code || "");
  const key = String(event && event.key || "");
  const keyCode = Number(event && (event.keyCode || event.which));
  if (code === "BrowserBack" || key === "BrowserBack" || keyCode === 166) return "MouseBack";
  if (code === "BrowserForward" || key === "BrowserForward" || keyCode === 167) return "MouseForward";
  if (!isShortcutKeyCode(code)) return "";
  const modifiers = [];
  if (event.ctrlKey) modifiers.push("Ctrl");
  if (event.altKey) modifiers.push("Alt");
  if (event.shiftKey) modifiers.push("Shift");
  if (event.metaKey) modifiers.push("Meta");
  const token = [...modifiers, code].join("+");
  return isBindableShortcutToken(token) ? token : "";
}

function isComicCollectionDetail(data) {
  const d = data || currentPageData();
  return Boolean(d && d.mode === "comic" && d.collectionId);
}

function isNovelCollectionDetail(page, data) {
  const d = data || currentPageData();
  return page === "novel_collections" && Boolean(d && d.mode === "collection_detail" && d.collectionId);
}

function isLibraryCollectionDetail(page, data) {
  const d = data || currentPageData();
  return page === "collections" && Boolean(d && d.mode === "collection_detail" && d.collectionId);
}

const BOOK_FIELD_SORT_OPTIONS = [
  ["file_mtime_desc", "text_novel.sort.file_mtime_desc", "File Date: Newest First"],
  ["file_mtime_asc", "text_novel.sort.file_mtime_asc", "File Date: Oldest First"],
  ["title_asc", "text_novel.sort.title_asc", "Title: A-Z"],
  ["title_desc", "text_novel.sort.title_desc", "Title: Z-A"],
  ["author_asc", "text_novel.sort.author_asc", "Author: A-Z"],
  ["author_desc", "text_novel.sort.author_desc", "Author: Z-A"],
  ["tags_asc", "text_novel.sort.tags_asc", "Tags: A-Z"],
  ["tags_desc", "text_novel.sort.tags_desc", "Tags: Z-A"],
  ["path_asc", "text_novel.sort.path_asc", "Path: A-Z"],
  ["path_desc", "text_novel.sort.path_desc", "Path: Z-A"],
];

const BOOK_COLLECTION_SORT_OPTIONS = [
  ["added_desc", "favorites.sort.added_desc", "Added Time: Newest First"],
  ["added_asc", "favorites.sort.added_asc", "Added Time: Oldest First"],
  ...BOOK_FIELD_SORT_OPTIONS,
];

function setBookPageSort(page, order) {
  if (!State.bridge || !State.bridge.setPageSort) return;
  clearResourceSelection();
  renderDetailEmpty();
  State.bridge.setPageSort(page, order, (json) => {
    const data = safeParse(json);
    if (!data) return;
    State.pages[page] = data;
    clearPageScroll(page);
    scheduleRenderPage();
  });
}

function isSearchablePage(page) {
  if (page === "library" || page === "text_novel" || page === "comic") return true;
  if (page === "comic_collections") return isComicCollectionDetail(State.pages[page] || {});
  return false;
}

function normalizeViewMode(value) {
  return String(value || "").toLowerCase() === "list" ? "list" : "grid";
}

function viewModeForPage(page) {
  if (page === "text_novel") return normalizeViewMode(State.settings.textNovelViewMode);
  return normalizeViewMode(State.viewMode);
}

function syncViewModeToggle(page) {
  const activeMode = viewModeForPage(page);
  document.querySelectorAll("#viewModeToggle button").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === activeMode);
  });
}

function setViewModeForPage(page, value) {
  const mode = normalizeViewMode(value);
  if (page === "text_novel") {
    State.settings.textNovelViewMode = mode;
    if (State.bridge && State.bridge.setSetting) State.bridge.setSetting("textNovelViewMode", mode);
  } else {
    State.viewMode = mode;
  }
  syncViewModeToggle(page);
  if (State.currentPage !== "settings") scheduleRenderPage();
}

function applyCollectionPageData(json) {
  const d = typeof json === "string" || json == null ? safeParse(json) : json;
  const page = COLLECTION_PAGES.has(State.currentPage) ? State.currentPage : "collections";
  applyCollectionDataForPage(page, d);
}

function applyCollectionDataForPage(page, data) {
  const d = typeof data === "string" || data == null ? safeParse(data) : data;
  if (d) {
    if (State.currentPage === page) {
      clearResourceSelection();
      renderDetailEmpty();
    }
    State.pages[page] = d;
    if (State.currentPage === page) scheduleRenderPage();
  }
}

function isCollectionDetailData(data) {
  return Boolean(data && data.collectionId && (data.mode === "collection_detail" || data.mode === "comic"));
}

function rememberRecentCollection(page, data) {
  if (!COLLECTION_PAGES.has(page) || !isCollectionDetailData(data)) return;
  State.recentCollections[page] = {
    collectionId: Number(data.collectionId),
    collectionName: String(data.collectionName || ""),
  };
}

function forgetRecentCollection(page, collectionId) {
  const recent = State.recentCollections[page];
  if (recent && Number(recent.collectionId) === Number(collectionId)) {
    State.recentCollections[page] = null;
  }
}

function openCollectionWithHistory(page, collectionId, notifyMissing) {
  State.bridge.openCollection(page, Number(collectionId), (json) => {
    const data = safeParse(json);
    if (data && Number(data.collectionId) === Number(collectionId) && isCollectionDetailData(data)) {
      rememberRecentCollection(page, data);
    } else if (notifyMissing) {
      State.recentCollections[page] = null;
      showShortcutNotice("shortcut.recent_missing");
    }
    applyCollectionDataForPage(page, data);
  });
}

function rememberRecentTag(tag) {
  const normalized = String(tag || "").trim();
  if (normalized) State.recentTag = normalized;
}

function exitCurrentTag() {
  const tag = State.tagDetail ? String(State.tagDetail.tag || "").trim() : "";
  if (!tag) {
    showShortcutNotice("shortcut.no_tag_to_exit");
    return false;
  }
  rememberRecentTag(tag);
  closeTagDetail();
  return true;
}

function reopenRecentTag() {
  if (State.tagDetail && String(State.tagDetail.tag || "").trim()) {
    showShortcutNotice("shortcut.already_in_tag");
    return false;
  }
  if (!State.recentTag) {
    showShortcutNotice("shortcut.no_recent_tag");
    return false;
  }
  openTagFromCatalog(State.recentTag);
  return true;
}

function openTagFromCatalog(tag) {
  const normalized = String(tag || "").trim();
  if (!normalized) return;
  rememberRecentTag(normalized);
  if (State.bridge && State.bridge.openTag) State.bridge.openTag(normalized);
  State.tagRequestId += 1;
  State.tagLoading = false;
  loadTagResources(normalized);
}

function exitCurrentCollection() {
  if (State.currentPage === TAG_MANAGER_PAGE) return exitCurrentTag();
  const page = State.currentPage;
  if (!COLLECTION_PAGES.has(page)) {
    showShortcutNotice("shortcut.not_collection_page");
    return false;
  }
  const data = State.pages[page] || {};
  if (!isCollectionDetailData(data)) {
    showShortcutNotice("shortcut.no_collection_to_exit");
    return false;
  }
  rememberRecentCollection(page, data);
  State.bridge.closeCollection(page, (json) => applyCollectionDataForPage(page, json));
  renderDetailEmpty();
  return true;
}

function reopenRecentCollection() {
  if (State.currentPage === TAG_MANAGER_PAGE) return reopenRecentTag();
  const page = State.currentPage;
  if (!COLLECTION_PAGES.has(page)) {
    showShortcutNotice("shortcut.not_collection_page");
    return false;
  }
  const data = State.pages[page] || {};
  if (isCollectionDetailData(data)) {
    showShortcutNotice("shortcut.already_in_collection");
    return false;
  }
  const recent = State.recentCollections[page];
  if (!recent) {
    showShortcutNotice("shortcut.no_recent_collection");
    return false;
  }
  openCollectionWithHistory(page, recent.collectionId, true);
  renderDetailEmpty();
  return true;
}

function searchPlaceholderForPage(page) {
  if (page === RANDOM_RECOMMENDATIONS_PAGE) return t("topbar.search_recommendations_placeholder", "Search is unavailable on recommendations.");
  if (page === TAG_MANAGER_PAGE) return t("topbar.search_tags_placeholder", "Search is unavailable in tag manager.");
  if (page === "text_novel") return t("topbar.search_text_placeholder");
  if (page === "comic" || (page === "comic_collections" && isComicCollectionDetail(State.pages[page] || {}))) {
    return t("topbar.search_comic_placeholder");
  }
  return t("topbar.search_placeholder");
}

function syncSearchInputFromPage(page) {
  const input = $("searchInput");
  if (page === RANDOM_RECOMMENDATIONS_PAGE || page === TAG_MANAGER_PAGE) {
    State.searchQuery = "";
    input.value = "";
    input.disabled = true;
    input.setAttribute("placeholder", searchPlaceholderForPage(page));
    closeSuggestions();
    return;
  }
  input.disabled = false;
  if (!isSearchablePage(page)) {
    input.setAttribute("placeholder", searchPlaceholderForPage(page));
    return;
  }
  const query = State.searchQueries[page] || "";
  State.searchQuery = query;
  input.value = query;
  input.setAttribute("placeholder", searchPlaceholderForPage(page));
}

function saveSearchQueryForPage(page, query) {
  if (!isSearchablePage(page)) return;
  State.searchQueries[page] = query;
  State.searchQuery = query;
}

const SKIN_STYLESHEETS = {
  glass: [
    "app://app/css/base.css",
    "app://app/css/skins/glass/tokens.css",
    "app://app/css/skins/glass/components.css",
  ],
  vaporwave: [
    "app://app/css/base.css",
    "app://app/css/skins/vaporwave/fonts.css",
    "app://app/css/skins/vaporwave/tokens.css",
    "app://app/css/skins/vaporwave/background.css",
    "app://app/css/skins/vaporwave/layout.css",
    "app://app/css/skins/vaporwave/components.css",
  ],
};

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
      const hadBatchSelection = selectedResourceRefs().length > 0;
      clearResourceSelection();
      const selectionCleared = clearInvalidCurrentSelectionAfterResourceChange() || hadBatchSelection;
      if (selectionCleared) renderDetailEmpty();
      if (data.recommendationsInvalidated) {
        invalidateRandomRecommendations(true);
      }
      if (data.tagCatalogInvalidated) {
        invalidateTagManager(true);
      }
      if (State.currentPage === RANDOM_RECOMMENDATIONS_PAGE) {
        if (data.recommendationsInvalidated) {
          renderDetailEmpty();
          loadRandomRecommendations();
        } else {
          scheduleRenderPage();
          if (!selectionCleared) refreshDetailIfSelected();
        }
      } else if (State.currentPage === TAG_MANAGER_PAGE) {
        if (data.tagCatalogInvalidated) loadCurrentTagPage();
        else scheduleRenderPage();
      } else if (State.currentPage !== "settings") {
        scheduleRenderPage();
        if (!selectionCleared) refreshDetailIfSelected();
      }
    }
  });
  b.toast.connect((json) => { const d = safeParse(json); if (d) showToast(d.title, d.message, d.kind); });
  b.scanProgress.connect((json) => { const d = safeParse(json); if (d) updateScanProgress(d); });
  b.scanState.connect((json) => { const d = safeParse(json); if (d) updateScanState(d); });
  b.settingsChanged.connect((json) => {
    const d = safeParse(json);
    if (!d) return;
    const previousItemCount = getRecommendationItemsPerCategory(State.settings);
    const previousColumnCount = getRecommendationColumnsPerCategory(State.settings);
    const previousTagScopes = JSON.stringify((State.settings || {}).tagManagerScopes || {});
    State.settings = d;
    const itemCountChanged = previousItemCount !== getRecommendationItemsPerCategory(d);
    const columnCountChanged = previousColumnCount !== getRecommendationColumnsPerCategory(d);
    if (itemCountChanged) {
      invalidateRandomRecommendations();
      if (State.currentPage === RANDOM_RECOMMENDATIONS_PAGE) {
        renderDetailEmpty();
        loadRandomRecommendations();
      }
    }
    else if (columnCountChanged && State.currentPage === RANDOM_RECOMMENDATIONS_PAGE) scheduleRenderPage();
    if (previousTagScopes !== JSON.stringify(d.tagManagerScopes || {})) {
      invalidateTagManager(true);
      if (State.currentPage === TAG_MANAGER_PAGE) loadCurrentTagPage();
    }
    if (d.theme) applyThemeConfig(d.theme);
    if (d.uiSkin) State.uiSkin = normalizeUiSkin(d.uiSkin);
    if (State.currentPage === "settings") renderSettings();
  });
  b.errorLogsChanged.connect((text) => { const box = document.getElementById("errorLogBox"); if (box) box.textContent = text; });
  if (b.updateCheckResult && b.updateCheckResult.connect) {
    b.updateCheckResult.connect((json) => {
      const d = safeParse(json);
      if (!d) return;
      resetUpdateCheckButton();
      if (d.status === "update_available") openUpdateModal(d);
      else if (d.status === "up_to_date") {
        showToast(
          t("settings.about.up_to_date", "Up to date"),
          t("settings.about.up_to_date_msg", "You are running the latest release."),
          "info"
        );
      } else {
        showToast(
          t("settings.about.error", "Update check failed"),
          d.message || t("settings.about.error", "Update check failed"),
          "warning"
        );
      }
    });
  }
  if (b.nativeShortcutInput && b.nativeShortcutInput.connect) {
    b.nativeShortcutInput.connect(handleNativeShortcutInput);
  }
  if (typeof wireTextRulesSignal === "function") wireTextRulesSignal(b);
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
    if (State.settings.uiSkin) State.uiSkin = State.settings.uiSkin;
    applyUiSkin(State.uiSkin);
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

function savePageScroll(page) {
  if (!page || page === "settings") return;
  const area = $("contentArea");
  if (!area) return;
  State.scrollPos[page] = area.scrollTop;
  if (COMIC_PAGES.has(page) && State._comicPage) {
    State.comicPageNum[page] = State._comicPage;
  }
}

function clearPageScroll(page) {
  State.scrollPos[page] = 0;
}

function selectPage(page) {
  // Same-page nav click: avoid wiping/rebuilding hundreds of cards.
  if (page === State.currentPage && page !== "settings") return;
  savePageScroll(State.currentPage);
  clearResourceSelection();
  State.resourceSelection.scopeKey = "";
  State.resourceSelection.order = [];
  if (page !== "settings") State.shortcutCaptureAction = "";
  State.currentPage = page;
  document.body.dataset.page = page;
  syncViewModeToggle(page);
  document.querySelectorAll(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.page === page));
  $("settingsBtn").classList.toggle("active", page === "settings");
  const detail = $("detailPanel");
  if (page === "settings") {
    // Invalidate in-flight comic scroll appenders / rAF grids.
    State.renderGen += 1;
    detail.classList.add("hidden");
    renderSettings();
    return;
  }
  detail.classList.remove("hidden");
  syncSearchInputFromPage(page);
  if (page === RANDOM_RECOMMENDATIONS_PAGE && !State.recommendations) {
    loadRandomRecommendations();
  } else if (page === TAG_MANAGER_PAGE) {
    if (State.tagDetail) scheduleRenderPage();
    else loadTagCatalog();
  } else if (isSearchablePage(page) && (State.searchQueries[page] || "").trim()) {
    commitSearch();
  } else {
    scheduleRenderPage();
  }
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
function currentPageData() {
  if (State.currentPage === RANDOM_RECOMMENDATIONS_PAGE && State.recommendations) return State.recommendations;
  if (State.currentPage === TAG_MANAGER_PAGE) {
    return State.tagDetail || State.tagCatalog || { mode: "tag_index", order: State.tagOrder, tagCount: 0, groups: [] };
  }
  return State.pages[State.currentPage] || { items: [], mode: "grid_or_list" };
}

function pageItemCount(data) {
  if (data && data.mode === "recommendations") {
    return (data.columns || []).reduce((total, column) => total + (column.items || []).length, 0);
  }
  if (data && data.mode === "tag_index") return Number(data.tagCount || 0);
  return (data.items || []).length;
}

function renderPage(expectedGen) {
  const gen = expectedGen != null ? expectedGen : State.renderGen;
  const page = State.currentPage;
  const data = currentPageData();
  document.body.dataset.pageMode = String(data.mode || "");
  const titleItem = State.nav.find((n) => n.page === page);
  $("pageTitle").textContent = data.mode === "tag_detail" && data.tag
    ? data.tag
    : ((data.mode === "collection_detail" && data.collectionName) ? data.collectionName : (titleItem ? titleItem.label : page));
  const count = pageItemCount(data);
  $("pageSubtitle").textContent = fmt(
    t(data.mode === "tag_index" ? "tags.count" : "page.count", data.mode === "tag_index" ? "{count} tags" : "{count} items"),
    { count }
  );

  renderPageTools(page, data);

  const area = $("contentArea");
  if (gen !== State.renderGen) return;
  teardownVirtualWindow(area);
  clear(area);
  // Large comic waterfall: skip enter animation — empty+animate looked like full white reload.
  const skipEnter = (page === "comic" || isComicCollectionDetail(data)) && (data.viewMode || "waterfall") !== "pagination" && count > 48;
  area.classList.remove("view-enter", "view-enter-skip");
  if (skipEnter) {
    area.classList.add("view-enter-skip");
  } else {
    void area.offsetWidth;
    area.classList.add("view-enter");
  }

  const showViewToggle = !COMIC_PAGES.has(page)
    && data.mode !== "collections"
    && data.mode !== "recommendations"
    && data.mode !== "tag_index"
    && data.mode !== "tag_detail";
  $("viewModeToggle").style.display = showViewToggle ? "" : "none";

  if (page === RANDOM_RECOMMENDATIONS_PAGE) {
    if (State.recommendationsLoading && !State.recommendations) {
      area.appendChild(buildEmpty(t("recommendations.loading", "Loading recommendations...")));
    } else {
      renderRecommendations(area, data);
    }
    return;
  }

  if (page === TAG_MANAGER_PAGE) {
    if (State.tagLoading && !State.tagCatalog && !State.tagDetail) {
      area.appendChild(buildEmpty(t("tags.loading", "Loading tags...")));
    } else if (data.mode === "tag_detail") {
      renderTagDetail(area, data, gen);
    } else {
      renderTagCatalog(area, data);
    }
    return;
  }

  if (!count) {
    area.appendChild(buildEmpty(t("empty.default", "Nothing here yet.")));
    return;
  }

  if (page === "text_novel") {
    if (viewModeForPage(page) === "list") renderTable(area, data.items, page, data.sort);
    else renderTextNovelGrid(area, data.items, page, gen);
    return;
  }
  if (data.mode === "collections") { renderCollections(area, data.items); return; }
  if (page === "comic" || data.mode === "comic") { renderComic(area, data, gen); return; }
  if (viewModeForPage(page) === "list") {
    renderTable(area, data.items, page, data.sort || "");
    return;
  }
  renderGrid(area, data.items, page, data.mode === "collection_detail", gen);
}

function renderPageTools(page, data) {
  const tools = $("pageHeadTools");
  clear(tools);
  if (page === RANDOM_RECOMMENDATIONS_PAGE) {
    const refresh = elem("button", "primary-btn", t("recommendations.refresh", "Recommend Again"));
    refresh.disabled = State.recommendationsLoading;
    refresh.addEventListener("click", () => loadRandomRecommendations(true));
    tools.appendChild(refresh);
    return;
  }
  if (page === TAG_MANAGER_PAGE) {
    if (data.mode === "tag_detail") {
      const back = elem("button", "ghost-btn", t("common.back", "Back"));
      back.addEventListener("click", () => executeAction("exit_collection", null));
      tools.appendChild(back);
    } else {
      const wrap = elem("div", "page-sort");
      wrap.appendChild(elem("span", "small-note", t("tags.sort.label", "Tag order")));
      const sel = elem("select", "sort-select");
      [["asc", "tags.sort.asc", "A-Z"], ["desc", "tags.sort.desc", "Z-A"]].forEach(([value, key, fallback]) => {
        const option = elem("option", null, t(key, fallback));
        option.value = value;
        option.selected = State.tagOrder === value;
        sel.appendChild(option);
      });
      sel.addEventListener("change", () => setTagOrder(sel.value));
      wrap.appendChild(sel);
      tools.appendChild(wrap);
    }
    return;
  }
  const inCollectionDetail = data.mode === "collection_detail" || isComicCollectionDetail(data);
  if (inCollectionDetail) {
    const back = elem("button", "ghost-btn", t("common.back", "Back"));
    back.addEventListener("click", () => executeAction("exit_collection", null));
    tools.appendChild(back);
    if (data.mode !== "comic" && !isNovelCollectionDetail(page, data) && !isLibraryCollectionDetail(page, data)) return;
  }
  if (data.mode === "collections") {
    const add = elem("button", "primary-btn", t("common.new_list", "New List"));
    add.addEventListener("click", openNewCollectionModal);
    tools.appendChild(add);
    return;
  }
  if (page === "comic" || isComicCollectionDetail(data)) {
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
      clearResourceSelection();
      renderDetailEmpty();
      State.bridge.setPageSort(page, sel.value, (json) => {
        const d = safeParse(json);
        if (d) { State.pages[page] = d; State.comicPageNum[page] = 1; State._comicPage = 1; clearPageScroll(page); scheduleRenderPage(); }
      });
    });
    wrap.appendChild(sel);
    tools.appendChild(wrap);
  }
  if (page === "text_novel" || isNovelCollectionDetail(page, data)) {
    const wrap = elem("div", "page-sort");
    wrap.appendChild(elem("span", "small-note", t("text_novel.sort.label", "Sort")));
    const sel = elem("select", "sort-select");
    BOOK_FIELD_SORT_OPTIONS.forEach(([value, key, fb]) => {
      const opt = elem("option", null, t(key, fb));
      opt.value = value;
      if ((data.sort || "file_mtime_desc") === value) opt.selected = true;
      sel.appendChild(opt);
    });
    sel.addEventListener("change", () => setBookPageSort(page, sel.value));
    wrap.appendChild(sel);
    tools.appendChild(wrap);
  }
  if (page === "library" || isLibraryCollectionDetail(page, data)) {
    const inBookCollection = isLibraryCollectionDetail(page, data);
    const wrap = elem("div", "page-sort");
    wrap.appendChild(elem("span", "small-note", t("favorites.sort.label", "Sort")));
    const sel = elem("select", "sort-select");
    const options = inBookCollection ? BOOK_COLLECTION_SORT_OPTIONS : BOOK_FIELD_SORT_OPTIONS;
    const defaultOrder = inBookCollection ? "added_desc" : "title_asc";
    options.forEach(([value, key, fb]) => {
      const opt = elem("option", null, t(key, fb));
      opt.value = value;
      if ((data.sort || defaultOrder) === value) opt.selected = true;
      sel.appendChild(opt);
    });
    sel.addEventListener("change", () => setBookPageSort(page, sel.value));
    wrap.appendChild(sel);
    tools.appendChild(wrap);
  }
}

function loadRandomRecommendations(force) {
  if (!State.bridge || State.recommendationsLoading) return;
  if (!force && State.recommendations) {
    if (State.currentPage === RANDOM_RECOMMENDATIONS_PAGE) scheduleRenderPage();
    return;
  }
  State.recommendationsLoading = true;
  const requestId = ++State.recommendationRequestId;
  if (State.currentPage === RANDOM_RECOMMENDATIONS_PAGE) scheduleRenderPage();
  State.bridge.getRandomRecommendations((json) => {
    if (requestId !== State.recommendationRequestId) return;
    State.recommendationsLoading = false;
    const data = safeParse(json);
    State.recommendations = data && data.mode === "recommendations"
      ? data
      : { mode: "recommendations", columns: [] };
    State.recommendationSelection = null;
    if (State.currentPage === RANDOM_RECOMMENDATIONS_PAGE) {
      clearPageScroll(RANDOM_RECOMMENDATIONS_PAGE);
      renderDetailEmpty();
      scheduleRenderPage();
    }
  });
}

function getRecommendationItemsPerCategory(settings) {
  const value = Math.round(Number((settings || State.settings).recommendationItemsPerCategory));
  return new Set([3, 6, 9, 12]).has(value) ? value : 6;
}

function getRecommendationColumnsPerCategory(settings) {
  const value = Math.round(Number((settings || State.settings).recommendationColumnsPerCategory));
  return new Set([1, 2, 3]).has(value) ? value : 2;
}

function invalidateRandomRecommendations(notifyStaleSelection) {
  // Retire any pending callback before requesting against the new source snapshot or item-count setting.
  const selectedResourceBecameStale = Boolean(
    notifyStaleSelection
    && State.currentPage === RANDOM_RECOMMENDATIONS_PAGE
    && State.recommendationSelection
  );
  State.recommendationRequestId += 1;
  State.recommendationsLoading = false;
  State.recommendations = null;
  State.recommendationSelection = null;
  if (selectedResourceBecameStale) showShortcutNotice("shortcut.selection_stale");
}

function invalidateTagManager(preserveDetailTag) {
  const activeTag = preserveDetailTag && State.tagDetail ? String(State.tagDetail.tag || "") : "";
  const selectedBecameStale = Boolean(State.currentPage === TAG_MANAGER_PAGE && State.tagSelection);
  State.tagRequestId += 1;
  State.tagLoading = false;
  State.tagCatalog = null;
  State.tagDetail = activeTag ? { mode: "tag_detail", tag: activeTag, items: [] } : null;
  State.tagSelection = null;
  if (selectedBecameStale) showShortcutNotice("shortcut.selection_stale");
}

function loadCurrentTagPage() {
  if (State.tagDetail && State.tagDetail.tag) loadTagResources(State.tagDetail.tag);
  else loadTagCatalog(true);
}

function loadTagCatalog(force) {
  if (!State.bridge || State.tagLoading) return;
  if (!force && State.tagCatalog && !State.tagDetail) {
    if (State.currentPage === TAG_MANAGER_PAGE) scheduleRenderPage();
    return;
  }
  State.tagLoading = true;
  const requestId = ++State.tagRequestId;
  if (State.currentPage === TAG_MANAGER_PAGE) scheduleRenderPage();
  State.bridge.getTagCatalog(State.tagOrder, (json) => {
    if (requestId !== State.tagRequestId) return;
    State.tagLoading = false;
    const data = safeParse(json);
    State.tagCatalog = data && data.mode === "tag_index"
      ? data
      : { mode: "tag_index", order: State.tagOrder, tagCount: 0, groups: [] };
    State.tagDetail = null;
    State.tagSelection = null;
    if (State.currentPage === TAG_MANAGER_PAGE) {
      clearPageScroll(TAG_MANAGER_PAGE);
      renderDetailEmpty();
      scheduleRenderPage();
    }
  });
}

function loadTagResources(tag) {
  if (!State.bridge || State.tagLoading) return;
  const normalizedTag = String(tag || "").trim();
  if (!normalizedTag) return;
  State.tagLoading = true;
  clearResourceSelection();
  State.tagDetail = { mode: "tag_detail", tag: normalizedTag, items: [] };
  State.tagSelection = null;
  const requestId = ++State.tagRequestId;
  if (State.currentPage === TAG_MANAGER_PAGE) scheduleRenderPage();
  State.bridge.getTagResources(normalizedTag, (json) => {
    if (requestId !== State.tagRequestId) return;
    State.tagLoading = false;
    const data = safeParse(json);
    State.tagDetail = data && data.mode === "tag_detail"
      ? data
      : { mode: "tag_detail", tag: normalizedTag, items: [] };
    State.tagSelection = null;
    if (State.currentPage === TAG_MANAGER_PAGE) {
      clearPageScroll(TAG_MANAGER_PAGE);
      renderDetailEmpty();
      scheduleRenderPage();
    }
  });
}

function closeTagDetail() {
  State.tagRequestId += 1;
  State.tagLoading = false;
  State.tagDetail = null;
  clearResourceSelection();
  State.tagSelection = null;
  clearPageScroll(TAG_MANAGER_PAGE);
  renderDetailEmpty();
  if (State.tagCatalog) scheduleRenderPage();
  else loadTagCatalog(true);
}

function setTagOrder(value) {
  const order = String(value || "").toLowerCase() === "desc" ? "desc" : "asc";
  if (State.tagOrder === order && State.tagCatalog) return;
  State.tagOrder = order;
  invalidateTagManager(false);
  loadTagCatalog(true);
}

function renderTagCatalog(area, data) {
  const groups = Array.isArray(data.groups) ? data.groups : [];
  if (!groups.length) {
    area.appendChild(buildEmpty(t("tags.empty", "No tags in the selected resource types.")));
    return;
  }
  const root = elem("div", "tag-catalog");
  groups.forEach((group) => {
    const section = elem("section", "tag-group");
    const heading = elem("h2", "tag-group-title");
    heading.appendChild(document.createTextNode(String(group.letter || "#")));
    heading.appendChild(elem("span", "tag-group-count", `(${Number(group.tagCount || 0)})`));
    section.appendChild(heading);
    const grid = elem("div", "tag-list");
    (group.items || []).forEach((item) => {
      const button = elem("button", "tag-link");
      button.type = "button";
      button.setAttribute("aria-label", `${item.name} (${Number(item.resourceCount || 0)})`);
      button.appendChild(elem("span", "tag-bullet", "•"));
      button.appendChild(elem("span", "tag-name", item.name || ""));
      button.appendChild(elem("span", "tag-resource-count", `(${Number(item.resourceCount || 0)})`));
      button.addEventListener("click", () => openTagFromCatalog(item.name));
      grid.appendChild(button);
    });
    section.appendChild(grid);
    root.appendChild(section);
  });
  area.appendChild(root);
}

function tagSourceLabel(sourcePage) {
  const keys = {
    library: ["tags.source.library", "Book"],
    text_novel: ["tags.source.text_novel", "Novel"],
    comic: ["tags.source.comic", "Comic"],
  };
  const entry = keys[sourcePage] || ["tags.source.library", "Book"];
  return t(entry[0], entry[1]);
}

function renderTagDetail(area, data, gen) {
  const items = Array.isArray(data.items) ? data.items : [];
  if (!items.length) {
    if (State.tagLoading) area.appendChild(buildEmpty(t("tags.loading", "Loading tags...")));
    else area.appendChild(buildEmpty(t("empty.default", "Nothing here yet.")));
    return;
  }
  prepareResourceSelection(TAG_MANAGER_PAGE, data, items, (item) => ({
    sourcePage: String(item.sourcePage || "library"),
    id: String(item.id || ""),
  }));
  mountVirtualCoverGrid(area, items, TAG_MANAGER_PAGE, true, gen, (item) => {
    const sourcePage = String(item.sourcePage || "library");
    const ref = { sourcePage, id: String(item.id || "") };
    const card = elem("article", "book-card tag-resource-card");
    card.tabIndex = 0;
    card.setAttribute("role", "button");
    card.setAttribute("aria-label", `${tagSourceLabel(sourcePage)}: ${item.title || ""}`);
    applyResourceSelectionState(card, ref);
    card.appendChild(buildCoverSlot(item, "cover", sourcePage === "library"));
    const meta = elem("div", "tag-card-meta");
    meta.appendChild(elem("div", "card-title", item.title || ""));
    meta.appendChild(elem("span", `tag-source-badge tag-source-${sourcePage}`, tagSourceLabel(sourcePage)));
    card.appendChild(meta);
    card.addEventListener("click", (event) => handleResourceSelection(ref, event));
    card.addEventListener("keydown", (event) => handleResourceSelectionKeydown(ref, event));
    card.addEventListener("dblclick", () => State.bridge.openResource(sourcePage, item.id));
    card.addEventListener("contextmenu", (event) => {
      event.preventDefault();
      openContextMenu(event, sourcePage, item, false);
    });
    return card;
  });
}

const RECOMMENDATION_CARD_MIN_WIDTH = 120;
const RECOMMENDATION_CARD_MAX_WIDTH = 260;
const RECOMMENDATION_CARD_GAP = 18;

function recommendationLayoutForWidth(containerWidth, requestedColumns) {
  const width = Math.max(0, Number(containerWidth) || 0);
  const desired = getRecommendationColumnsPerCategory({ recommendationColumnsPerCategory: requestedColumns });
  const maxFit = Math.max(1, Math.floor(
    (width + RECOMMENDATION_CARD_GAP) / (RECOMMENDATION_CARD_MIN_WIDTH + RECOMMENDATION_CARD_GAP)
  ));
  const columns = Math.min(desired, maxFit);
  const available = Math.max(0, (width - RECOMMENDATION_CARD_GAP * (columns - 1)) / columns);
  return { columns, cardWidth: Math.floor(Math.min(RECOMMENDATION_CARD_MAX_WIDTH, available)) };
}

function attachRecommendationLayout(area, columnsRoot) {
  let frameId = null;
  const sync = () => {
    frameId = null;
    const desired = getRecommendationColumnsPerCategory();
    columnsRoot.querySelectorAll(".recommendation-stack").forEach((stack) => {
      const width = stack.clientWidth;
      if (!width) return;
      const layout = recommendationLayoutForWidth(width, desired);
      stack.dataset.effectiveColumns = String(layout.columns);
      stack.style.gridTemplateColumns = `repeat(${layout.columns}, minmax(0, ${layout.cardWidth}px))`;
    });
  };
  const schedule = () => {
    if (frameId != null) return;
    frameId = requestAnimationFrame(sync);
  };
  sync();
  const observer = new ResizeObserver(schedule);
  observer.observe(columnsRoot);
  area._recommendationCleanup = () => {
    observer.disconnect();
    if (frameId != null) cancelAnimationFrame(frameId);
  };
}

function recommendationColumnTitle(key) {
  const labels = {
    books: t("recommendations.books", "Books"),
    novels: t("recommendations.novels", "Novels"),
    comics: t("recommendations.comics", "Comics"),
  };
  return labels[key] || key;
}

function renderRecommendations(area, data) {
  const columns = elem("div", "recommendation-columns");
  (data.columns || []).forEach((column) => {
    const section = elem("section", "recommendation-column");
    section.appendChild(elem("h2", "recommendation-column-title", recommendationColumnTitle(column.key)));
    const stack = elem("div", "recommendation-stack");
    const items = column.items || [];
    if (!items.length) {
      stack.appendChild(buildEmpty(t("recommendations.empty_column", "No items available.")));
    } else {
      items.forEach((item) => {
        const card = elem("article", "book-card");
        card.tabIndex = 0;
        card.setAttribute("role", "button");
        card.setAttribute("aria-label", item.title || recommendationColumnTitle(column.key));
        const selected = State.recommendationSelection;
        if (selected && selected.sourcePage === column.sourcePage && selected.id === item.id) {
          card.classList.add("selected");
        }
        card.appendChild(buildCoverSlot(item, "cover", column.sourcePage === "library"));
        card.addEventListener("click", () => selectRecommendedResource(column.sourcePage, item.id, card));
        card.addEventListener("keydown", (event) => {
          if (event.key !== "Enter" && event.key !== " ") return;
          event.preventDefault();
          selectRecommendedResource(column.sourcePage, item.id, card);
        });
        card.addEventListener("dblclick", () => State.bridge.openResource(column.sourcePage, item.id));
        card.addEventListener("contextmenu", (event) => {
          event.preventDefault();
          openContextMenu(event, column.sourcePage, item, false);
        });
        stack.appendChild(card);
      });
    }
    section.appendChild(stack);
    columns.appendChild(section);
  });
  area.appendChild(columns);
  attachRecommendationLayout(area, columns);
}

function getBufferScreens() {
  const v = Number(State.settings.viewportBufferScreens);
  if (!Number.isFinite(v)) return 3;
  return Math.min(6, Math.max(3, Math.round(v)));
}

function getGridColumns() {
  const v = Number(State.settings.gridColumns);
  if (!Number.isFinite(v)) return 6;
  const allowed = new Set([4, 5, 6, 7, 8, 10, 12]);
  const rounded = Math.round(v);
  return allowed.has(rounded) ? rounded : 6;
}

function contentInnerWidth(area) {
  const cs = getComputedStyle(area);
  const pl = parseFloat(cs.paddingLeft) || 0;
  const pr = parseFloat(cs.paddingRight) || 0;
  return Math.max(0, area.clientWidth - pl - pr);
}

function measureCoverGridMetrics(areaWidth, withMeta) {
  const gap = 18;
  const minCol = withMeta ? 140 : 100;
  const desired = getGridColumns();
  // Cap columns so each cover stays readable; fewer cols => larger on-screen footprint => fewer concurrent decodes.
  let cols = Math.max(1, Math.min(desired, Math.floor((areaWidth + gap) / (minCol + gap)) || 1));
  let cardWidth = (areaWidth - (cols - 1) * gap) / cols;
  if (cardWidth < minCol && cols > 1) {
    cols = Math.max(1, Math.floor((areaWidth + gap) / (minCol + gap)) || 1);
    cardWidth = (areaWidth - (cols - 1) * gap) / cols;
  }
  const coverHeight = cardWidth * 1.5;
  const rowHeight = coverHeight + gap + (withMeta ? 48 : 0);
  return { cols, cardWidth, coverHeight, rowHeight, gap };
}

function visibleIndexRange(scrollTop, viewH, itemCount, cols, rowH, bufferScreens) {
  if (!itemCount || rowH <= 0) return { start: 0, end: -1, totalRows: 0, topPad: 0, bottomPad: 0 };
  const totalRows = Math.max(1, Math.ceil(itemCount / cols));
  const bufferPx = bufferScreens * Math.max(viewH, 1);
  const startRow = Math.max(0, Math.floor((scrollTop - bufferPx) / rowH));
  const endRow = Math.min(
    totalRows - 1,
    Math.max(0, Math.ceil((scrollTop + viewH + bufferPx) / rowH) - 1)
  );
  const start = Math.min(itemCount, startRow * cols);
  const end = Math.min(itemCount, (endRow + 1) * cols) - 1;
  const topPad = startRow * rowH;
  const bottomPad = Math.max(0, (totalRows - endRow - 1) * rowH);
  return { start, end, totalRows, topPad, bottomPad };
}

const TABLE_ROW_HEIGHT = 64;

function teardownVirtualWindow(area) {
  if (area && area._virtCleanup) {
    area._virtCleanup();
    area._virtCleanup = null;
  }
  if (area && area._recommendationCleanup) {
    area._recommendationCleanup();
    area._recommendationCleanup = null;
  }
}

function attachVirtualWindow(area, gen, page, syncFn) {
  let rafId = null;
  const schedule = () => {
    if (rafId != null) return;
    rafId = requestAnimationFrame(() => {
      rafId = null;
      if (gen != null && gen !== State.renderGen) return;
      syncFn();
      State.scrollPos[page] = area.scrollTop;
    });
  };
  const onScroll = () => schedule();
  area.addEventListener("scroll", onScroll, { passive: true });
  let ro = null;
  if (typeof ResizeObserver !== "undefined") {
    ro = new ResizeObserver(schedule);
    ro.observe(area);
  }
  const saved = Number(State.scrollPos[page] || 0);
  if (saved > 0) area.scrollTop = saved;
  schedule();
  return () => {
    area.removeEventListener("scroll", onScroll);
    if (ro) ro.disconnect();
    if (rafId != null) cancelAnimationFrame(rafId);
  };
}

function mountVirtualCoverGrid(area, items, page, withMeta, gen, buildCard) {
  const topSpacer = elem("div", "virt-spacer-top");
  const grid = elem("div", withMeta ? "cover-grid with-meta" : "cover-grid");
  const bottomSpacer = elem("div", "virt-spacer-bottom");
  area.appendChild(topSpacer);
  area.appendChild(grid);
  area.appendChild(bottomSpacer);
  let lastKey = "";

  const sync = () => {
    if (gen != null && gen !== State.renderGen) return;
    const metrics = measureCoverGridMetrics(contentInnerWidth(area), withMeta);
    grid.style.gridTemplateColumns = `repeat(${metrics.cols}, minmax(0, 1fr))`;
    const range = visibleIndexRange(
      area.scrollTop, area.clientHeight, items.length,
      metrics.cols, metrics.rowHeight, getBufferScreens()
    );
    const key = [metrics.cols, range.start, range.end, range.topPad, range.bottomPad].join(":");
    if (key === lastKey) return;
    lastKey = key;
    topSpacer.style.height = range.topPad + "px";
    bottomSpacer.style.height = range.bottomPad + "px";
    clear(grid);
    if (range.end < range.start) return;
    const frag = document.createDocumentFragment();
    for (let i = range.start; i <= range.end; i++) frag.appendChild(buildCard(items[i], i));
    grid.appendChild(frag);
  };

  area._virtCleanup = attachVirtualWindow(area, gen, page, sync);
}

function resourceRefForPage(page, item) {
  return {
    sourcePage: tagSourcePage(page),
    id: String(item && item.id || ""),
  };
}

function prepareResourceSelection(page, data, items, refBuilder) {
  const buildRef = refBuilder || ((item) => resourceRefForPage(page, item));
  return configureResourceSelection(page, data, (items || []).map(buildRef));
}

function applyResourceSelectionState(node, ref) {
  const selected = State.resourceSelection.selectedKeys.has(resourceSelectionKey(ref));
  node.dataset.selectionKey = resourceSelectionKey(ref);
  node.classList.toggle("selected", selected);
  node.setAttribute("aria-selected", selected ? "true" : "false");
}

function syncResourceSelectionNodes() {
  const area = $("contentArea");
  if (!area) return;
  area.querySelectorAll("[data-selection-key]").forEach((node) => {
    const selected = State.resourceSelection.selectedKeys.has(String(node.dataset.selectionKey || ""));
    node.classList.toggle("selected", selected);
    node.setAttribute("aria-selected", selected ? "true" : "false");
  });
}

function renderResourceSelectionDetail() {
  const refs = selectedResourceRefs();
  if (!refs.length) {
    State.tagSelection = null;
    if (State.currentPage) delete State.selected[State.currentPage];
    renderDetailEmpty();
    return;
  }
  if (refs.length > 1) {
    State.tagSelection = null;
    if (State.currentPage) delete State.selected[State.currentPage];
    renderBatchSelectionPanel(refs);
    return;
  }
  const ref = refs[0];
  if (State.currentPage === TAG_MANAGER_PAGE) {
    State.tagSelection = { sourcePage: ref.sourcePage, id: ref.id };
  } else {
    State.selected[State.currentPage] = ref.id;
  }
  const expectedKey = resourceSelectionKey(ref);
  State.bridge.getDetail(ref.sourcePage, ref.id, (json) => {
    const current = selectedResourceRefs();
    if (current.length !== 1 || resourceSelectionKey(current[0]) !== expectedKey) return;
    renderDetail(safeParse(json), ref.sourcePage);
  });
}

function handleResourceSelection(ref, event) {
  updateResourceSelection(ref, event || {});
  syncResourceSelectionNodes();
  renderResourceSelectionDetail();
}

function handleResourceSelectionKeydown(ref, event) {
  if (!event) return;
  if (event.key === "Enter") {
    event.preventDefault();
    handleResourceSelection(ref, {});
    return;
  }
  if (event.key !== " ") return;
  event.preventDefault();
  handleResourceSelection(ref, event);
}

function renderGrid(area, items, page, isCollectionDetail, gen) {
  const showFormatBadge = page === "library" || (isCollectionDetail && page !== "comic" && page !== "comic_collections");
  prepareResourceSelection(page, currentPageData(), items);
  mountVirtualCoverGrid(area, items, page, false, gen, (item) => {
    const ref = resourceRefForPage(page, item);
    const card = elem("article", "book-card");
    card.setAttribute("role", "button");
    card.setAttribute("tabindex", "0");
    card.setAttribute("aria-label", item.title || "");
    applyResourceSelectionState(card, ref);
    card.appendChild(buildCoverSlot(item, "cover", showFormatBadge));
    card.addEventListener("click", (event) => handleResourceSelection(ref, event));
    card.addEventListener("keydown", (event) => handleResourceSelectionKeydown(ref, event));
    card.addEventListener("dblclick", () => State.bridge.openResource(page, item.id));
    card.addEventListener("contextmenu", (e) => { e.preventDefault(); openContextMenu(e, page, item, isCollectionDetail); });
    return card;
  });
}

function renderTextNovelGrid(area, items, page, gen) {
  prepareResourceSelection(page, currentPageData(), items);
  mountVirtualCoverGrid(area, items, page, true, gen, (item) => {
    const ref = resourceRefForPage(page, item);
    const card = elem("article", "book-card");
    card.setAttribute("role", "button");
    card.setAttribute("tabindex", "0");
    card.setAttribute("aria-label", item.title || "");
    applyResourceSelectionState(card, ref);
    card.appendChild(buildCover(item, "cover"));
    card.appendChild(elem("div", "card-title", item.title || ""));
    card.addEventListener("click", (event) => handleResourceSelection(ref, event));
    card.addEventListener("keydown", (event) => handleResourceSelectionKeydown(ref, event));
    card.addEventListener("dblclick", () => State.bridge.openResource(page, item.id));
    card.addEventListener("contextmenu", (event) => {
      event.preventDefault();
      openContextMenu(event, page, item, false);
    });
    return card;
  });
}

function renderCollections(area, items) {
  const page = State.currentPage;
  mountVirtualCoverGrid(area, items, page, true, State.renderGen, (item) => {
    const card = elem("article", "book-card");
    card.appendChild(buildCover(item, "cover"));
    card.appendChild(elem("div", "card-title", item.title));
    card.appendChild(elem("div", "card-meta", item.meta || ""));
    const openCol = () => {
      openCollectionWithHistory(page, item.collectionId, false);
    };
    card.addEventListener("click", openCol);
    card.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      openCollectionCardMenu(e, item, openCol);
    });
    return card;
  });
}

function renderComic(area, data, gen) {
  let items = data.items || [];
  const isPagination = data.viewMode === "pagination";
  let pageSize = data.pageSize || 48;
  const pageKey = State.currentPage;
  if (!State.comicPageNum[pageKey]) State.comicPageNum[pageKey] = 1;
  State._comicPage = State.comicPageNum[pageKey];
  let totalPages = 1;
  if (isPagination) {
    totalPages = Math.max(1, Math.ceil(items.length / pageSize));
    if (State._comicPage > totalPages) State._comicPage = totalPages;
    State.comicPageNum[pageKey] = State._comicPage;
    const start = (State._comicPage - 1) * pageSize;
    items = items.slice(start, start + pageSize);
  }
  renderGrid(area, items, pageKey, Boolean(data.collectionId), gen);
  if (isPagination) {
    const bar = elem("div", "detail-actions");
    bar.style.justifyContent = "flex-end";
    const prev = elem("button", "ghost-btn", t("comic.pagination.prev", "Prev"));
    const label = elem("span", "small-note", fmt(t("comic.pagination.status", "Page {current}/{total}"), { current: State._comicPage, total: totalPages }));
    const next = elem("button", "ghost-btn", t("comic.pagination.next", "Next"));
    prev.disabled = State._comicPage <= 1;
    next.disabled = State._comicPage >= totalPages;
    prev.addEventListener("click", () => {
      clearResourceSelection();
      renderDetailEmpty();
      State._comicPage--;
      State.comicPageNum[pageKey] = State._comicPage;
      clearPageScroll(pageKey);
      scheduleRenderPage();
    });
    next.addEventListener("click", () => {
      clearResourceSelection();
      renderDetailEmpty();
      State._comicPage++;
      State.comicPageNum[pageKey] = State._comicPage;
      clearPageScroll(pageKey);
      scheduleRenderPage();
    });
    bar.appendChild(prev); bar.appendChild(label); bar.appendChild(next);
    area.appendChild(bar);
  }
}

function renderTable(area, items, page, pageSort) {
  const gen = State.renderGen;
  prepareResourceSelection(page, currentPageData(), items);
  const topSpacer = elem("div", "virt-spacer-top");
  const table = elem("table", "table");
  const thead = elem("thead");
  const htr = elem("tr");
  const sortableBookList = page === "library"
    || page === "text_novel"
    || ((page === "collections" || page === "novel_collections") && Boolean(pageSort));
  const showCoverColumn = page !== "text_novel" && page !== "novel_collections";
  const headers = [
    ["title", t("detail.title", "Title")],
    ["author", t("detail.author", "Author")],
    ["tags", t("detail.tags", "Tags")],
    ["path", t("detail.path", "Path")],
  ];
  if (showCoverColumn) htr.appendChild(elem("th", null, t("detail.cover", "Cover")));
  headers.forEach(([field, label]) => {
    if (!sortableBookList) {
      htr.appendChild(elem("th", null, label));
      return;
    }
    const th = elem("th", "sortable-column-header");
    const currentSort = String(pageSort || (page === "library" ? "title_asc" : "file_mtime_desc"));
    const ascending = currentSort === `${field}_asc`;
    const descending = currentSort === `${field}_desc`;
    th.setAttribute("aria-sort", ascending ? "ascending" : (descending ? "descending" : "none"));
    const button = elem("button", "column-sort-button");
    button.type = "button";
    button.appendChild(elem("span", "column-sort-label", label));
    if (ascending || descending) {
      button.classList.add("active");
      button.appendChild(elem("span", "column-sort-indicator", ascending ? "▲" : "▼"));
    }
    button.addEventListener("click", () => {
      const nextOrder = ascending ? `${field}_desc` : `${field}_asc`;
      setBookPageSort(page, nextOrder);
    });
    th.appendChild(button);
    htr.appendChild(th);
  });
  thead.appendChild(htr);
  table.appendChild(thead);
  const tbody = elem("tbody");
  table.appendChild(tbody);
  const bottomSpacer = elem("div", "virt-spacer-bottom");
  area.appendChild(topSpacer);
  area.appendChild(table);
  area.appendChild(bottomSpacer);
  let lastKey = "";

  const sync = () => {
    if (gen !== State.renderGen) return;
    const range = visibleIndexRange(
      area.scrollTop, area.clientHeight, items.length,
      1, TABLE_ROW_HEIGHT, getBufferScreens()
    );
    const key = [range.start, range.end, range.topPad, range.bottomPad].join(":");
    if (key === lastKey) return;
    lastKey = key;
    topSpacer.style.height = range.topPad + "px";
    bottomSpacer.style.height = range.bottomPad + "px";
    clear(tbody);
    if (range.end < range.start) return;
    const frag = document.createDocumentFragment();
    for (let i = range.start; i <= range.end; i++) {
      const item = items[i];
      const ref = resourceRefForPage(page, item);
      const tr = elem("tr");
      tr.setAttribute("role", "row");
      tr.setAttribute("tabindex", "0");
      tr.setAttribute("aria-label", item.title || "");
      applyResourceSelectionState(tr, ref);
      if (showCoverColumn) {
        const coverTd = elem("td");
        if (item.cover) coverTd.appendChild(buildCover(item, "mini-cover"));
        tr.appendChild(coverTd);
      }
      tr.appendChild(elem("td", null, item.title));
      tr.appendChild(elem("td", null, item.author || ""));
      tr.appendChild(elem("td", null, (item.tags || []).join(", ")));
      tr.appendChild(elem("td", null, item.path || ""));
      tr.addEventListener("click", (event) => handleResourceSelection(ref, event));
      tr.addEventListener("keydown", (event) => handleResourceSelectionKeydown(ref, event));
      tr.addEventListener("dblclick", () => State.bridge.openResource(page, item.id));
      tr.addEventListener("contextmenu", (e) => { e.preventDefault(); openContextMenu(e, page, item, false); });
      frag.appendChild(tr);
    }
    tbody.appendChild(frag);
  };

  area._virtCleanup = attachVirtualWindow(area, gen, page, sync);
}

const FORMAT_BADGE_LABELS = {
  ".pdf": "PDF",
  ".epub": "EPUB",
  ".html": "HTML",
  ".htm": "HTML",
  ".md": "MD",
  ".markdown": "MD",
  ".fb2": "FB2",
  ".fb2.zip": "FB2",
  ".docx": "DOCX",
};

function formatBadgeLabel(item) {
  const ext = String(item.extension || "").trim().toLowerCase();
  if (ext && FORMAT_BADGE_LABELS[ext]) return FORMAT_BADGE_LABELS[ext];
  const type = String(item.type || "").trim();
  if (type && type !== "book" && type !== "text_novel") return type.toUpperCase();
  return "";
}

function buildCoverSlot(item, cls, showFormatBadge) {
  if (!showFormatBadge) return buildCover(item, cls);
  const wrap = elem("div", "cover-wrap");
  wrap.appendChild(buildCover(item, cls));
  const label = formatBadgeLabel(item);
  if (label) wrap.appendChild(elem("span", "format-badge", label));
  return wrap;
}

function buildCover(item, cls) {
  if (item.cover) {
    const img = elem("img", cls);
    img.alt = item.title || "";
    img.decoding = "async";
    // Grid covers: eager inside the virtual window (window size is capped by buffer screens).
    if (cls === "cover" || cls === "mini-cover") {
      img.loading = "eager";
    } else {
      img.loading = "lazy";
    }
    img.src = item.cover;
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
  State.bridge.getDetail(page, id, (json) => { const d = safeParse(json); renderDetail(d, page); });
}

function selectRecommendedResource(sourcePage, id, node) {
  State.recommendationSelection = { sourcePage, id };
  const area = $("contentArea");
  if (area) area.querySelectorAll(".selected").forEach((selected) => selected.classList.remove("selected"));
  node.classList.add("selected");
  State.bridge.getDetail(sourcePage, id, (json) => {
    const selected = State.recommendationSelection;
    if (State.currentPage !== RANDOM_RECOMMENDATIONS_PAGE || !selected || selected.sourcePage !== sourcePage || selected.id !== id) return;
    renderDetail(safeParse(json), sourcePage);
  });
}

function selectTaggedResource(sourcePage, id, node) {
  State.tagSelection = { sourcePage, id };
  const area = $("contentArea");
  if (area) area.querySelectorAll(".selected").forEach((selected) => selected.classList.remove("selected"));
  node.classList.add("selected");
  State.bridge.getDetail(sourcePage, id, (json) => {
    const selected = State.tagSelection;
    if (State.currentPage !== TAG_MANAGER_PAGE || !selected || selected.sourcePage !== sourcePage || selected.id !== id) return;
    renderDetail(safeParse(json), sourcePage);
  });
}

function refreshDetailIfSelected() {
  if (State.currentPage === RANDOM_RECOMMENDATIONS_PAGE) {
    const selected = State.recommendationSelection;
    if (selected) {
      State.bridge.getDetail(selected.sourcePage, selected.id, (json) => renderDetail(safeParse(json), selected.sourcePage));
    }
    return;
  }
  if (State.currentPage === TAG_MANAGER_PAGE) {
    const selected = State.tagSelection;
    if (selected) {
      State.bridge.getDetail(selected.sourcePage, selected.id, (json) => renderDetail(safeParse(json), selected.sourcePage));
    }
    return;
  }
  const id = State.selected[State.currentPage];
  if (id) State.bridge.getDetail(State.currentPage, id, (json) => renderDetail(safeParse(json), State.currentPage));
}

function renderDetailEmpty() {
  $("detailEmpty").classList.remove("hidden");
  $("detailContent").classList.add("hidden");
}

function renderBatchSelectionPanel(refs) {
  const selectedRefs = Array.isArray(refs) ? refs : selectedResourceRefs();
  const empty = $("detailEmpty");
  const content = $("detailContent");
  empty.classList.add("hidden");
  content.classList.remove("hidden");
  clear(content);
  content.appendChild(elem(
    "h2",
    null,
    fmt(t("batch.selection_count", "{count} items selected"), { count: selectedRefs.length })
  ));
  const counts = { library: 0, text_novel: 0, comic: 0 };
  selectedRefs.forEach((ref) => {
    if (Object.prototype.hasOwnProperty.call(counts, ref.sourcePage)) counts[ref.sourcePage] += 1;
  });
  const meta = elem("div", "detail-meta batch-selection-summary");
  [
    ["library", "batch.books", "Books"],
    ["text_novel", "batch.novels", "Text Novels"],
    ["comic", "batch.comics", "Comics"],
  ].forEach(([page, key, fallback]) => {
    if (!counts[page]) return;
    meta.appendChild(buildDetailBlock(t(key, fallback), String(counts[page])));
  });
  content.appendChild(meta);
  const actions = elem("div", "detail-actions batch-selection-actions");
  const quickAdd = elem("button", "primary-btn", t("batch.quick_add", "Batch Quick Add"));
  quickAdd.addEventListener("click", () => openBatchQuickAddModal(selectedResourceRefs()));
  const clearButton = elem("button", "ghost-btn", t("batch.clear_selection", "Clear selection"));
  clearButton.addEventListener("click", () => {
    clearResourceSelection();
    syncResourceSelectionNodes();
    renderDetailEmpty();
  });
  actions.appendChild(quickAdd);
  actions.appendChild(clearButton);
  content.appendChild(actions);
}

function renderDetail(d, sourcePage) {
  if (!d || !d.id) { renderDetailEmpty(); return; }
  const actionPage = sourcePage || State.currentPage;
  const empty = $("detailEmpty");
  const content = $("detailContent");
  empty.classList.add("hidden");
  content.classList.remove("hidden");
  clear(content);
  content.appendChild(wrapDetailCover(d));
  content.appendChild(elem("h2", null, d.title));

  const meta = elem("div", "detail-meta");
  const isComic = COMIC_PAGES.has(actionPage);
  if (d.author) meta.appendChild(buildDetailBlock(t("detail.author", "Author"), d.author));
  if (d.publisher && d.publisher.toLowerCase() !== "unknown") meta.appendChild(buildDetailBlock(t("detail.publisher", "Publisher"), d.publisher));
  if (isComic && d.imageCount) meta.appendChild(buildDetailBlock(t("detail.images", "Images"), String(d.imageCount)));
  if (d.tags && d.tags.length) meta.appendChild(buildDetailBlock(t("detail.tags", "Tags"), d.tags.join("、")));
  if (d.bookCollections && d.bookCollections.length) {
    meta.appendChild(buildDetailBlock(t("detail.collections", "Collections"), d.bookCollections.map((c) => c.name).join("、")));
  }
  if (d.comicCollections && d.comicCollections.length) {
    meta.appendChild(buildDetailBlock(t("detail.collections", "Collections"), d.comicCollections.map((c) => c.name).join("、")));
  }
  if (d.path) meta.appendChild(buildDetailBlock(t("detail.file", "File"), d.path));
  if (d.info) meta.appendChild(buildDetailBlock(t("detail.preview", "Text Preview"), d.info));
  content.appendChild(meta);

  const actions = elem("div", "detail-actions");
  const openBtn = elem("button", "primary-btn", t("detail.open", "Open"));
  openBtn.addEventListener("click", () => State.bridge.openResource(actionPage, d.id));
  actions.appendChild(openBtn);
  const qa = elem("button", "ghost-btn", t("detail.quick_add", "Quick Add"));
  qa.addEventListener("click", () => openQuickAddModal(d, actionPage));
  actions.appendChild(qa);
  const coverBtn = elem("button", "ghost-btn", t("detail.edit_cover", "Edit Cover"));
  coverBtn.addEventListener("click", () => State.bridge.editCover(d.id));
  actions.appendChild(coverBtn);
  if (actionPage === "library" || actionPage === "text_novel" || isComic) {
    const removeBtn = elem("button", "danger-btn", t("menu.remove_library", "Remove from Library"));
    removeBtn.addEventListener("click", () => confirmRemoveFromLibrary(actionPage, d));
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

/* ---------- actions and shortcuts ---------- */
function isComicActionContext(context) {
  return Boolean(context && (context.page === "comic" || context.page === "comic_collections"));
}

function tagSourcePage(page) {
  if (page === "comic" || page === "comic_collections") return "comic";
  if (page === "text_novel" || page === "novel_collections") return "text_novel";
  return "library";
}

const SHORTCUT_ACTIONS = {
  exit_collection: {
    labelKey: "shortcut.action.exit_collection",
    needsResource: false,
    available: () => true,
    run: () => exitCurrentCollection(),
  },
  reopen_recent_collection: {
    labelKey: "shortcut.action.reopen_recent_collection",
    needsResource: false,
    available: () => true,
    run: () => reopenRecentCollection(),
  },
  open_resource: {
    labelKey: "shortcut.action.open_resource",
    needsResource: true,
    available: () => true,
    run: (context) => State.bridge.openResource(context.page, context.item.id),
  },
  open_folder: {
    labelKey: "shortcut.action.open_folder",
    needsResource: true,
    available: (context) => !isComicActionContext(context),
    run: (context) => State.bridge.openFolder(context.item.id),
  },
  quick_add: {
    labelKey: "shortcut.action.quick_add",
    needsResource: true,
    available: () => true,
    run: (context) => {
      if (context.batchRefs && context.batchRefs.length > 1) {
        openBatchQuickAddModal(context.batchRefs);
      } else {
        openQuickAddModal(context.item, context.page);
      }
    },
  },
  edit_cover: {
    labelKey: "shortcut.action.edit_cover",
    needsResource: true,
    available: () => true,
    run: (context) => State.bridge.editCover(context.item.id),
  },
  remove_from_collection: {
    labelKey: "shortcut.action.remove_from_collection",
    needsResource: true,
    available: (context) => Boolean(context.isCollectionDetail && context.collectionId),
    run: (context) => State.bridge.removeFromCollection(context.item.id, context.collectionId),
  },
  remove_from_library: {
    labelKey: "shortcut.action.remove_from_library",
    needsResource: true,
    available: (context) => (
      context.page === "library" || context.page === "text_novel" || context.page === "comic"
      || context.isCollectionDetail
    ),
    run: (context) => confirmRemoveFromLibrary(context.page, context.item),
  },
};

function showShortcutNotice(key, params) {
  showToast(
    t("shortcut.notice.title", "Shortcut"),
    fmt(t(key, key), params || {}),
    "info"
  );
}

function executeAction(actionId, context) {
  const action = SHORTCUT_ACTIONS[actionId];
  if (!action) {
    showShortcutNotice("shortcut.unavailable");
    return false;
  }
  if (action.needsResource && (!context || !context.item || !context.item.id)) {
    showShortcutNotice("shortcut.no_selection");
    return false;
  }
  if (!action.available(context)) {
    showShortcutNotice("shortcut.unavailable");
    return false;
  }
  action.run(context);
  return true;
}

function selectedResourceActionContext() {
  if (State.currentPage === RANDOM_RECOMMENDATIONS_PAGE) {
    const selected = State.recommendationSelection;
    const columns = State.recommendations && Array.isArray(State.recommendations.columns)
      ? State.recommendations.columns : [];
    const column = selected && columns.find((entry) => entry.sourcePage === selected.sourcePage);
    const item = column && Array.isArray(column.items)
      ? column.items.find((entry) => String(entry.id) === String(selected.id)) : null;
    if (!item) {
      State.recommendationSelection = null;
      return null;
    }
    return {
      page: column.sourcePage,
      item,
      isCollectionDetail: false,
      collectionId: null,
    };
  }

  if (State.currentPage === TAG_MANAGER_PAGE) {
    const batchRefs = selectedResourceRefs();
    const focusKey = State.resourceSelection.focusKey;
    const selected = batchRefs.find((ref) => resourceSelectionKey(ref) === focusKey) || batchRefs[0] || State.tagSelection;
    const items = State.tagDetail && Array.isArray(State.tagDetail.items) ? State.tagDetail.items : [];
    const item = selected
      ? items.find((entry) => entry.sourcePage === selected.sourcePage && String(entry.id) === String(selected.id))
      : null;
    if (!item) {
      State.tagSelection = null;
      return null;
    }
    return {
      page: selected.sourcePage,
      item,
      isCollectionDetail: false,
      collectionId: null,
      batchRefs,
    };
  }

  const page = State.currentPage;
  const data = State.pages[page] || {};
  const batchRefs = selectedResourceRefs();
  const focusKey = State.resourceSelection.focusKey;
  const focusedRef = batchRefs.find((ref) => resourceSelectionKey(ref) === focusKey) || batchRefs[0] || null;
  const selectedId = focusedRef ? focusedRef.id : State.selected[page];
  const items = Array.isArray(data.items) ? data.items : [];
  const item = items.find((entry) => String(entry.id) === String(selectedId));
  if (!item) {
    if (selectedId != null) delete State.selected[page];
    return null;
  }
  return {
    page: focusedRef ? focusedRef.sourcePage : page,
    item,
    isCollectionDetail: isCollectionDetailData(data),
    collectionId: data.collectionId || null,
    batchRefs,
  };
}

function clearInvalidCurrentSelectionAfterResourceChange() {
  const page = State.currentPage;
  if (page === RANDOM_RECOMMENDATIONS_PAGE || page === TAG_MANAGER_PAGE || page === "settings") return false;
  const selectedId = State.selected[page];
  if (selectedId == null) return false;
  const data = State.pages[page] || {};
  if (COLLECTION_PAGES.has(page) && !isCollectionDetailData(data)) return false;
  const items = Array.isArray(data.items) ? data.items : [];
  if (items.some((item) => String(item.id) === String(selectedId))) return false;
  delete State.selected[page];
  renderDetailEmpty();
  showShortcutNotice("shortcut.selection_stale");
  return true;
}

function shortcutBindings() {
  const bindings = State.settings && State.settings.shortcutBindings;
  return bindings && typeof bindings === "object" ? bindings : {};
}

function shortcutActionForInput(inputToken) {
  return Object.keys(SHORTCUT_ACTIONS).find((actionId) => shortcutBindings()[actionId] === inputToken) || "";
}

function dispatchShortcutInput(inputToken) {
  const actionId = shortcutActionForInput(inputToken);
  if (!actionId) return false;
  const action = SHORTCUT_ACTIONS[actionId];
  const context = action.needsResource ? selectedResourceActionContext() : null;
  return executeAction(actionId, context);
}

function isVisibleOverlay(id) {
  const overlay = $(id);
  return Boolean(overlay && !overlay.classList.contains("hidden"));
}

function isEditableShortcutTarget(target) {
  if (!target) return false;
  const tag = String(target.tagName || "").toLowerCase();
  if (["input", "select", "textarea"].includes(tag) || target.isContentEditable) return true;
  return Boolean(target.closest && target.closest("[contenteditable='true']"));
}

function shortcutInteractionBlocked(event) {
  const target = event && event.target ? event.target : document.activeElement;
  return isEditableShortcutTarget(target)
    || isVisibleOverlay("overlay")
    || isVisibleOverlay("textRulesOverlay");
}

function beginShortcutCapture(actionId) {
  if (!SHORTCUT_ACTIONS[actionId]) return false;
  State.shortcutCaptureAction = actionId;
  if (State.currentPage === "settings") renderSettings();
  return true;
}

function cancelShortcutCapture() {
  if (!State.shortcutCaptureAction) return false;
  State.shortcutCaptureAction = "";
  if (State.currentPage === "settings") renderSettings();
  return true;
}

function persistShortcutBinding(actionId, inputToken) {
  if (!State.bridge || !State.bridge.setShortcutBinding) return false;
  State.bridge.setShortcutBinding(actionId, inputToken, (json) => {
    const result = safeParse(json);
    if (!result) {
      showShortcutNotice("shortcut.binding_invalid");
      return;
    }
    if (!result.ok) {
      if (result.error === "duplicate") {
        const conflict = SHORTCUT_ACTIONS[result.conflictAction];
        showShortcutNotice("shortcut.binding_duplicate", {
          action: conflict ? t(conflict.labelKey, result.conflictAction) : result.conflictAction,
        });
      } else {
        showShortcutNotice("shortcut.binding_invalid");
      }
      if (State.currentPage === "settings") renderSettings();
      return;
    }
    State.settings.shortcutBindings = result.bindings || {};
    State.shortcutCaptureAction = "";
    if (State.currentPage === "settings") renderSettings();
  });
  return true;
}

function clearShortcutBinding(actionId) {
  if (State.shortcutCaptureAction === actionId) State.shortcutCaptureAction = "";
  return persistShortcutBinding(actionId, "");
}

function captureShortcutInput(inputToken) {
  if (!State.shortcutCaptureAction || !isBindableShortcutToken(inputToken)) {
    if (State.shortcutCaptureAction) showShortcutNotice("shortcut.binding_invalid");
    return false;
  }
  return persistShortcutBinding(State.shortcutCaptureAction, inputToken);
}

function handleShortcutKeydown(event) {
  if (!event || event.repeat) return false;
  if (State.shortcutCaptureAction) {
    event.preventDefault();
    event.stopPropagation();
    if (event.code === "Escape") {
      cancelShortcutCapture();
      return true;
    }
    const capturedToken = shortcutTokenFromKeyboardEvent(event);
    if (capturedToken) captureShortcutInput(capturedToken);
    else if (!/^(Control|Shift|Alt|Meta)(Left|Right)$/.test(String(event.code || ""))) {
      showShortcutNotice("shortcut.binding_invalid");
    }
    return true;
  }
  const browserToken = shortcutTokenFromKeyboardEvent(event);
  if (browserToken && SHORTCUT_MOUSE_TOKENS.has(browserToken)) {
    event.preventDefault();
    event.stopPropagation();
    if (shortcutInteractionBlocked(event)) return false;
    return dispatchShortcutInput(browserToken);
  }
  if (shortcutInteractionBlocked(event)) return false;
  if (
    event.ctrlKey
    && !event.altKey
    && !event.shiftKey
    && !event.metaKey
    && String(event.code || "") === "KeyA"
    && State.resourceSelection.order.length
  ) {
    event.preventDefault();
    event.stopPropagation();
    selectAllResourcesInScope();
    syncResourceSelectionNodes();
    renderResourceSelectionDetail();
    return true;
  }
  const inputToken = shortcutTokenFromKeyboardEvent(event);
  if (!inputToken || !shortcutActionForInput(inputToken)) return false;
  event.preventDefault();
  event.stopPropagation();
  dispatchShortcutInput(inputToken);
  return true;
}

let lastSideButtonToken = "";
let lastSideButtonAt = 0;

function handleShortcutSideButton(event) {
  const token = shortcutTokenFromMouseEvent(event);
  if (!token) return false;
  if (event && event.preventDefault) event.preventDefault();
  if (event && event.stopPropagation) event.stopPropagation();
  const now = Date.now();
  if (token === lastSideButtonToken && now - lastSideButtonAt < 120) return true;
  lastSideButtonToken = token;
  lastSideButtonAt = now;
  if (State.shortcutCaptureAction) return captureShortcutInput(token);
  if (shortcutInteractionBlocked(event)) return false;
  return dispatchShortcutInput(token);
}

function handleShortcutMouseDown(event) {
  return handleShortcutSideButton(event);
}

function suppressShortcutMouseNavigation(event) {
  return handleShortcutSideButton(event);
}

function handleNativeShortcutInput(inputToken) {
  const token = String(inputToken || "");
  if (State.shortcutCaptureAction) return captureShortcutInput(token);
  if (shortcutInteractionBlocked(null)) return false;
  return dispatchShortcutInput(token);
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
  const ref = { sourcePage: tagSourcePage(page), id: String(item.id) };
  const selectionKey = resourceSelectionKey(ref);
  if (
    State.resourceSelection.order.includes(selectionKey)
    && !State.resourceSelection.selectedKeys.has(selectionKey)
  ) {
    handleResourceSelection(ref, {});
  }
  const batchRefs = selectedResourceRefs();
  const isComic = page === "comic" || (page === "comic_collections" && isComicCollectionDetail());
  const context = {
    page,
    item,
    isCollectionDetail: Boolean(isCollectionDetail),
    collectionId: isCollectionDetail ? currentPageData().collectionId : null,
    batchRefs,
  };
  menuAction(
    isComic ? t("menu.open_cover", "Open Cover") : t("menu.open_external", "Open External"),
    () => executeAction("open_resource", context)
  );
  if (!isComic) {
    menuAction(t("menu.open_folder", "Open Folder"), () => executeAction("open_folder", context));
  }
  menuAction(t("menu.quick_add", "Quick Add Tag / Collection"), () => executeAction("quick_add", context));
  menuAction(t("menu.edit_cover", "Edit Cover..."), () => executeAction("edit_cover", context));
  if (isCollectionDetail) {
    menu.appendChild(elem("hr"));
    menuAction(
      t("menu.collection_remove", "Remove from Collection"),
      () => executeAction("remove_from_collection", context),
      true
    );
  }
  if (page === "library" || page === "text_novel" || page === "comic" || isCollectionDetail) {
    menu.appendChild(elem("hr"));
    menuAction(
      t("menu.remove_library", "Remove from Library"),
      () => executeAction("remove_from_library", context),
      true
    );
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
function setLibraryTaskButtonsDisabled(disabled) {
  const top = $("scanBtn");
  if (top) top.disabled = !!disabled;
  document.querySelectorAll("[data-library-task-btn]").forEach((btn) => {
    btn.disabled = !!disabled;
  });
}

function updateScanState(d) {
  State._scanRunning = !!d.running;
  State._taskKind = d.kind || (String(d.scope || "").includes(":thumb") ? "thumbnail" : "scan");
  const btn = $("scanBtn");
  if (d.running) {
    const scanningLabel = State._taskKind === "thumbnail"
      ? t("topbar.thumb_busy", "Working...")
      : t("topbar.scanning", "Scanning...");
    if (btn) btn.textContent = scanningLabel;
  } else if (btn) {
    btn.textContent = t("topbar.scan", "Scan");
  }
  setLibraryTaskButtonsDisabled(!!d.running);
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
  const close = () => {
    if (modal.parentElement === overlay) closeModal();
  };
  build(modal, close);
  overlay.appendChild(modal);
  overlay.onclick = (e) => {
    if (e.target === overlay && modal.dataset.submitting !== "true") close();
  };
}
function closeModal() { const o = $("overlay"); o.classList.add("hidden"); clear(o); o.onclick = null; }

function modalHeader(modal, title, onClose) {
  const head = elem("div", "modal-title");
  head.appendChild(elem("h3", null, title));
  const x = elem("button", "close-x", "×");
  x.addEventListener("click", onClose);
  head.appendChild(x);
  modal.appendChild(head);
  return x;
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
      State.bridge.createCollection(State.currentPage, name, () => {
        close();
        State.bridge.closeCollection(State.currentPage, (json) => applyCollectionPageData(json));
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
        State.bridge.closeCollection(State.currentPage, (json) => applyCollectionPageData(json));
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
        forgetRecentCollection(State.currentPage, item.collectionId);
        close();
        State.bridge.closeCollection(State.currentPage, (json) => applyCollectionPageData(json));
      });
    });
    actions.appendChild(cancel); actions.appendChild(confirm);
    modal.appendChild(actions);
  });
}

function openQuickAddModal(item, sourcePage) {
  const actionPage = sourcePage || State.currentPage;
  const resourceTagPage = tagSourcePage(actionPage);
  openModal((modal, close) => {
    let submitting = false;
    const requestClose = () => { if (!submitting) close(); };
    const closeButton = modalHeader(modal, t("detail.quick_add", "Quick Add"), requestClose);
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
          if (submitting) return;
          if (State.bridge.removeResourceTag) State.bridge.removeResourceTag(resourceTagPage, item.id, tag);
          else State.bridge.removeTag(item.id, tag);
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
      if (submitting) return;
      const tag = String(value || "").trim();
      if (!tag || workingTags.includes(tag)) return;
      if (State.bridge.addResourceTag) State.bridge.addResourceTag(resourceTagPage, item.id, tag);
      else State.bridge.addTag(item.id, tag);
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
    let exactNameKey = "";
    let exactNameQuery = "";
    let nameKeyRequest = 0;

    const normalizedCollectionName = (value) => String(value || "").trim().toLocaleLowerCase();
    const collectionNameKey = (collection) => String(
      collection.nameKey || normalizedCollectionName(collection.name)
    );

    const quickAddItemIsSelected = () => {
      if (State.currentPage === RANDOM_RECOMMENDATIONS_PAGE) {
        const selected = State.recommendationSelection;
        return Boolean(selected && selected.sourcePage === actionPage && selected.id === item.id);
      }
      if (State.currentPage === TAG_MANAGER_PAGE) {
        const selected = State.tagSelection;
        return Boolean(selected && selected.sourcePage === actionPage && selected.id === item.id);
      }
      return State.selected[State.currentPage] === item.id;
    };

    const renderCollectionRows = () => {
      const queryName = searchInput.value.trim();
      const q = normalizedCollectionName(queryName);
      clear(list);
      const exactKeyResolved = exactNameQuery === queryName;
      const hasExactMatch = exactKeyResolved && exactNameKey && allCollections.some(
        (coll) => collectionNameKey(coll) === exactNameKey
      );
      if (queryName && exactKeyResolved && !hasExactMatch) {
        const create = elem(
          "button",
          "list-item list-item-action quick-create-row",
          fmt(t("quick_add.create_and_add", "Create and add “{name}”"), { name: queryName })
        );
        create.type = "button";
        create.disabled = submitting;
        create.addEventListener("click", () => submitCollectionChanges(queryName));
        list.appendChild(create);
      }
      allCollections
        .filter((coll) => !q || normalizedCollectionName(coll.name).includes(q))
        .forEach((coll) => {
          const collectionId = Number(coll.id);
          const row = elem("div", "list-item list-item-action");
          row.appendChild(elem("span", null, coll.name));
          const isMember = pendingMembers.has(collectionId);
          const btn = elem(
            "button",
            isMember ? "ghost-btn list-action-btn is-added" : "ghost-btn list-action-btn is-add",
            isMember ? t("quick_add.added", "Added") : t("quick_add.add", "Add")
          );
          btn.type = "button";
          btn.disabled = submitting;
          btn.addEventListener("click", (e) => {
            e.stopPropagation();
            if (pendingMembers.has(collectionId)) pendingMembers.delete(collectionId);
            else pendingMembers.add(collectionId);
            renderCollectionRows();
          });
          row.appendChild(btn);
          list.appendChild(row);
        });
    };

    const updateCollectionSearch = () => {
      const queryName = searchInput.value.trim();
      const requestId = ++nameKeyRequest;
      exactNameQuery = "";
      exactNameKey = "";
      renderCollectionRows();
      if (!queryName) {
        exactNameQuery = "";
        renderCollectionRows();
        return;
      }
      State.bridge.getCollectionNameKey(queryName, (key) => {
        if (requestId !== nameKeyRequest || searchInput.value.trim() !== queryName) return;
        exactNameQuery = queryName;
        exactNameKey = String(key || "");
        renderCollectionRows();
      });
    };

    searchInput.addEventListener("input", updateCollectionSearch);
    searchInput.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      const queryName = searchInput.value.trim();
      if (!queryName || exactNameQuery !== queryName || allCollections.some(
        (coll) => collectionNameKey(coll) === exactNameKey
      )) return;
      event.preventDefault();
      submitCollectionChanges(queryName);
    });

    State.bridge.getCollections(actionPage, (cjson) => {
      allCollections = safeParse(cjson) || [];
      State.bridge.getDetail(actionPage, item.id, (djson) => {
        const detail = safeParse(djson) || {};
        (detail.bookCollections || detail.comicCollections || []).forEach((c) => {
          initialMembers.add(Number(c.id));
          pendingMembers.add(Number(c.id));
        });
        renderCollectionRows();
      });
    });

    const actions = elem("div", "modal-actions");
    const cancel = elem("button", "ghost-btn", t("common.cancel", "Cancel"));
    cancel.addEventListener("click", () => {
      if (submitting) return;
      close();
      refreshDetailIfSelected();
    });
    const confirm = elem("button", "primary-btn", t("quick_add.confirm", "Confirm add"));
    const setSubmitting = (value) => {
      submitting = value;
      modal.dataset.submitting = value ? "true" : "false";
      tagInput.disabled = value;
      searchInput.disabled = value;
      closeButton.disabled = value;
      cancel.disabled = value;
      confirm.disabled = value;
      modal.querySelectorAll("button").forEach((button) => { button.disabled = value; });
      renderCollectionRows();
    };

    function submitCollectionChanges(createName) {
      if (submitting) return;
      const addIds = [...pendingMembers]
        .filter((collectionId) => !initialMembers.has(collectionId))
        .sort((a, b) => a - b);
      const removeIds = [...initialMembers]
        .filter((collectionId) => !pendingMembers.has(collectionId))
        .sort((a, b) => a - b);
      const cleanCreateName = String(createName || "").trim();
      if (!addIds.length && !removeIds.length && !cleanCreateName) {
        close();
        refreshDetailIfSelected();
        return;
      }

      setSubmitting(true);
      State.bridge.applyCollectionQuickAdd(
        actionPage,
        item.id,
        JSON.stringify({ addIds, removeIds, createName: cleanCreateName }),
        (resultJson) => {
          const result = safeParse(resultJson);
          if (!result || !result.ok) {
            setSubmitting(false);
            showToast(
              t("quick_add.save_failed_title", "Collection update failed"),
              t("quick_add.save_failed", "Could not save collection changes. Please try again."),
              "warning"
            );
            return;
          }

          const collectionPage = String(result.collectionPage || "");
          const previousCollectionData = State.pages[collectionPage] || {};
          const visibleCollectionId = State.currentPage === collectionPage
            ? Number(previousCollectionData.collectionId || 0)
            : 0;
          const removesVisibleItem = visibleCollectionId > 0 && removeIds.includes(visibleCollectionId);
          if (removesVisibleItem) savePageScroll(State.currentPage);
          if (collectionPage && result.collectionPageData) {
            State.pages[collectionPage] = result.collectionPageData;
          }
          if (result.detail) {
            if (Array.isArray(result.detail.bookCollections)) {
              item.bookCollections = result.detail.bookCollections.slice();
            }
            if (Array.isArray(result.detail.comicCollections)) {
              item.comicCollections = result.detail.comicCollections.slice();
            }
          }

          close();
          if (removesVisibleItem) {
            State.selected[State.currentPage] = null;
            renderDetailEmpty();
            scheduleRenderPage();
          } else if (result.detail && quickAddItemIsSelected()) {
            renderDetail(result.detail, actionPage);
          }
        }
      );
    }

    confirm.addEventListener("click", () => submitCollectionChanges(""));
    actions.appendChild(cancel);
    actions.appendChild(confirm);
    modal.appendChild(actions);
    renderCurrentChips();
    tagInput.focus();
  });
}

function openBatchQuickAddModal(refs) {
  const selectedRefs = (Array.isArray(refs) ? refs : selectedResourceRefs()).map((ref) => ({
    sourcePage: String(ref.sourcePage || ""),
    id: String(ref.id || ""),
  })).filter((ref) => ref.sourcePage && ref.id);
  if (selectedRefs.length < 2) return;

  const groups = [
    { kind: "book", sourcePage: "library", labelKey: "batch.books", fallback: "Books" },
    { kind: "text_novel", sourcePage: "text_novel", labelKey: "batch.novels", fallback: "Text Novels" },
    { kind: "comic", sourcePage: "comic", labelKey: "batch.comics", fallback: "Comics" },
  ].filter((group) => selectedRefs.some((ref) => ref.sourcePage === group.sourcePage));

  openModal((modal, close) => {
    let submitting = false;
    let pendingLoads = groups.length;
    let submit = null;
    const syncSubmitDisabled = () => {
      if (submit) submit.disabled = submitting || pendingLoads > 0;
    };
    const controls = [];
    const selectedCollectionIds = Object.fromEntries(groups.map((group) => [group.kind, new Set()]));
    const queuedCollectionNames = Object.fromEntries(groups.map((group) => [group.kind, []]));
    const collectionRows = Object.fromEntries(groups.map((group) => [group.kind, []]));
    const pendingTags = [];
    const requestClose = () => { if (!submitting) close(); };
    const closeButton = modalHeader(modal, t("batch.title", "Batch Quick Add"), requestClose);
    controls.push(closeButton);
    modal.classList.add("batch-quick-add-modal");
    modal.appendChild(elem(
      "p",
      "small-note",
      fmt(t("batch.selection_count", "{count} items selected"), { count: selectedRefs.length })
    ));

    const tagField = elem("div", "field batch-tag-field");
    tagField.appendChild(elem("label", null, t("batch.tags", "Tags to add")));
    const tagInput = elem("input", "batch-tag-input");
    tagInput.placeholder = t("batch.tag_placeholder", "Type a tag and press Enter...");
    controls.push(tagInput);
    tagField.appendChild(tagInput);
    const tagChips = elem("div", "chip-row batch-pending-tags");
    const recentTags = elem("div", "chip-row recent-tags");
    const renderTagChips = () => {
      clear(tagChips);
      pendingTags.forEach((tag) => {
        const chip = elem("button", "chip chip-btn", `${tag} ×`);
        chip.type = "button";
        chip.disabled = submitting;
        chip.addEventListener("click", () => {
          if (submitting) return;
          const index = pendingTags.indexOf(tag);
          if (index >= 0) pendingTags.splice(index, 1);
          renderTagChips();
        });
        tagChips.appendChild(chip);
      });
    };
    const addPendingTag = (value) => {
      const tag = String(value || "").trim();
      if (!tag || pendingTags.includes(tag)) return;
      pendingTags.push(tag);
      renderTagChips();
    };
    tagInput.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      addPendingTag(tagInput.value);
      tagInput.value = "";
    });
    tagField.appendChild(tagChips);
    tagField.appendChild(elem("div", "kicker mt", t("quick_add.recent_tags", "Recent tags")));
    tagField.appendChild(recentTags);
    modal.appendChild(tagField);
    State.bridge.getTags((json) => {
      clear(recentTags);
      (safeParse(json) || []).slice(0, 12).forEach((tag) => {
        const chip = elem("button", "chip chip-btn", tag);
        chip.type = "button";
        chip.addEventListener("click", () => addPendingTag(tag));
        controls.push(chip);
        recentTags.appendChild(chip);
      });
    });

    modal.appendChild(elem("hr", "modal-divider"));
    const collectionWrap = elem("div", "batch-collection-groups");
    modal.appendChild(collectionWrap);

    groups.forEach((group) => {
      const field = elem("section", "field batch-collection-group");
      field.dataset.kind = group.kind;
      field.appendChild(elem("label", null, t(group.labelKey, group.fallback)));
      const search = elem("input", "batch-collection-search");
      search.dataset.kind = group.kind;
      search.placeholder = t("quick_add.collection_placeholder", "Search collections...");
      controls.push(search);
      field.appendChild(search);
      const queued = elem("div", "chip-row batch-pending-collections");
      const list = elem("div", "list-stack mt batch-collection-list");
      field.appendChild(queued);
      field.appendChild(list);
      collectionWrap.appendChild(field);

      const renderQueuedNames = () => {
        clear(queued);
        queuedCollectionNames[group.kind].forEach((name) => {
          const chip = elem("button", "chip chip-btn", `${name} ×`);
          chip.type = "button";
          chip.disabled = submitting;
          chip.addEventListener("click", () => {
            if (submitting) return;
            const index = queuedCollectionNames[group.kind].indexOf(name);
            if (index >= 0) queuedCollectionNames[group.kind].splice(index, 1);
            renderQueuedNames();
          });
          queued.appendChild(chip);
        });
      };

      const queueCollectionName = (value) => {
        const name = String(value || "").trim();
        if (!name) return;
        const names = queuedCollectionNames[group.kind];
        if (!names.some((current) => current.toLocaleLowerCase() === name.toLocaleLowerCase())) {
          names.push(name);
        }
        search.value = "";
        renderQueuedNames();
        renderRows();
      };

      const renderRows = () => {
        clear(list);
        const query = String(search.value || "").trim().toLocaleLowerCase();
        if (query) {
          const create = elem(
            "button",
            "list-item list-item-action quick-create-row",
            fmt(t("quick_add.create_and_add", "Create and add “{name}”"), { name: search.value.trim() })
          );
          create.type = "button";
          create.disabled = submitting;
          create.addEventListener("click", () => queueCollectionName(search.value));
          list.appendChild(create);
        }
        collectionRows[group.kind]
          .filter((collection) => !query || String(collection.name || "").toLocaleLowerCase().includes(query))
          .forEach((collection) => {
            const collectionId = Number(collection.id);
            const selected = selectedCollectionIds[group.kind].has(collectionId);
            const button = elem(
              "button",
              selected ? "list-item list-item-action batch-collection-option selected" : "list-item list-item-action batch-collection-option",
              String(collection.name || "")
            );
            button.type = "button";
            button.dataset.collectionId = String(collectionId);
            button.setAttribute("aria-pressed", selected ? "true" : "false");
            button.disabled = submitting;
            button.addEventListener("click", () => {
              if (submitting) return;
              if (selectedCollectionIds[group.kind].has(collectionId)) {
                selectedCollectionIds[group.kind].delete(collectionId);
              } else {
                selectedCollectionIds[group.kind].add(collectionId);
              }
              renderRows();
            });
            list.appendChild(button);
          });
      };

      search.addEventListener("input", renderRows);
      search.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") return;
        event.preventDefault();
        queueCollectionName(search.value);
      });
      State.bridge.getCollections(group.sourcePage, (json) => {
        collectionRows[group.kind] = safeParse(json) || [];
        pendingLoads = Math.max(0, pendingLoads - 1);
        renderRows();
        syncSubmitDisabled();
      });
    });

    const actions = elem("div", "modal-actions");
    const cancel = elem("button", "ghost-btn", t("common.cancel", "Cancel"));
    cancel.addEventListener("click", requestClose);
    submit = elem("button", "primary-btn batch-submit", t("batch.confirm", "Add to selected items"));
    controls.push(cancel, submit);
    const setSubmitting = (value) => {
      submitting = value;
      modal.dataset.submitting = value ? "true" : "false";
      controls.forEach((control) => { control.disabled = value; });
      syncSubmitDisabled();
    };

    submit.addEventListener("click", () => {
      if (submitting || pendingLoads > 0) return;
      const collections = {};
      groups.forEach((group) => {
        collections[group.kind] = {
          addIds: [...selectedCollectionIds[group.kind]].sort((a, b) => a - b),
          createNames: queuedCollectionNames[group.kind].slice(),
        };
      });
      const hasCollectionTarget = Object.values(collections).some((config) => (
        config.addIds.length || config.createNames.length
      ));
      if (!pendingTags.length && !hasCollectionTarget) {
        showToast(
          t("batch.no_targets_title", "Nothing to add"),
          t("batch.no_targets", "Choose at least one collection or tag."),
          "warning"
        );
        return;
      }
      const payload = {
        resources: selectedRefs.map((ref) => ({ sourcePage: ref.sourcePage, resourceId: ref.id })),
        collections,
        tags: pendingTags.slice(),
      };
      setSubmitting(true);
      State.bridge.applyBatchQuickAdd(JSON.stringify(payload), (json) => {
        const result = safeParse(json);
        if (!result || !result.ok) {
          setSubmitting(false);
          showToast(
            t("batch.save_failed_title", "Batch update failed"),
            t("batch.save_failed", "No changes were saved. Please try again."),
            "warning"
          );
          return;
        }
        Object.entries(result.sourcePages || {}).forEach(([page, data]) => {
          State.pages[page] = data;
        });
        Object.entries(result.collectionPages || {}).forEach(([page, data]) => {
          State.pages[page] = data;
        });
        if (result.tagCatalogInvalidated) {
          State.tagRequestId += 1;
          State.tagCatalog = null;
        }
        if (State.tagDetail && Array.isArray(State.tagDetail.items)) {
          const tagsByResource = new Map((result.resourceTags || []).map((entry) => [
            resourceSelectionKey({ sourcePage: entry.sourcePage, id: entry.resourceId }),
            Array.isArray(entry.tags) ? entry.tags : [],
          ]));
          State.tagDetail.items.forEach((item) => {
            const key = resourceSelectionKey({ sourcePage: item.sourcePage, id: item.id });
            if (tagsByResource.has(key)) item.tags = tagsByResource.get(key).slice();
          });
        }
        close();
        clearResourceSelection();
        syncResourceSelectionNodes();
        renderDetailEmpty();
        showToast(
          t("batch.saved_title", "Batch update complete"),
          fmt(t("batch.saved", "Updated {count} items."), { count: Number(result.summary && result.summary.resourceCount || selectedRefs.length) }),
          "success"
        );
      });
    });
    actions.appendChild(cancel);
    actions.appendChild(submit);
    modal.appendChild(actions);
    syncSubmitDisabled();
    tagInput.focus();
  });
}

/* ---------- settings ---------- */
const SETTINGS_SECTIONS = [
  ["general", "settings.nav.general"],
  ["appearance", "settings.nav.appearance"],
  ["shortcuts", "settings.nav.shortcuts"],
  ["paths", "settings.nav.paths"],
  ["errors", "settings.nav.errors"],
];

function renderSettings() {
  $("pageTitle").textContent = t("settings.title", "Settings");
  $("pageSubtitle").textContent = "";
  clear($("pageHeadTools"));
  $("viewModeToggle").style.display = "none";
  const area = $("contentArea");
  teardownVirtualWindow(area);
  clear(area);
  area.classList.remove("view-enter"); void area.offsetWidth; area.classList.add("view-enter");

  const grid = elem("div", "settings-grid");
  grid.style.userSelect = "text";
  const nav = elem("div", "settings-nav");
  const panel = elem("div");
  panel.style.minWidth = "0";
  if (!State._settingsSection) State._settingsSection = "general";
  else if (State._settingsSection === "tasks") State._settingsSection = "paths";
  SETTINGS_SECTIONS.forEach(([id, key]) => {
    const btn = elem("button", State._settingsSection === id ? "active" : null, t(key));
    btn.addEventListener("click", () => {
      if (id !== "shortcuts") State.shortcutCaptureAction = "";
      State._settingsSection = id;
      renderSettings();
    });
    nav.appendChild(btn);
  });
  grid.appendChild(nav);
  grid.appendChild(panel);
  area.appendChild(grid);

  const section = State._settingsSection;
  if (section === "general") renderSettingsGeneral(panel);
  else if (section === "appearance") renderSettingsAppearance(panel);
  else if (section === "shortcuts") renderSettingsShortcuts(panel);
  else if (section === "paths") {
    renderSettingsPaths(panel);
    renderSettingsTasks(panel);
  }
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

function setTagManagerScope(scope, checked) {
  const current = Object.assign(
    { library: true, text_novel: true, comic: true },
    State.settings.tagManagerScopes || {}
  );
  if (!(scope in current)) return false;
  const next = Object.assign({}, current, { [scope]: Boolean(checked) });
  if (!Object.values(next).some(Boolean)) {
    showToast(
      t("tags.scope.title", "Tag Manager Sources"),
      t("tags.scope.required", "Keep at least one resource type selected."),
      "warning"
    );
    return false;
  }
  State.bridge.setTagManagerScopes(JSON.stringify(next), (json) => {
    const result = safeParse(json);
    if (!result || !result.ok) {
      showToast(
        t("tags.scope.title", "Tag Manager Sources"),
        t("tags.scope.required", "Keep at least one resource type selected."),
        "warning"
      );
      if (State.currentPage === "settings") renderSettings();
      return;
    }
    State.settings.tagManagerScopes = result.scopes;
    invalidateTagManager(true);
    if (State.currentPage === TAG_MANAGER_PAGE) loadCurrentTagPage();
  });
  return true;
}

function tagScopeField(labelKey, scope, checked) {
  const field = elem("div", "field field-inline");
  const label = elem("label", null, t(labelKey));
  label.style.marginBottom = "0";
  const sw = elem("label", "switch");
  const input = elem("input");
  input.type = "checkbox";
  input.checked = Boolean(checked);
  input.addEventListener("change", () => {
    if (!setTagManagerScope(scope, input.checked)) input.checked = !input.checked;
  });
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

const SHORTCUT_DISPLAY_CODES = {
  MouseBack: "shortcut.input.mouse_back",
  MouseForward: "shortcut.input.mouse_forward",
  ArrowUp: "↑",
  ArrowDown: "↓",
  ArrowLeft: "←",
  ArrowRight: "→",
  Backspace: "Backspace",
  PageUp: "Page Up",
  PageDown: "Page Down",
  NumpadAdd: "Num +",
  NumpadSubtract: "Num −",
  NumpadMultiply: "Num ×",
  NumpadDivide: "Num ÷",
  NumpadDecimal: "Num .",
};

function shortcutCodeLabel(code) {
  if (SHORTCUT_DISPLAY_CODES[code]) {
    const label = SHORTCUT_DISPLAY_CODES[code];
    return label.startsWith("shortcut.") ? t(label, code) : label;
  }
  if (/^Key[A-Z]$/.test(code)) return code.slice(3);
  if (/^Digit[0-9]$/.test(code)) return code.slice(5);
  if (/^Numpad[0-9]$/.test(code)) return `Num ${code.slice(6)}`;
  return code;
}

function shortcutDisplayLabel(inputToken) {
  const token = String(inputToken || "");
  if (!token) return t("shortcut.unassigned", "Not assigned");
  if (SHORTCUT_MOUSE_TOKENS.has(token)) return shortcutCodeLabel(token);
  const parts = token.split("+");
  const code = parts.pop() || "";
  return [...parts, shortcutCodeLabel(code)].join(" + ");
}

function buildShortcutRow(actionId) {
  const action = SHORTCUT_ACTIONS[actionId];
  const token = shortcutBindings()[actionId] || "";
  const capturing = State.shortcutCaptureAction === actionId;
  const row = elem("div", `shortcut-row${capturing ? " is-capturing" : ""}`);
  row.dataset.actionId = actionId;
  row.appendChild(elem("div", "shortcut-action-label", t(action.labelKey, actionId)));

  const binding = elem("button", "shortcut-binding-btn");
  binding.type = "button";
  binding.setAttribute("aria-pressed", capturing ? "true" : "false");
  binding.setAttribute("aria-label", fmt(
    t("shortcut.capture_aria", "Set shortcut for {action}"),
    { action: t(action.labelKey, actionId) }
  ));
  binding.appendChild(elem(
    "span",
    `shortcut-keycap${token ? "" : " is-empty"}`,
    capturing ? t("shortcut.capture", "Press a key or mouse side button…") : shortcutDisplayLabel(token)
  ));
  binding.addEventListener("click", () => beginShortcutCapture(actionId));
  row.appendChild(binding);

  const clearButton = elem("button", "ghost-btn shortcut-clear-btn", t("shortcut.clear", "Clear"));
  clearButton.type = "button";
  clearButton.disabled = !token;
  clearButton.addEventListener("click", () => clearShortcutBinding(actionId));
  row.appendChild(clearButton);
  return row;
}

function buildShortcutGroup(titleKey, actionIds) {
  const card = settingCard(t(titleKey));
  const list = elem("div", "shortcut-list");
  actionIds.forEach((actionId) => list.appendChild(buildShortcutRow(actionId)));
  card.appendChild(list);
  return card;
}

function renderSettingsShortcuts(panel) {
  const intro = settingCard(t("settings.nav.shortcuts", "Shortcuts"));
  intro.appendChild(elem("p", "small-note", t(
    "shortcut.scope_hint",
    "Shortcuts work only while this app is focused. Reserved system, zoom, and accessibility keys cannot be assigned."
  )));
  intro.appendChild(elem("p", "small-note", t(
    "shortcut.capture_hint",
    "Choose a binding field, then press a key combination or a mouse side button. Press Escape to cancel."
  )));
  panel.appendChild(intro);
  panel.appendChild(buildShortcutGroup("shortcut.section.navigation", [
    "reopen_recent_collection",
    "exit_collection",
  ]));
  panel.appendChild(buildShortcutGroup("shortcut.section.resource", [
    "open_resource",
    "open_folder",
    "quick_add",
    "edit_cover",
    "remove_from_collection",
    "remove_from_library",
  ]));
}

function renderSettingsGeneral(panel) {
  const s = State.settings;
  const card = settingCard(t("settings.nav.general", "General"));
  const grid = elem("div", "form-grid");
  grid.appendChild(selectField("settings.language", "language", [["en", "English"], ["zh-cn", "简体中文"]], s.language));
  grid.appendChild(selectField("settings.search_font", "searchFontSize", [[12,"12"],[15,"15"],[18,"18"],[20,"20"]], s.searchFontSize));
  grid.appendChild(selectField("settings.scan_depth", "scanDepth", [[1,"1"],[2,"2"],[3,"3"]], s.scanDepth));
  const hashField = selectField("settings.hash", "hashStrategy", [["size_mtime", t("settings.hash.fast", "Fast")], ["sha256", t("settings.hash.strict", "Strict")], ["quick", t("settings.hash.quick", "Quick")]], s.hashStrategy);
  const hashHint = elem("p", "small-note", t("settings.hash.hint", "Fast may miss content changes; use Quick or Strict for important libraries."));
  hashHint.style.margin = "6px 0 0";
  hashField.appendChild(hashHint);
  grid.appendChild(hashField);
  grid.appendChild(selectField("settings.comic_scan_strategy", "comicScanStrategy", [
    ["snapshot", t("settings.comic_scan_strategy.snapshot", "Directory snapshot (fast)")],
    ["full", t("settings.comic_scan_strategy.full", "Full rescan each time (strict)")],
  ], s.comicScanStrategy || "snapshot"));
  grid.appendChild(selectField("settings.comic_title_conflict", "comicTitleConflictPolicy", [
    ["skip_incoming", t("settings.comic_title_conflict.skip_incoming", "Skip incoming")],
    ["keep_both", t("settings.comic_title_conflict.keep_both", "Keep both")],
    ["prefer_newer", t("settings.comic_title_conflict.prefer_newer", "Prefer newer")],
  ], s.comicTitleConflictPolicy || "skip_incoming"));
  grid.appendChild(selectField("settings.text_encoding_preference", "textEncodingPreference", [
    ["simplified", t("settings.text_encoding.simplified", "Simplified first")],
    ["traditional", t("settings.text_encoding.traditional", "Traditional first")],
    ["auto", t("settings.text_encoding.auto", "Auto")],
  ], s.textEncodingPreference || "simplified"));
  grid.appendChild(selectField("settings.card_spacing", "cardSpacing", [[10,"10"],[14,"14"],[18,"18"],[22,"22"]], s.cardSpacing));
  grid.appendChild(selectField("settings.text_preview_chars", "textPreviewChars", [[500,"500"],[1000,"1000"],[2000,"2000"]], s.textPreviewChars));
  grid.appendChild(selectField("settings.comic_view_mode", "comicViewMode", [["waterfall", t("settings.comic_view_waterfall", "Waterfall")],["pagination", t("settings.comic_view_pagination", "Pagination")]], s.comicViewMode));
  grid.appendChild(selectField("settings.comic_page_size", "comicPageSize", [[24,"24"],[48,"48"],[72,"72"],[96,"96"]], s.comicPageSize));
  grid.appendChild(selectField("settings.viewport_buffer_screens", "viewportBufferScreens", [[3,"3"],[4,"4"],[5,"5"],[6,"6"]], s.viewportBufferScreens ?? 3));
  grid.appendChild(selectField("settings.grid_columns", "gridColumns", [[4,"4"],[5,"5"],[6,"6"],[7,"7"],[8,"8"],[10,"10"],[12,"12"]], s.gridColumns ?? 6));
  grid.appendChild(selectField("settings.recommendation_items_per_category", "recommendationItemsPerCategory", [[3,"3"],[6,"6"],[9,"9"],[12,"12"]], s.recommendationItemsPerCategory ?? 6));
  grid.appendChild(selectField("settings.recommendation_columns_per_category", "recommendationColumnsPerCategory", [[1,"1"],[2,"2"],[3,"3"]], s.recommendationColumnsPerCategory ?? 2));
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
  const tagCard = settingCard(t("tags.scope.title", "Tag Manager Sources"));
  tagCard.appendChild(elem("p", "small-note", t(
    "tags.scope.required",
    "Keep at least one resource type selected."
  )));
  const tagScopes = Object.assign(
    { library: true, text_novel: true, comic: true },
    s.tagManagerScopes || {}
  );
  const tagGrid = elem("div", "form-grid");
  tagGrid.appendChild(tagScopeField("tags.scope.library", "library", tagScopes.library));
  tagGrid.appendChild(tagScopeField("tags.scope.text_novel", "text_novel", tagScopes.text_novel));
  tagGrid.appendChild(tagScopeField("tags.scope.comic", "comic", tagScopes.comic));
  tagCard.appendChild(tagGrid);
  panel.appendChild(tagCard);
  renderSettingsAbout(panel);
}

function renderSettingsAbout(panel) {
  const s = State.settings;
  const card = settingCard(t("settings.about.title", "About"));
  card.appendChild(elem("p", "small-note", fmt(
    t("settings.about.version", "Current version: {version}"),
    { version: String(s.appVersion || "—") }
  )));
  const actions = elem("div", "detail-actions");
  actions.style.marginTop = "10px";
  const checkBtn = elem("button", "ghost-btn", t("settings.about.check_update", "Check for updates"));
  checkBtn.setAttribute("data-update-check-btn", "1");
  checkBtn.addEventListener("click", () => {
    if (checkBtn.disabled) return;
    State._updateCheckBtn = checkBtn;
    checkBtn.disabled = true;
    checkBtn.textContent = t("settings.about.checking", "Checking…");
    State.bridge.checkForUpdates();
  });
  actions.appendChild(checkBtn);
  card.appendChild(actions);
  panel.appendChild(card);
}

function resetUpdateCheckButton() {
  const btn = State._updateCheckBtn || document.querySelector("[data-update-check-btn]");
  if (!btn) return;
  btn.disabled = false;
  btn.textContent = t("settings.about.check_update", "Check for updates");
  State._updateCheckBtn = null;
}

function openUpdateModal(data) {
  openModal((modal, close) => {
    modalHeader(modal, t("settings.about.update_available", "Update available"), close);
    modal.appendChild(elem("p", "small-note", fmt(
      t("settings.about.update_msg", "A new version {latestVersion} is available.\nYou are on {currentVersion}."),
      {
        latestVersion: String(data.latestVersion || ""),
        currentVersion: String(data.currentVersion || ""),
      }
    )));
    const actions = elem("div", "modal-actions");
    const later = elem("button", "ghost-btn", t("settings.about.later", "Later"));
    later.addEventListener("click", close);
    const go = elem("button", "primary-btn", t("settings.about.go_github", "Go to GitHub"));
    go.addEventListener("click", () => {
      if (data.url) State.bridge.openExternalUrl(String(data.url));
      close();
    });
    actions.appendChild(later);
    actions.appendChild(go);
    modal.appendChild(actions);
  });
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

  const skinCard = settingCard(t("settings.ui_skin.title", "UI Style"));
  skinCard.appendChild(elem("p", "small-note", t("settings.ui_skin.restart_hint", "Please restart the app to apply the new UI style.")));
  const skinSeg = elem("div", "segmented");
  [["glass", "settings.ui_skin.glass"], ["vaporwave", "settings.ui_skin.vaporwave"]].forEach(([skin, key]) => {
    const btn = elem("button", State.uiSkin === skin ? "active" : null, t(key));
    btn.addEventListener("click", () => { if (State.uiSkin !== skin) setUiSkin(skin); });
    skinSeg.appendChild(btn);
  });
  const skinWrap = elem("div", "field");
  skinWrap.appendChild(elem("label", null, t("settings.ui_skin.title", "UI Style")));
  skinWrap.appendChild(skinSeg);
  skinCard.appendChild(skinWrap);
  panel.appendChild(skinCard);

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
  panel.appendChild(buildPreviewCacheCard());
  const strategyCard = settingCard(null);
  strategyCard.appendChild(switchField("settings.per_root_strategy", "perRootScanStrategyEnabled", s.perRootScanStrategyEnabled));
  const strategyHint = elem("p", "small-note", t("settings.per_root_strategy.hint", "When enabled, set a scan strategy for each root; when disabled, global strategies apply (saved overrides are kept)."));
  strategyHint.style.margin = "6px 0 0";
  strategyCard.appendChild(strategyHint);
  panel.appendChild(strategyCard);
  panel.appendChild(buildRootCard(
    t("settings.roots.library", "Library roots"),
    "library",
    normalizeRootList(s.libraryRoots),
    false,
    true
  ));
  panel.appendChild(buildRootCard(
    t("settings.roots.comic", "Comic roots"),
    "comic",
    normalizeRootList(s.comicRoots),
    false,
    true
  ));
  panel.appendChild(buildRootCard(
    t("settings.roots.text", "Text novel roots"),
    "text",
    normalizeRootList(s.textRoots),
    true,
    true
  ));
}

function normalizeRootList(roots) {
  return (roots || []).map((item) => {
    if (item && typeof item === "object") {
      return {
        path: String(item.path || ""),
        scan_strategy: item.scan_strategy || "",
      };
    }
    return { path: String(item), scan_strategy: "" };
  });
}

function buildPreviewCacheCard() {
  const s = State.settings;
  const card = settingCard(t("settings.cache.title", "Thumbnail cache folder"));
  card.appendChild(elem("p", "small-note", t(
    "settings.cache.hint",
    "Covers are stored here. Default is the project img_preview folder. Changing location can migrate files or only update the index."
  )));
  const pathRow = elem("div", "path-row");
  const effective = String(s.previewCacheDirEffective || s.previewCacheDirDefault || "");
  const pathLabel = elem("span", "path-text", effective);
  if (s.previewCacheDirIsDefault) {
    pathLabel.textContent = effective + " " + t("settings.cache.default_note", "(using default)");
  }
  pathRow.appendChild(pathLabel);
  card.appendChild(pathRow);
  const actions = elem("div", "modal-actions");
  actions.style.justifyContent = "flex-start";
  actions.style.marginTop = "10px";
  const changeBtn = elem("button", "ghost-btn", t("settings.cache.change", "Change…"));
  changeBtn.addEventListener("click", () => {
    State.bridge.browsePreviewCacheDir((chosen) => {
      const path = String(chosen || "");
      if (!path) return;
      openPreviewCacheConfirmModal(path);
    });
  });
  const resetBtn = elem("button", "ghost-btn", t("settings.cache.reset", "Use default"));
  resetBtn.addEventListener("click", () => openPreviewCacheConfirmModal(""));
  resetBtn.disabled = !!s.previewCacheDirIsDefault;
  actions.appendChild(changeBtn);
  actions.appendChild(resetBtn);
  card.appendChild(actions);
  return card;
}

function openPreviewCacheConfirmModal(newPath) {
  const s = State.settings;
  const oldPath = String(s.previewCacheDirEffective || "");
  const defaultPath = String(s.previewCacheDirDefault || "");
  const targetPath = String(newPath || "");
  const displayNew = targetPath || defaultPath;
  if (targetPath && oldPath && targetPath.replace(/[\\/]+$/, "").toLowerCase() === oldPath.replace(/[\\/]+$/, "").toLowerCase()) {
    showToast(t("settings.cache.confirm_title", "Change cache folder"), t("settings.cache.same_path", "That folder is already in use."), "warning");
    return;
  }
  openModal((modal, close) => {
    modalHeader(modal, t("settings.cache.confirm_title", "Change cache folder"), close);
    modal.appendChild(elem("p", "small-note", fmt(t("settings.cache.confirm_from", "From:\n{old}"), { old: oldPath })));
    modal.appendChild(elem("p", "small-note", fmt(t("settings.cache.confirm_to", "To:\n{new}"), { new: displayNew + (targetPath ? "" : " " + t("settings.cache.default_note", "(using default)")) })));
    modal.appendChild(elem("p", "small-note", t(
      "settings.cache.confirm_structure",
      "If you move files yourself, keep subfolders: book|comic|text_novel / original|compressed."
    )));
    const actions = elem("div", "modal-actions");
    actions.style.flexWrap = "wrap";
    const cancel = elem("button", "ghost-btn", t("common.cancel", "Cancel"));
    cancel.addEventListener("click", close);
    const migrate = elem("button", "primary-btn", t("settings.cache.mode.migrate", "Migrate automatically (copy + update index)"));
    migrate.addEventListener("click", () => {
      State.bridge.setPreviewCacheDir(targetPath, "migrate");
      close();
    });
    const rewire = elem("button", "ghost-btn", t("settings.cache.mode.rewire", "I already moved files (update index only)"));
    rewire.addEventListener("click", () => {
      State.bridge.setPreviewCacheDir(targetPath, "rewire_only");
      close();
    });
    const switchOnly = elem("button", "ghost-btn", t("settings.cache.mode.switch", "Switch only (rebuild thumbnails later)"));
    switchOnly.addEventListener("click", () => {
      State.bridge.setPreviewCacheDir(targetPath, "switch_only");
      close();
    });
    actions.appendChild(cancel);
    actions.appendChild(migrate);
    actions.appendChild(rewire);
    actions.appendChild(switchOnly);
    modal.appendChild(actions);
  });
}

function rootScanStrategyShortLabel(kind, strategy) {
  const value = strategy || "";
  if (!value) return t("settings.scan_strategy.inherit", "Inherit global");
  if (kind === "comic") {
    if (value === "snapshot") return t("settings.comic_scan_strategy.snapshot", "Directory snapshot (fast)");
    if (value === "full") return t("settings.comic_scan_strategy.full", "Full rescan each time (strict)");
    return value;
  }
  if (value === "size_mtime") return t("settings.hash.fast", "Fast");
  if (value === "quick") return t("settings.hash.quick", "Quick");
  if (value === "sha256") return t("settings.hash.strict", "Strict");
  return value;
}

function buildRootCard(title, kind, roots, withRules, withStrategy) {
  const s = State.settings;
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
    if (withStrategy && s.perRootScanStrategyEnabled) {
      const shortLabel = rootScanStrategyShortLabel(kind, root.scan_strategy);
      const strategyBtn = elem("button", "ghost-btn", `${t("settings.roots.scan_strategy", "Scan strategy")} · ${shortLabel}`);
      strategyBtn.title = t("settings.roots.scan_strategy_hint", "Choose a scan strategy for this directory");
      strategyBtn.addEventListener("click", () => openRootScanStrategyModal(kind, root.path, root.scan_strategy || ""));
      row.appendChild(strategyBtn);
    }
    if (withRules) {
      const rules = elem("button", "ghost-btn", t("settings.roots.rules", "Rules"));
      rules.title = t("settings.roots.rules_hint", "Open Text Rules editor for this folder");
      rules.addEventListener("click", () => State.bridge.openTextRules(root.path));
      row.appendChild(rules);
    }
    row.appendChild(elem("span", "path-text", root.path));
    list.appendChild(row);
  });
  card.appendChild(list);
  return card;
}

function openRootScanStrategyModal(kind, path, current) {
  const options = kind === "comic"
    ? [
      ["", t("settings.scan_strategy.inherit", "Inherit global")],
      ["snapshot", t("settings.comic_scan_strategy.snapshot", "Directory snapshot (fast)")],
      ["full", t("settings.comic_scan_strategy.full", "Full rescan each time (strict)")],
    ]
    : [
      ["", t("settings.scan_strategy.inherit", "Inherit global")],
      ["size_mtime", t("settings.hash.fast", "Fast")],
      ["quick", t("settings.hash.quick", "Quick")],
      ["sha256", t("settings.hash.strict", "Strict")],
    ];
  openModal((modal, close) => {
    modalHeader(modal, t("settings.roots.scan_strategy.title", "Directory scan strategy"), close);
    modal.appendChild(elem("p", "small-note", path));
    modal.appendChild(elem("p", "small-note", t("settings.roots.scan_strategy_hint", "Choose a scan strategy for this directory")));
    const field = elem("div", "field");
    field.appendChild(elem("label", null, t("settings.roots.scan_strategy", "Scan strategy")));
    const sel = elem("select");
    options.forEach(([value, label]) => {
      const opt = elem("option", null, label);
      opt.value = value;
      if (String(value) === String(current || "")) opt.selected = true;
      sel.appendChild(opt);
    });
    field.appendChild(sel);
    modal.appendChild(field);
    const actions = elem("div", "modal-actions");
    const cancel = elem("button", "ghost-btn", t("common.cancel", "Cancel"));
    cancel.addEventListener("click", close);
    const confirm = elem("button", "primary-btn", t("common.confirm", "Confirm"));
    confirm.addEventListener("click", () => {
      State.bridge.setRootScanStrategy(kind, path, sel.value);
      close();
    });
    actions.appendChild(cancel);
    actions.appendChild(confirm);
    modal.appendChild(actions);
  });
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
  const ignored = report.ignored_unsupported_count ?? report.ignored_unsupported ?? 0;
  const textScanned = report.text_scanned_count ?? report.text_scanned_files ?? 0;
  const downscaled = report.comic_thumbnail_downscaled_count ?? report.comic_large_image_downscaled_count ?? 0;
  const addedTotal =
    Number(report.added_count || 0) +
    Number(report.text_added_count || 0) +
    Number(report.comic_added_count || 0);
  let text = fmt(t("settings.scan_summary_template", "Last scan: {updated_at}\nScope: {scope} | Added: {added} | Ignored unsupported: {ignored} | Name conflicts: {conflicts}\nRemoved missing: {removed_total} (library/text: {removed_books}, comic: {removed_comics})"), {
    updated_at: report.updated_at || report.finished_at || "—",
    scope: report.scope || report.trigger || "—",
    added: addedTotal,
    ignored,
    conflicts: Array.isArray(report.name_conflicts) ? report.name_conflicts.length : (report.name_conflict_count || 0),
    removed_total: report.removed_missing_count || 0,
    removed_books: report.removed_missing_book_count || 0,
    removed_comics: report.removed_missing_comic_count || 0,
  });
  if (Number(report.skipped_unchanged_count || 0) > 0) {
    text += fmt(t("settings.scan_summary_skipped", "\nLibrary unchanged skipped: {skipped}"), {
      skipped: report.skipped_unchanged_count || 0,
    });
  }
  text += fmt(t("settings.text.scan_summary", "\nText Novel - scanned:{scanned} added:{added} updated:{updated}"), {
    scanned: textScanned,
    added: report.text_added_count || 0,
    updated: report.text_updated_count || 0,
  });
  text += fmt(t("settings.comic.scan_perf_summary", "\nComic - added:{added} updated:{updated} placeholders:{copied} thumbs queued:{queued} workers:{workers} downscaled:{downscaled}"), {
    added: report.comic_added_count || 0,
    updated: report.comic_updated_count || 0,
    copied: report.comic_placeholder_copied_count || 0,
    queued: report.comic_thumbnail_enqueued_count || 0,
    workers: report.comic_thumbnail_workers_used || "—",
    downscaled,
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
    btn.setAttribute("data-library-task-btn", "scan");
    btn.disabled = !!State._scanRunning;
    btn.addEventListener("click", () => State.bridge.startScan(scope));
    scanRow.appendChild(btn);
  });
  card.appendChild(scanRow);

  const thumbRow = elem("div", "detail-actions");
  [["cleanup","library","settings.tasks.cleanup_library"],["regenerate","library","settings.tasks.regen_library"],
   ["cleanup","text_novel","settings.tasks.cleanup_text"],["regenerate","text_novel","settings.tasks.regen_text"],
   ["cleanup","comic","settings.tasks.cleanup_comic"],["regenerate","comic","settings.tasks.regen_comic"]].forEach(([kind, scope, key]) => {
    const btn = elem("button", "ghost-btn", t(key));
    btn.setAttribute("data-library-task-btn", "thumb");
    btn.disabled = !!State._scanRunning;
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

/* ---------- ui skin ---------- */
function normalizeUiSkin(skin) {
  return skin === "vaporwave" ? "vaporwave" : "glass";
}

function loadSkinStylesheets(skin) {
  const normalized = normalizeUiSkin(skin);
  document.querySelectorAll("link[data-skin-link]").forEach((node) => node.remove());
  SKIN_STYLESHEETS[normalized].forEach((href) => {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    link.setAttribute("data-skin-link", "");
    document.head.appendChild(link);
  });
}

function toggleVaporwaveScene(enabled) {
  const mount = document.getElementById("vwSceneMount");
  if (!mount) return;
  clear(mount);
  mount.hidden = !enabled;
  if (!enabled) return;
  const scene = document.createElement("div");
  scene.className = "vw-scene";
  scene.setAttribute("aria-hidden", "true");
  scene.innerHTML = `<div class="vw-atmosphere"></div><div class="vw-scanlines"></div>`;
  mount.appendChild(scene);
}

function applyUiSkin(skin) {
  const normalized = normalizeUiSkin(skin);
  State.uiSkin = normalized;
  document.body.dataset.uiSkin = normalized;
  loadSkinStylesheets(normalized);
  toggleVaporwaveScene(normalized === "vaporwave");
}

function setUiSkin(skin) {
  const normalized = normalizeUiSkin(skin);
  if (normalized === State.uiSkin || !State.bridge) return;
  State.bridge.setUiSkin(normalized);
  State.uiSkin = normalized;
  if (State.settings) State.settings.uiSkin = normalized;
  if (State.currentPage === "settings") renderSettings();
  showToast(
    t("toast.ui_skin_restart_required", "Restart required"),
    t("settings.ui_skin.restart_hint", "Please restart the app to apply the new UI style."),
    "info"
  );
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
  try {
    if (State.bridge && State.bridge.setPageBackground) {
      State.bridge.setPageBackground(State.uiSkin, theme === "night" ? "night" : "day");
    } else if (State.bridge && State.bridge.setPageBackgroundTheme) {
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
    saveSearchQueryForPage(State.currentPage, input.value);
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
      setViewModeForPage(State.currentPage, btn.dataset.mode);
    });
  });
}

function searchContext() {
  const page = State.currentPage;
  if (page === "text_novel") return "text_novel";
  if (page === "comic") return "comic";
  if (page === "comic_collections" && isComicCollectionDetail()) return "comic_collections";
  return "library";
}

function commitSearch() {
  const ctx = searchContext();
  if (!isSearchablePage(State.currentPage)) return;
  State.bridge.search(ctx, State.searchQuery, (json) => {
    const data = safeParse(json);
    if (!data) return;
    clearResourceSelection();
    renderDetailEmpty();
    State.pages[ctx] = data;
    if (State.currentPage === ctx) scheduleRenderPage();
  });
}

function updateSuggestions() {
  const query = $("searchInput").value;
  if (State.currentPage === "settings" || (COLLECTION_PAGES.has(State.currentPage) && !isComicCollectionDetail())) { closeSuggestions(); return; }
  if (!isSearchablePage(State.currentPage)) { closeSuggestions(); return; }
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
        saveSearchQueryForPage(State.currentPage, s.query_value);
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
document.addEventListener("pointerdown", handleShortcutSideButton, true);
document.addEventListener("mousedown", handleShortcutSideButton, true);
document.addEventListener("mouseup", handleShortcutSideButton, true);
document.addEventListener("auxclick", handleShortcutSideButton, true);
document.addEventListener("DOMContentLoaded", () => {
  initTopbar();
  initChannel();
});
document.addEventListener("keydown", handleShortcutKeydown, true);
