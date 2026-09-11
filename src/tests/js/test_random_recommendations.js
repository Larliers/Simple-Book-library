"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const appPath = process.argv[2];
if (!appPath) throw new Error("app.js path is required");

class FakeClassList {
  constructor() { this.values = new Set(); }
  add(...names) { names.forEach((name) => this.values.add(name)); }
  remove(...names) { names.forEach((name) => this.values.delete(name)); }
  contains(name) { return this.values.has(name); }
  toggle(name, force) {
    const enabled = force === undefined ? !this.values.has(name) : Boolean(force);
    if (enabled) this.values.add(name); else this.values.delete(name);
    return enabled;
  }
}

class FakeNode {
  constructor(tagName = "div") {
    this.tagName = tagName.toUpperCase();
    this.children = [];
    this.parentElement = null;
    this.listeners = {};
    this.classList = new FakeClassList();
    this.style = {};
    this.dataset = {};
    this.attributes = {};
    this.textContent = "";
    this.value = "";
    this.disabled = false;
    this.offsetWidth = 160;
    this.offsetHeight = 120;
    this.clientWidth = 800;
    this.clientHeight = 600;
    this.scrollTop = 0;
  }
  get firstChild() { return this.children[0] || null; }
  appendChild(child) {
    child.parentElement = this;
    this.children.push(child);
    return child;
  }
  removeChild(child) {
    this.children.splice(this.children.indexOf(child), 1);
    child.parentElement = null;
  }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  removeEventListener(name) { delete this.listeners[name]; }
  dispatch(name, event = {}) {
    if (this.listeners[name]) this.listeners[name](Object.assign({ preventDefault() {} }, event));
  }
  querySelectorAll(selector) {
    const result = [];
    const visit = (node) => {
      if (selector === ".selected" && node.classList.contains("selected")) result.push(node);
      node.children.forEach(visit);
    };
    this.children.forEach(visit);
    return result;
  }
  contains(target) {
    if (target === this) return true;
    return this.children.some((child) => child.contains(target));
  }
}

const nodes = {
  searchInput: new FakeNode("input"),
  suggestions: new FakeNode(),
  contentArea: new FakeNode("main"),
  detailEmpty: new FakeNode(),
  detailContent: new FakeNode(),
  contextMenu: new FakeNode(),
};

const observerStats = { created: 0, disconnected: 0 };

const document = {
  createElement: (tag) => new FakeNode(tag),
  createDocumentFragment: () => new FakeNode("fragment"),
  getElementById: (id) => nodes[id] || null,
  addEventListener() {},
  querySelectorAll() { return []; },
};

const context = {
  assert,
  console,
  document,
  window: { innerWidth: 1400, innerHeight: 860 },
  observerStats,
  ResizeObserver: class {
    constructor() { observerStats.created += 1; }
    observe() {}
    disconnect() { observerStats.disconnected += 1; }
  },
  requestAnimationFrame: (callback) => { callback(); return 1; },
  cancelAnimationFrame() {},
  setTimeout: () => 1,
  clearTimeout() {},
  getComputedStyle: () => ({ paddingLeft: "0", paddingRight: "0" }),
};
vm.createContext(context);

