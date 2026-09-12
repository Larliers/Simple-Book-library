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
    this.clientWidth = 900;
    this.clientHeight = 600;
    this.scrollTop = 0;
  }
  get firstChild() { return this.children[0] || null; }
  appendChild(child) { child.parentElement = this; this.children.push(child); return child; }
  removeChild(child) { this.children.splice(this.children.indexOf(child), 1); child.parentElement = null; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  removeEventListener(name) { delete this.listeners[name]; }
  dispatch(name, event = {}) {
    if (this.listeners[name]) this.listeners[name](Object.assign({ preventDefault() {} }, event));
  }
    querySelectorAll(selector) {
    const result = [];
    const visit = (node) => {
      if (!node || !Array.isArray(node.children)) return;
      if (selector === ".selected" && node.classList && node.classList.contains("selected")) result.push(node);
      node.children.forEach(visit);
    };
    this.children.forEach(visit);
    return result;
  }
  contains(target) { return target === this || this.children.some((child) => child.contains(target)); }
}

const nodes = {
  searchInput: new FakeNode("input"),
  suggestions: new FakeNode(),
  contentArea: new FakeNode("main"),
  detailEmpty: new FakeNode(),
  detailContent: new FakeNode(),
  contextMenu: new FakeNode(),
  toastStack: new FakeNode(),
};

const document = {
  createElement: (tag) => new FakeNode(tag),
  createDocumentFragment: () => new FakeNode("fragment"),
  createTextNode: (text) => ({ textContent: text, parentElement: null, contains: () => false }),
  getElementById: (id) => nodes[id] || null,
  addEventListener() {},
  querySelectorAll() { return []; },
};

