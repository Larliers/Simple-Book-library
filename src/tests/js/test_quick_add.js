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
  querySelectorAll(selector) {
    const tags = new Set(String(selector).split(",").map((value) => value.trim().toUpperCase()));
    const matches = [];
    const visit = (node) => {
      node.children.forEach((child) => {
        if (tags.has(child.tagName)) matches.push(child);
        visit(child);
      });
    };
    visit(this);
    return matches;
  }
}

const nodes = {
  overlay: new FakeNode(),
  contentArea: new FakeNode("main"),
  contextMenu: new FakeNode(),
  toastStack: new FakeNode(),
};
nodes.overlay.classList.add("hidden");
nodes.contextMenu.classList.add("hidden");

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
  getCollectionNameKey(value, callback) {
    callback(String(value || "").trim().toLowerCase().replaceAll("ß", "ss"));
  },
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
  { id: 4, name: "Straße", nameKey: "strasse" },
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
secondInputs[1].value = "STRASSE";
secondInputs[1].dispatch("input");
assert.strictEqual(
  walk(document.getElementById("overlay"), (node) => node.className.includes("quick-create-row")).length,
  0,
  "Unicode casefold-equivalent names must not offer duplicate creation"
);
secondInputs[1].value = "noth";
secondInputs[1].dispatch("input");
assert.strictEqual(
  walk(document.getElementById("overlay"), (node) => node.className.includes("quick-create-row")).length,
  1,
  "partial matches must still offer exact-name creation"
);
assert.strictEqual(
  walk(
    document.getElementById("overlay"),
    (node) => node.className.includes("list-item") && node.children[0] && node.children[0].textContent === "Another"
  ).length,
  1,
  "partial matching rows must remain visible beside the create action"
);
secondInputs[1].value = "Keyboard Shelf";
secondInputs[1].dispatch("input");
secondInputs[1].dispatch("keydown", { key: "Enter" });
assert.deepStrictEqual(calls.at(-1), ["library", "book-1", {
  addIds: [], removeIds: [], createName: "Keyboard Shelf",
}]);

openQuickAddModal({ id: "book-1", title: "Book One", tags: [] }, "library");
const batchInputs = walk(document.getElementById("overlay"), (node) => node.tagName === "INPUT");
batchInputs[1].value = "";
batchInputs[1].dispatch("input");
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

let delayedCallback = null;
let tagWritesDuringSubmit = 0;
State.bridge.getTags = (callback) => callback(JSON.stringify(["Recent"]));
State.bridge.addResourceTag = () => { tagWritesDuringSubmit += 1; };
State.bridge.applyCollectionQuickAdd = (page, id, payloadJson, callback) => {
  delayedCallback = callback;
};
openQuickAddModal({ id: "book-1", title: "Book One", tags: [] }, "library");
const lockedSearch = walk(document.getElementById("overlay"), (node) => node.tagName === "INPUT")[1];
lockedSearch.value = "Slow Shelf";
lockedSearch.dispatch("input");
walk(document.getElementById("overlay"), (node) => node.className.includes("quick-create-row"))[0].dispatch("click");
const lockedClose = walk(
  document.getElementById("overlay"),
  (node) => node.tagName === "BUTTON" && node.className.includes("close-x")
)[0];
assert.strictEqual(lockedClose.disabled, true);
document.getElementById("overlay").onclick({ target: document.getElementById("overlay") });
assert.strictEqual(document.getElementById("overlay").classList.contains("hidden"), false);
const recentTag = walk(
  document.getElementById("overlay"),
  (node) => node.tagName === "BUTTON" && node.textContent === "Recent"
)[0];
recentTag.dispatch("click");
assert.strictEqual(tagWritesDuringSubmit, 0);
delayedCallback(JSON.stringify({ ok: false, error: "storage_error" }));
assert.strictEqual(lockedClose.disabled, false);
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

