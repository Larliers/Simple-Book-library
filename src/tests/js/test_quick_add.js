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
    this.className = "";
    this.style = {};
    this.dataset = {};
    this.attributes = {};
    this.textContent = "";
    this.value = "";
    this.disabled = false;
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
    if (this.listeners[name]) {
      this.listeners[name](Object.assign({ preventDefault() {}, stopPropagation() {} }, event));
    }
  }
  focus() { document.activeElement = this; }
  select() {}
  contains(target) {
    if (target === this) return true;
    return this.children.some((child) => child.contains(target));
  }
  querySelectorAll() { return []; }
}

const nodes = {
  overlay: new FakeNode(),
  contentArea: new FakeNode("main"),
  toastStack: new FakeNode(),
};
nodes.overlay.classList.add("hidden");

const document = {
  activeElement: null,
  createElement: (tag) => new FakeNode(tag),
  createTextNode: (text) => {
    const node = new FakeNode("#text");
    node.textContent = String(text);
    return node;
  },
  getElementById: (id) => nodes[id] || null,
  addEventListener() {},
  querySelectorAll() { return []; },
};

const context = {
  assert,
  console,
  document,
  window: { innerWidth: 740, innerHeight: 700 },
  setTimeout: () => 1,
  clearTimeout() {},
};
vm.createContext(context);