const context = {
  assert,
  console,
  document,
  window: { innerWidth: 1400, innerHeight: 860 },
  ResizeObserver: class { observe() {} disconnect() {} },
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

assert.strictEqual(TAG_MANAGER_PAGE, "tag_manager");
State.currentPage = TAG_MANAGER_PAGE;
State.settings = { gridColumns: 4, viewportBufferScreens: 3, tagManagerScopes: { library: true, text_novel: true, comic: true } };

const catalogCallbacks = [];
const resourceCallbacks = [];
State.bridge = {
  getTagCatalog(order, callback) { catalogCallbacks.push([order, callback]); },
  getTagResources(tag, callback) { resourceCallbacks.push([tag, callback]); },
};
loadTagCatalog();
loadTagCatalog();
assert.strictEqual(catalogCallbacks.length, 1, "duplicate catalog requests are blocked");
catalogCallbacks[0][1](JSON.stringify({ mode: "tag_index", order: "asc", tagCount: 1, groups: [] }));
assert.strictEqual(State.tagCatalog.tagCount, 1);

loadTagCatalog(true);
assert.strictEqual(catalogCallbacks.length, 2);
invalidateTagManager(false);
loadTagCatalog(true);
assert.strictEqual(catalogCallbacks.length, 3);
catalogCallbacks[1][1](JSON.stringify({ mode: "tag_index", order: "asc", tagCount: 99, groups: [] }));
assert.strictEqual(State.tagCatalog, null, "stale catalog response is discarded by request id");
catalogCallbacks[2][1](JSON.stringify({ mode: "tag_index", order: "asc", tagCount: 2, groups: [] }));
assert.strictEqual(State.tagCatalog.tagCount, 2);

invalidateTagManager(false);
loadTagCatalog(true);
setTagOrder("desc");
assert.strictEqual(catalogCallbacks.length, 5, "changing sort replaces an in-flight catalog request");
assert.strictEqual(catalogCallbacks[4][0], "desc");
catalogCallbacks[3][1](JSON.stringify({ mode: "tag_index", order: "asc", tagCount: 98, groups: [] }));
assert.strictEqual(State.tagCatalog, null, "old sort response is discarded");
catalogCallbacks[4][1](JSON.stringify({ mode: "tag_index", order: "desc", tagCount: 3, groups: [] }));
assert.strictEqual(State.tagCatalog.order, "desc");

const openTagCalls = [];
State.bridge.openTag = (tag) => { openTagCalls.push(tag); };
const catalogArea = document.getElementById("contentArea");
renderTagCatalog(catalogArea, {
  mode: "tag_index",
  order: "desc",
  tagCount: 1,
  groups: [{ letter: "B", tagCount: 1, items: [{ name: "白色", resourceCount: 2 }] }],
});
const tagButtons = [];
const collectButtons = (node) => {
  if (!node || !Array.isArray(node.children)) return;
  if (node.tagName === "BUTTON") tagButtons.push(node);
  node.children.forEach(collectButtons);
};
collectButtons(catalogArea);
assert.strictEqual(tagButtons.length, 1);
tagButtons[0].dispatch("click");
assert.deepStrictEqual(openTagCalls, ["白色"]);
assert.strictEqual(resourceCallbacks.length, 1);
resourceCallbacks[0][1](JSON.stringify({ mode: "tag_detail", tag: "白色", items: [
  { id: "b1", title: "Book", sourcePage: "library" },
  { id: "n1", title: "Novel", sourcePage: "text_novel" },
  { id: "c1", title: "Comic", sourcePage: "comic" },
] }));
assert.strictEqual(State.tagDetail.tag, "白色");

const calls = { detail: [], open: [], context: [] };
State.bridge.getDetail = (page, id) => calls.detail.push([page, id]);
State.bridge.openResource = (page, id) => calls.open.push([page, id]);
openContextMenu = (event, page, item) => calls.context.push([page, item.id]);
const area = document.getElementById("contentArea");
State.renderGen += 1;
renderTagDetail(area, State.tagDetail, State.renderGen);
const cards = [];
const collectCards = (node) => {
  if (!node || !Array.isArray(node.children)) return;
  if (node.tagName === "ARTICLE") cards.push(node);
  node.children.forEach(collectCards);
};
collectCards(area);
assert.strictEqual(cards.length, 3);
cards.forEach((card) => {
  assert.strictEqual(card.attributes.role, "button");
  card.dispatch("click");
  card.dispatch("keydown", { key: "Enter", preventDefault() {} });
  card.dispatch("dblclick");
  card.dispatch("contextmenu", { preventDefault() {} });
});
assert.deepStrictEqual(calls.open, [["library", "b1"], ["text_novel", "n1"], ["comic", "c1"]]);
assert.deepStrictEqual(calls.context, [["library", "b1"], ["text_novel", "n1"], ["comic", "c1"]]);
assert.deepStrictEqual(calls.detail, [
  ["library", "b1"], ["library", "b1"],
  ["text_novel", "n1"], ["text_novel", "n1"],
  ["comic", "c1"], ["comic", "c1"],
]);
const selected = selectedResourceActionContext();
assert.strictEqual(selected.page, "comic");
assert.strictEqual(selected.item.id, "c1");

loadTagResources("白色");
assert.strictEqual(openTagCalls.length, 1, "direct loadTagResources does not emit open_tag");
assert.strictEqual(resourceCallbacks.length, 2);

syncSearchInputFromPage(TAG_MANAGER_PAGE);
assert.strictEqual(document.getElementById("searchInput").disabled, true);

let scopePayload = "";
State.bridge.setTagManagerScopes = (payload, callback) => { scopePayload = payload; callback(JSON.stringify({ ok: true, error: "", scopes: JSON.parse(payload) })); };
assert.strictEqual(setTagManagerScope("comic", false), true);
assert.strictEqual(JSON.parse(scopePayload).comic, false);
State.settings.tagManagerScopes = { library: false, text_novel: true, comic: false };
assert.strictEqual(setTagManagerScope("text_novel", false), false, "last selected scope is protected");

assert.strictEqual(exitCurrentCollection(), true);
assert.strictEqual(State.tagDetail, null);
assert.strictEqual(State.recentTag, "白色");
assert.strictEqual(openTagCalls.length, 1);

assert.strictEqual(reopenRecentCollection(), true);
assert.deepStrictEqual(openTagCalls, ["白色", "白色"]);
assert.ok(resourceCallbacks.length >= 3);
assert.strictEqual(reopenRecentCollection(), false, "already in tag detail");

State.currentPage = "library";
assert.strictEqual(exitCurrentCollection(), false);
State.currentPage = TAG_MANAGER_PAGE;
assert.strictEqual(exitCurrentCollection(), true);
State.recentTag = null;
assert.strictEqual(reopenRecentCollection(), false);
`;

vm.runInContext(fs.readFileSync(appPath, "utf8") + "\n" + assertions, context, { filename: appPath });
console.log("TAG_MANAGEMENT_BEHAVIOR_OK");