closeModal();
State.currentPage = "tag_manager";
State.pages = {
  library: { mode: "grid_or_list", items: [] },
  text_novel: { mode: "grid_or_list", items: [] },
  comic: { mode: "comic", items: [] },
  collections: { mode: "collections", items: [] },
  novel_collections: { mode: "collections", items: [] },
  comic_collections: { mode: "collections", items: [] },
};
const batchRefs = [
  { sourcePage: "library", id: "book-1" },
  { sourcePage: "text_novel", id: "novel-1" },
  { sourcePage: "comic", id: "comic-1" },
];
configureResourceSelection("tag_manager", { mode: "tag_detail", tag: "Mixed" }, batchRefs);
selectAllResourcesInScope();
let batchPayload = null;
State.bridge.getTags = (callback) => callback(JSON.stringify(["Recent Batch"]));
State.bridge.getCollections = (page, callback) => callback(JSON.stringify(
  page === "library" ? [{ id: 7, name: "Existing Books", nameKey: "existing books" }] : []
));
State.bridge.applyBatchQuickAdd = (payloadJson, callback) => {
  batchPayload = JSON.parse(payloadJson);
  callback(JSON.stringify({
    ok: true,
    summary: { resourceCount: 3, collectionLinksAdded: 4, tagsAdded: 6 },
    createdCollections: { book: [], text_novel: [], comic: [] },
    resourceTags: batchRefs.map((ref) => ({ sourcePage: ref.sourcePage, resourceId: ref.id, tags: ["Tag One"] })),
    sourcePages: State.pages,
    collectionPages: {},
    tagCatalogInvalidated: true,
  }));
};
document.getElementById("contentArea").scrollTop = 909;
openBatchQuickAddModal(selectedResourceRefs());
const batchOverlay = document.getElementById("overlay");
const tagInput = walk(batchOverlay, (node) => node.className.includes("batch-tag-input"))[0];
const labelledBatchInputs = walk(
  batchOverlay,
  (node) => node.tagName === "INPUT" && (
    node.className.includes("batch-tag-input") || node.className.includes("batch-collection-search")
  )
);
labelledBatchInputs.forEach((input) => {
  assert.ok(input.attributes.id, "batch inputs must expose a stable id");
  assert.strictEqual(
    walk(batchOverlay, (node) => node.tagName === "LABEL" && node.attributes.for === input.attributes.id).length,
    1,
    "each batch input must have an associated label"
  );
});
tagInput.value = "Tag One";
tagInput.dispatch("keydown", { key: "Enter" });
const existingBooks = walk(
  batchOverlay,
  (node) => node.tagName === "BUTTON" && node.textContent === "Existing Books"
)[0];
existingBooks.dispatch("click");
const comicSearch = walk(
  batchOverlay,
  (node) => node.className.includes("batch-collection-search") && node.dataset.kind === "comic"
)[0];
comicSearch.value = "New Comics";
comicSearch.dispatch("keydown", { key: "Enter" });
walk(
  batchOverlay,
  (node) => node.tagName === "BUTTON" && node.className.includes("batch-submit")
)[0].dispatch("click");
assert.deepStrictEqual(batchPayload, {
  resources: [
    { sourcePage: "library", resourceId: "book-1" },
    { sourcePage: "text_novel", resourceId: "novel-1" },
    { sourcePage: "comic", resourceId: "comic-1" },
  ],
  collections: {
    book: { addIds: [7], createNames: [] },
    text_novel: { addIds: [], createNames: [] },
    comic: { addIds: [], createNames: ["New Comics"] },
  },
  tags: ["Tag One"],
});
assert.strictEqual(batchOverlay.classList.contains("hidden"), true);
assert.strictEqual(selectedResourceRefs().length, 0);
assert.strictEqual(document.getElementById("contentArea").scrollTop, 909);

configureResourceSelection("tag_manager", { mode: "tag_detail", tag: "Mixed" }, batchRefs);
selectAllResourcesInScope();
let failedBatchCallback = null;
State.bridge.applyBatchQuickAdd = (payloadJson, callback) => { failedBatchCallback = callback; };
openBatchQuickAddModal(selectedResourceRefs());
const failedBatchOverlay = document.getElementById("overlay");
const failedTagInput = walk(failedBatchOverlay, (node) => node.className.includes("batch-tag-input"))[0];
failedTagInput.value = "Retry Tag";
failedTagInput.dispatch("keydown", { key: "Enter" });
walk(
  failedBatchOverlay,
  (node) => node.tagName === "BUTTON" && node.className.includes("batch-submit")
)[0].dispatch("click");
assert.ok(failedBatchCallback, "batch submission must reach the bridge");
const lockedControls = walk(
  failedBatchOverlay,
  (node) => ["BUTTON", "INPUT", "SELECT", "TEXTAREA"].includes(node.tagName)
);
assert.ok(lockedControls.length > 4);
assert.strictEqual(
  lockedControls.every((control) => control.disabled),
  true,
  "all modal controls, including dynamically rendered chips and options, must lock during submit"
);
failedBatchCallback(JSON.stringify({ ok: false, error: "storage_error" }));
assert.strictEqual(failedBatchOverlay.classList.contains("hidden"), false);
assert.strictEqual(selectedResourceRefs().length, 3);
assert.strictEqual(
  lockedControls.every((control) => !control.disabled),
  true,
  "failed submission must unlock the modal for retry"
);
closeModal();

State.currentPage = "library";
State.pages.library = {
  mode: "grid_or_list",
  items: [
    { id: "book-1", title: "Book One" },
    { id: "book-2", title: "Book Two" },
    { id: "book-3", title: "Book Three" },
  ],
};
const contextRefs = [
  { sourcePage: "library", id: "book-1" },
  { sourcePage: "library", id: "book-2" },
  { sourcePage: "library", id: "book-3" },
];
configureResourceSelection("library", State.pages.library, contextRefs);
updateResourceSelection(contextRefs[0], {});
updateResourceSelection(contextRefs[1], { ctrlKey: true });
openContextMenu({ clientX: 20, clientY: 30 }, "library", State.pages.library.items[0], false);
assert.strictEqual(selectedResourceRefs().length, 2, "right-clicking a selected item must preserve the batch");
const contextQuickAdd = walk(
  document.getElementById("contextMenu"),
  (node) => node.tagName === "BUTTON" && node.textContent.includes("Quick Add")
)[0];
contextQuickAdd.dispatch("click");
assert.strictEqual(document.getElementById("overlay").classList.contains("hidden"), false);
assert.strictEqual(
  walk(document.getElementById("overlay"), (node) => node.className.includes("batch-submit")).length,
  1,
  "context Quick Add must open the batch modal for a multi-selection"
);
closeModal();

openContextMenu({ clientX: 20, clientY: 30 }, "library", State.pages.library.items[2], false);
assert.deepStrictEqual(
  selectedResourceRefs().map((ref) => ref.id),
  ["book-3"],
  "right-clicking an unselected resource must replace the prior batch with that resource"
);
walk(
  document.getElementById("contextMenu"),
  (node) => node.tagName === "BUTTON" && node.textContent.includes("Quick Add")
)[0].dispatch("click");
assert.strictEqual(
  walk(document.getElementById("overlay"), (node) => node.className.includes("batch-submit")).length,
  0,
  "Quick Add must fall back to the single-resource modal after right-clicking an unselected item"
);

console.log("QUICK_ADD_BEHAVIOR_OK");
`;

vm.runInContext(fs.readFileSync(appPath, "utf8") + "\n" + assertions, context, { filename: appPath });