const assertions = `
const walk = (node, predicate, output = []) => {
  if (predicate(node)) output.push(node);
  node.children.forEach((child) => walk(child, predicate, output));
  return output;
};
let scheduledRenders = 0;
let renderedDetails = [];
let detailClears = 0;
scheduleRenderPage = () => { scheduledRenders += 1; };
renderDetail = (detail, page) => { renderedDetails.push([page, detail.id]); };
renderDetailEmpty = () => { detailClears += 1; };

State.currentPage = "library";
State.selected.library = "book-1";
State.pages = {
  library: { mode: "grid_or_list", items: [{ id: "book-1", title: "Book One" }] },
  collections: { mode: "collections", items: [] },
};
document.getElementById("contentArea").scrollTop = 1234;
const calls = [];
State.bridge = {
  getTags(callback) { callback("[]"); },
  getCollections(page, callback) {
    callback(JSON.stringify([{ id: 1, name: "Existing" }]));
  },
  getDetail(page, id, callback) {
    callback(JSON.stringify({ id, title: "Book One", bookCollections: [] }));
  },
  applyCollectionQuickAdd(page, id, payloadJson, callback) {
    calls.push([page, id, JSON.parse(payloadJson)]);
    callback(JSON.stringify({
      ok: true,
      error: "",
      createdCollection: { id: 2, name: "New Shelf" },
      memberIds: [2],
      collectionPage: "collections",
      collectionPageData: { mode: "collections", items: [{ id: "2", title: "New Shelf" }] },
      detail: { id, title: "Book One", bookCollections: [{ id: 2, name: "New Shelf" }] },
    }));
  },
};

openQuickAddModal({ id: "book-1", title: "Book One", tags: [] }, "library");
const inputs = walk(document.getElementById("overlay"), (node) => node.tagName === "INPUT");
assert.strictEqual(inputs.length, 2);
const collectionSearch = inputs[1];
collectionSearch.value = "  New Shelf  ";
collectionSearch.dispatch("input");
const createButtons = walk(
  document.getElementById("overlay"),
  (node) => node.tagName === "BUTTON" && node.textContent.includes("New Shelf")
);
assert.strictEqual(createButtons.length, 1, "missing create-and-add action");
createButtons[0].dispatch("click");

assert.deepStrictEqual(calls, [["library", "book-1", {
  addIds: [], removeIds: [], createName: "New Shelf",
}]]);
assert.strictEqual(document.getElementById("overlay").classList.contains("hidden"), true);
assert.strictEqual(document.getElementById("contentArea").scrollTop, 1234);
assert.strictEqual(scheduledRenders, 0);
assert.strictEqual(State.pages.collections.items[0].title, "New Shelf");
assert.deepStrictEqual(renderedDetails, [["library", "book-1"]]);

State.currentPage = "library";
State.pages.collections = { mode: "collections", items: [] };
State.bridge.getCollections = (page, callback) => callback(JSON.stringify([
  { id: 1, name: "Existing" },
  { id: 3, name: "Another" },
]));
State.bridge.getDetail = (page, id, callback) => callback(JSON.stringify({
  id, title: "Book One", bookCollections: [{ id: 1, name: "Existing" }],
}));
State.bridge.applyCollectionQuickAdd = (page, id, payloadJson, callback) => {
  calls.push([page, id, JSON.parse(payloadJson)]);
  callback(JSON.stringify({
    ok: true,
    collectionPage: "collections",
    collectionPageData: { mode: "collections", items: [] },
    detail: { id, title: "Book One", bookCollections: [{ id: 1, name: "Existing" }, { id: 3, name: "Another" }] },
  }));
};
openQuickAddModal({ id: "book-1", title: "Book One", tags: [] }, "library");
const secondInputs = walk(document.getElementById("overlay"), (node) => node.tagName === "INPUT");
secondInputs[1].value = " existing ";
secondInputs[1].dispatch("input");
assert.strictEqual(
  walk(document.getElementById("overlay"), (node) => node.className.includes("quick-create-row")).length,
  0,
  "case-insensitive exact names must not offer duplicate creation"
);
secondInputs[1].value = "";
secondInputs[1].dispatch("input");
const anotherRow = walk(
  document.getElementById("overlay"),
  (node) => node.className.includes("list-item") && node.children[0] && node.children[0].textContent === "Another"
)[0];
anotherRow.children[1].dispatch("click");
const confirmButton = walk(
  document.getElementById("overlay"),
  (node) => node.tagName === "BUTTON" && node.textContent === "Confirm add"
)[0];
confirmButton.dispatch("click");
assert.deepStrictEqual(calls.at(-1), ["library", "book-1", {
  addIds: [3], removeIds: [], createName: "",
}]);
assert.strictEqual(scheduledRenders, 0);

State.bridge.getCollections = (page, callback) => callback("[]");
State.bridge.getDetail = (page, id, callback) => callback(JSON.stringify({
  id, title: "Book One", bookCollections: [],
}));
State.bridge.applyCollectionQuickAdd = (page, id, payloadJson, callback) => callback(JSON.stringify({
  ok: false, error: "invalid_collection",
}));
openQuickAddModal({ id: "book-1", title: "Book One", tags: [] }, "library");
const failedSearch = walk(document.getElementById("overlay"), (node) => node.tagName === "INPUT")[1];
failedSearch.value = "Failed Shelf";
failedSearch.dispatch("input");
walk(document.getElementById("overlay"), (node) => node.className.includes("quick-create-row"))[0].dispatch("click");
assert.strictEqual(document.getElementById("overlay").classList.contains("hidden"), false);
assert.strictEqual(failedSearch.disabled, false);
assert.strictEqual(document.getElementById("toastStack").children.length, 1);
closeModal();

State.currentPage = "collections";
State.selected.collections = "book-1";
State.pages.collections = {
  mode: "collection_detail", collectionId: 1, collectionName: "Existing",
  items: [{ id: "book-1", title: "Book One" }],
};
document.getElementById("contentArea").scrollTop = 777;
State.bridge.getCollections = (page, callback) => callback(JSON.stringify([{ id: 1, name: "Existing" }]));
State.bridge.getDetail = (page, id, callback) => callback(JSON.stringify({
  id, title: "Book One", bookCollections: [{ id: 1, name: "Existing" }],
}));
State.bridge.applyCollectionQuickAdd = (page, id, payloadJson, callback) => {
  calls.push([page, id, JSON.parse(payloadJson)]);
  callback(JSON.stringify({
    ok: true,
    collectionPage: "collections",
    collectionPageData: { mode: "collection_detail", collectionId: 1, collectionName: "Existing", items: [] },
    detail: { id, title: "Book One", bookCollections: [] },
  }));
};
openQuickAddModal({ id: "book-1", title: "Book One", tags: [] }, "library");
const currentRow = walk(
  document.getElementById("overlay"),
  (node) => node.className.includes("list-item") && node.children[0] && node.children[0].textContent === "Existing"
)[0];
currentRow.children[1].dispatch("click");
walk(
  document.getElementById("overlay"),
  (node) => node.tagName === "BUTTON" && node.textContent === "Confirm add"
)[0].dispatch("click");
assert.deepStrictEqual(calls.at(-1), ["library", "book-1", {
  addIds: [], removeIds: [1], createName: "",
}]);
assert.strictEqual(State.scrollPos.collections, 777);
assert.strictEqual(scheduledRenders, 1);
assert.strictEqual(detailClears, 1);

console.log("QUICK_ADD_BEHAVIOR_OK");
`;

vm.runInContext(fs.readFileSync(appPath, "utf8") + "\n" + assertions, context, { filename: appPath });