const assertions = `
let scheduledRenders = 0;
scheduleRenderPage = () => { scheduledRenders += 1; };
renderDetailEmpty = () => {};
renderSettings = () => {};
wireTextRulesSignal = () => {};

assert.deepStrictEqual(recommendationLayoutForWidth(620, 2), { columns: 2, cardWidth: 260 });
assert.deepStrictEqual(recommendationLayoutForWidth(250, 2), { columns: 1, cardWidth: 250 });
assert.deepStrictEqual(recommendationLayoutForWidth(500, 3), { columns: 3, cardWidth: 154 });
assert.deepStrictEqual(recommendationLayoutForWidth(100, 3), { columns: 1, cardWidth: 100 });
assert.strictEqual(getRecommendationColumnsPerCategory({ recommendationColumnsPerCategory: 3 }), 3);
assert.strictEqual(getRecommendationColumnsPerCategory({ recommendationColumnsPerCategory: 99 }), 2);

const calls = { detail: [], open: [], context: [], quick: [], remove: [] };
State.currentPage = RANDOM_RECOMMENDATIONS_PAGE;
State.bridge = {
  getDetail(page, id) { calls.detail.push([page, id]); },
  openResource(page, id) { calls.open.push([page, id]); },
};
openContextMenu = (event, page, item) => calls.context.push([page, item.id]);

const recommendationData = {
  mode: "recommendations",
  columns: [
    { key: "books", sourcePage: "library", items: [{ id: "b1", title: "Book" }] },
    { key: "novels", sourcePage: "text_novel", items: [{ id: "n1", title: "Novel" }] },
    { key: "comics", sourcePage: "comic", items: [{ id: "c1", title: "Comic" }] },
  ],
};
const area = document.getElementById("contentArea");
renderRecommendations(area, recommendationData);
const cards = [];
const collectCards = (node) => {
  if (node.tagName === "ARTICLE") cards.push(node);
  node.children.forEach(collectCards);
};
collectCards(area);
assert.strictEqual(cards.length, 3);
cards.forEach((card) => {
  card.dispatch("click");
  card.dispatch("keydown", { key: "Enter", preventDefault() {} });
  card.dispatch("dblclick");
  card.dispatch("contextmenu", { preventDefault() {} });
});
assert.deepStrictEqual(calls.detail, [
  ["library", "b1"], ["library", "b1"],
  ["text_novel", "n1"], ["text_novel", "n1"],
  ["comic", "c1"], ["comic", "c1"],
]);
assert.deepStrictEqual(calls.open, [["library", "b1"], ["text_novel", "n1"], ["comic", "c1"]]);
assert.deepStrictEqual(calls.context, [["library", "b1"], ["text_novel", "n1"], ["comic", "c1"]]);
assert.strictEqual(observerStats.created, 1, "one ResizeObserver must own all recommendation columns");
assert.strictEqual(typeof area._recommendationCleanup, "function");
teardownVirtualWindow(area);
assert.strictEqual(observerStats.disconnected, 1, "recommendation ResizeObserver must disconnect on teardown");
assert.strictEqual(area._recommendationCleanup, null);

openQuickAddModal = (item, page) => calls.quick.push([page, item.id]);
confirmRemoveFromLibrary = (page, item) => calls.remove.push([page, item.id]);
for (const [page, id] of [["library", "b1"], ["text_novel", "n1"], ["comic", "c1"]]) {
  clear(document.getElementById("detailContent"));
  renderDetail({ id, title: id }, page);
  const buttons = document.getElementById("detailContent").children.at(-1).children;
  buttons[0].dispatch("click");
  buttons[1].dispatch("click");
  buttons.at(-1).dispatch("click");
}
assert.deepStrictEqual(calls.open.slice(-3), [["library", "b1"], ["text_novel", "n1"], ["comic", "c1"]]);
assert.deepStrictEqual(calls.quick, [["library", "b1"], ["text_novel", "n1"], ["comic", "c1"]]);
assert.deepStrictEqual(calls.remove, [["library", "b1"], ["text_novel", "n1"], ["comic", "c1"]]);

State.settings = { gridColumns: 4, viewportBufferScreens: 3, textNovelViewMode: "grid" };
assert.strictEqual(viewModeForPage("text_novel"), "grid");
assert.strictEqual(viewModeForPage("library"), State.viewMode);
const savedViewModes = [];
State.bridge.setSetting = (key, value) => savedViewModes.push([key, value]);
setViewModeForPage("text_novel", "list");
assert.deepStrictEqual(savedViewModes, [["textNovelViewMode", "list"]]);
assert.strictEqual(State.settings.textNovelViewMode, "list");

clear(area);
State.renderGen += 1;
renderTextNovelGrid(area, [{ id: "n-grid", title: "Grid Novel", cover: "" }], "text_novel", State.renderGen);
const textGridCards = [];
const findArticles = (node) => {
  if (node.tagName === "ARTICLE") textGridCards.push(node);
  node.children.forEach(findArticles);
};
textGridCards.length = 0;
findArticles(area);
assert.strictEqual(textGridCards.length, 1);
assert.strictEqual(textGridCards[0].children.at(-1).textContent, "Grid Novel");
assert.strictEqual(textGridCards[0].attributes.role, "button");
assert.strictEqual(textGridCards[0].attributes.tabindex, "0");
textGridCards[0].dispatch("keydown", { key: "Enter", preventDefault() {} });
assert.deepStrictEqual(calls.detail.at(-1), ["text_novel", "n-grid"]);
textGridCards[0].dispatch("dblclick");
textGridCards[0].dispatch("contextmenu", { preventDefault() {} });
assert.deepStrictEqual(calls.open.at(-1), ["text_novel", "n-grid"]);
assert.deepStrictEqual(calls.context.at(-1), ["text_novel", "n-grid"]);
assert.strictEqual(typeof area._virtCleanup, "function", "Text Novel grid keeps virtual-window cleanup");

teardownVirtualWindow(area);
clear(area);
State.renderGen += 1;
renderTable(area, [{ id: "n-list", title: "List Novel", author: "A", tags: [], path: "N.txt" }], "text_novel");
const textTable = area.children[1];
assert.strictEqual(textTable.children[0].children[0].children.length, 4, "Text Novel list omits cover column");
assert.strictEqual(textTable.children[1].children[0].children[0].children.length, 4, "Text Novel rows align without cover cell");

teardownVirtualWindow(area);
clear(area);
State.renderGen += 1;
renderTable(area, [{ id: "b-list", title: "Book", author: "A", tags: [], path: "B.pdf" }], "library");
const libraryTable = area.children[1];
assert.strictEqual(libraryTable.children[0].children[0].children.length, 5, "Library list keeps cover column");

State.searchQueries.library = "preserved query";
syncSearchInputFromPage(RANDOM_RECOMMENDATIONS_PAGE);
assert.strictEqual(document.getElementById("searchInput").disabled, true);
assert.strictEqual(document.getElementById("searchInput").value, "");
syncSearchInputFromPage("library");
assert.strictEqual(document.getElementById("searchInput").disabled, false);
assert.strictEqual(document.getElementById("searchInput").value, "preserved query");

const callbacks = [];
let resourcesChangedHandler = null;
let settingsChangedHandler = null;
const signal = () => ({ connect(callback) { this.callback = callback; } });
const bridge = {
  resourcesChanged: { connect(callback) { resourcesChangedHandler = callback; } },
  settingsChanged: { connect(callback) { settingsChangedHandler = callback; } },
  toast: signal(), scanProgress: signal(), scanState: signal(), errorLogsChanged: signal(),
  getRandomRecommendations(callback) { callbacks.push(callback); },
};
State.bridge = bridge;
State.currentPage = RANDOM_RECOMMENDATIONS_PAGE;
State.recommendations = null;
State.recommendationsLoading = false;
State.recommendationRequestId = 0;
loadRandomRecommendations();
loadRandomRecommendations();
assert.strictEqual(callbacks.length, 1, "duplicate requests must be blocked");
callbacks[0](JSON.stringify({ mode: "recommendations", columns: [{ key: "books", items: [{ id: "first" }] }] }));
const cached = State.recommendations;
loadRandomRecommendations();
assert.strictEqual(callbacks.length, 1, "cached recommendations must be reused");
loadRandomRecommendations(true);
loadRandomRecommendations(true);
assert.strictEqual(callbacks.length, 2, "refresh must replace all columns with one request");

wireSignals();
resourcesChangedHandler(JSON.stringify({ pages: {}, recommendationsInvalidated: false }));
assert.strictEqual(State.recommendations, cached, "metadata-only changes must preserve recommendations");
resourcesChangedHandler(JSON.stringify({ pages: {}, recommendationsInvalidated: true }));
assert.strictEqual(callbacks.length, 3, "source changes must request a fresh recommendation set");
callbacks[1](JSON.stringify({ mode: "recommendations", columns: [{ key: "books", items: [{ id: "stale" }] }] }));
assert.strictEqual(State.recommendations, null, "retired callbacks must not restore stale data");
callbacks[2](JSON.stringify({ mode: "recommendations", columns: [{ key: "books", items: [{ id: "fresh" }] }] }));
assert.strictEqual(State.recommendations.columns[0].items[0].id, "fresh");

State.currentPage = RANDOM_RECOMMENDATIONS_PAGE;
State.settings = { recommendationItemsPerCategory: 6, recommendationColumnsPerCategory: 2 };
const recommendationsBeforeLayoutChange = State.recommendations;
scheduledRenders = 0;
settingsChangedHandler(JSON.stringify({ recommendationItemsPerCategory: 6, recommendationColumnsPerCategory: 3 }));
assert.strictEqual(State.recommendations, recommendationsBeforeLayoutChange, "column changes must preserve recommendation ids");
assert.strictEqual(scheduledRenders, 1, "column changes must relayout the current recommendation page");
const callbacksBeforeItemCountChange = callbacks.length;
settingsChangedHandler(JSON.stringify({ recommendationItemsPerCategory: 9, recommendationColumnsPerCategory: 3 }));
assert.strictEqual(State.recommendations, null, "item-count changes must invalidate recommendation ids");
assert.strictEqual(callbacks.length, callbacksBeforeItemCountChange + 1, "item-count changes must request a fresh recommendation set");
`;

vm.runInContext(fs.readFileSync(appPath, "utf8") + "\n" + assertions, context, { filename: appPath });
console.log("RANDOM_RECOMMENDATIONS_BEHAVIOR_OK");
