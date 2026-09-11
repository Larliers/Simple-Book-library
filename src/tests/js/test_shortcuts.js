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
  }
  get firstChild() { return this.children[0] || null; }
  appendChild(child) { child.parentElement = this; this.children.push(child); return child; }
  removeChild(child) { this.children.splice(this.children.indexOf(child), 1); child.parentElement = null; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  getAttribute(name) { return this.attributes[name] || null; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  querySelectorAll() { return []; }
  querySelector() { return null; }
  contains(target) { return target === this || this.children.some((child) => child.contains(target)); }
  focus() { document.activeElement = this; }
}

const nodes = {
  overlay: new FakeNode(),
  contextMenu: new FakeNode(),
  contentArea: new FakeNode("main"),
  detailEmpty: new FakeNode(),
  detailContent: new FakeNode(),
};
nodes.overlay.classList.add("hidden");
nodes.contextMenu.classList.add("hidden");

const document = {
  activeElement: null,
  listeners: {},
  createElement: (tag) => new FakeNode(tag),
  createDocumentFragment: () => new FakeNode("fragment"),
  createTextNode: (text) => ({ textContent: text, parentElement: null, contains: () => false }),
  getElementById: (id) => nodes[id] || null,
  addEventListener(name, callback) { this.listeners[name] = callback; },
  querySelectorAll() { return []; },
  querySelector() { return null; },
};

const context = {
  assert,
  console,
  document,
  FakeNode,
  nodes,
  window: { innerWidth: 1400, innerHeight: 860 },
  ResizeObserver: class { observe() {} disconnect() {} },
  requestAnimationFrame: (callback) => { callback(); return 1; },
  cancelAnimationFrame() {},
  setTimeout: () => 1,
  clearTimeout() {},
};
vm.createContext(context);

const assertions = `
assert.strictEqual(shortcutTokenFromKeyboardEvent({ code: "KeyK", ctrlKey: true, altKey: false, shiftKey: true, metaKey: false }), "Ctrl+Shift+KeyK");
assert.strictEqual(shortcutTokenFromKeyboardEvent({ code: "Digit1", ctrlKey: false, altKey: true, shiftKey: false, metaKey: false }), "Alt+Digit1");
assert.strictEqual(shortcutTokenFromKeyboardEvent({ code: "ControlLeft", ctrlKey: true, altKey: false, shiftKey: false, metaKey: false }), "");
assert.strictEqual(isBindableShortcutToken("MouseBack"), true);
assert.strictEqual(shortcutTokenFromKeyboardEvent({ code: "BrowserBack" }), "MouseBack");
assert.strictEqual(shortcutTokenFromKeyboardEvent({ code: "BrowserForward" }), "MouseForward");
assert.strictEqual(shortcutTokenFromMouseEvent({ button: 3 }), "MouseBack");
assert.strictEqual(shortcutTokenFromMouseEvent({ button: 4 }), "MouseForward");
assert.strictEqual(shortcutTokenFromMouseEvent({ buttons: 8 }), "MouseBack");
assert.strictEqual(shortcutTokenFromMouseEvent({ which: 5 }), "MouseForward");
assert.strictEqual(shortcutTokenFromMouseEvent({ button: 0 }), "");
assert.strictEqual(shortcutTokenFromKeyboardEvent({ key: "BrowserBack" }), "MouseBack");
assert.strictEqual(shortcutTokenFromKeyboardEvent({ keyCode: 166 }), "MouseBack");
assert.strictEqual(shortcutTokenFromKeyboardEvent({ keyCode: 167 }), "MouseForward");
assert.strictEqual(isBindableShortcutToken("Ctrl+KeyR"), false);
assert.strictEqual(isBindableShortcutToken("Ctrl+Numpad0"), false);
assert.strictEqual(isBindableShortcutToken("F5"), false);

const calls = { open: [], folder: [], quick: [], cover: [], collection: [], library: [], notices: [] };
State.bridge = {
  openResource(page, id) { calls.open.push([page, id]); },
  openFolder(id) { calls.folder.push(id); },
  editCover(id) { calls.cover.push(id); },
  removeFromCollection(id, collectionId) { calls.collection.push([id, collectionId]); },
};
openQuickAddModal = (item, page) => calls.quick.push([page, item.id]);
confirmRemoveFromLibrary = (page, item) => calls.library.push([page, item.id]);
showShortcutNotice = (key) => calls.notices.push(key);

const book = { page: "library", item: { id: "b1", title: "Book" }, isCollectionDetail: false, collectionId: null };
const novelInCollection = { page: "novel_collections", item: { id: "n1", title: "Novel" }, isCollectionDetail: true, collectionId: 8 };
const comic = { page: "comic", item: { id: "c1", title: "Comic" }, isCollectionDetail: false, collectionId: null };
const comicInCollection = { page: "comic_collections", item: { id: "c2", title: "Comic Series" }, isCollectionDetail: true, collectionId: 9 };
assert.strictEqual(executeAction("open_resource", book), true);
assert.strictEqual(executeAction("open_resource", comic), true);
assert.strictEqual(executeAction("open_folder", book), true);
assert.strictEqual(executeAction("quick_add", novelInCollection), true);
assert.strictEqual(executeAction("edit_cover", comic), true);
assert.strictEqual(executeAction("remove_from_collection", novelInCollection), true);
assert.strictEqual(executeAction("remove_from_library", book), true);
assert.strictEqual(executeAction("remove_from_library", novelInCollection), true);
assert.strictEqual(executeAction("remove_from_library", comicInCollection), true);
assert.strictEqual(executeAction("open_folder", comic), false);
assert.strictEqual(executeAction("quick_add", null), false);
assert.deepStrictEqual(calls.open, [["library", "b1"], ["comic", "c1"]]);
assert.deepStrictEqual(calls.folder, ["b1"]);
assert.deepStrictEqual(calls.quick, [["novel_collections", "n1"]]);
assert.deepStrictEqual(calls.cover, ["c1"]);
assert.deepStrictEqual(calls.collection, [["n1", 8]]);
assert.deepStrictEqual(calls.library, [["library", "b1"], ["novel_collections", "n1"], ["comic_collections", "c2"]]);
assert.deepStrictEqual(calls.notices, ["shortcut.unavailable", "shortcut.no_selection"]);

const matrixContexts = [
  { page: "library", item: { id: "b3" }, isCollectionDetail: false, collectionId: null },
  { page: "text_novel", item: { id: "n3" }, isCollectionDetail: false, collectionId: null },
  { page: "comic", item: { id: "c3" }, isCollectionDetail: false, collectionId: null },
  { page: "collections", item: { id: "bc3" }, isCollectionDetail: true, collectionId: 10 },
  { page: "novel_collections", item: { id: "nc3" }, isCollectionDetail: true, collectionId: 11 },
  { page: "comic_collections", item: { id: "cc3" }, isCollectionDetail: true, collectionId: 12 },
];
const matrixStart = Object.fromEntries(Object.entries(calls).map(([key, value]) => [key, value.length]));
matrixContexts.forEach((context) => {
  executeAction("open_resource", context);
  if (!isComicActionContext(context)) executeAction("open_folder", context);
  executeAction("quick_add", context);
  executeAction("edit_cover", context);
  if (context.isCollectionDetail) executeAction("remove_from_collection", context);
  executeAction("remove_from_library", context);
});
assert.deepStrictEqual(calls.open.slice(matrixStart.open), matrixContexts.map((context) => [context.page, context.item.id]));
assert.deepStrictEqual(calls.folder.slice(matrixStart.folder), ["b3", "n3", "bc3", "nc3"]);
assert.deepStrictEqual(calls.quick.slice(matrixStart.quick), matrixContexts.map((context) => [context.page, context.item.id]));
assert.deepStrictEqual(calls.cover.slice(matrixStart.cover), matrixContexts.map((context) => context.item.id));
assert.deepStrictEqual(calls.collection.slice(matrixStart.collection), [["bc3", 10], ["nc3", 11], ["cc3", 12]]);
assert.deepStrictEqual(calls.library.slice(matrixStart.library), matrixContexts.map((context) => [context.page, context.item.id]));

const collectionCalls = { close: [], open: [], pages: [] };
scheduleRenderPage = () => {};
renderDetailEmpty = () => {};
selectPage = (page) => { collectionCalls.pages.push(page); State.currentPage = page; };
State.bridge.closeCollection = (page, callback) => {
  collectionCalls.close.push(page);
  callback(JSON.stringify({ mode: "collections", items: [] }));
};
State.bridge.openCollection = (page, collectionId, callback) => {
  collectionCalls.open.push([page, collectionId]);
  callback(JSON.stringify({ mode: "collection_detail", collectionId, collectionName: "Recent", items: [] }));
};
assert.deepStrictEqual(State.recentCollections, { collections: null, novel_collections: null, comic_collections: null });
State.currentPage = "collections";
State.pages.collections = { mode: "collection_detail", collectionId: 31, collectionName: "Series 31", items: [] };
assert.strictEqual(exitCurrentCollection(), true);
assert.deepStrictEqual(State.recentCollections.collections, { collectionId: 31, collectionName: "Series 31" });
assert.strictEqual(State.recentCollections.novel_collections, null);
assert.deepStrictEqual(collectionCalls.close, ["collections"]);

State.currentPage = "novel_collections";
State.pages.novel_collections = { mode: "collection_detail", collectionId: 44, collectionName: "Novel 44", items: [] };
assert.strictEqual(exitCurrentCollection(), true);
assert.deepStrictEqual(State.recentCollections.novel_collections, { collectionId: 44, collectionName: "Novel 44" });
assert.deepStrictEqual(State.recentCollections.collections, { collectionId: 31, collectionName: "Series 31" });

State.pages.collections = { mode: "collections", items: [] };
State.currentPage = "collections";
assert.strictEqual(reopenRecentCollection(), true);
assert.deepStrictEqual(collectionCalls.open, [["collections", 31]]);
assert.strictEqual(collectionCalls.pages.length, 0);
assert.deepStrictEqual(State.recentCollections.collections, { collectionId: 31, collectionName: "Recent" });

State.currentPage = "library";
assert.strictEqual(reopenRecentCollection(), false);
assert.strictEqual(exitCurrentCollection(), false);
assert.strictEqual(calls.notices.at(-1), "shortcut.not_collection_page");

State.currentPage = "collections";
State.pages.collections = { mode: "collections", items: [] };
assert.strictEqual(exitCurrentCollection(), false);
assert.strictEqual(calls.notices.at(-1), "shortcut.no_collection_to_exit");

State.pages.collections = { mode: "collection_detail", collectionId: 31, collectionName: "Series 31", items: [] };
assert.strictEqual(reopenRecentCollection(), false);
assert.strictEqual(calls.notices.at(-1), "shortcut.already_in_collection");

State.bridge.openCollection = (page, collectionId, callback) => {
  callback(JSON.stringify({ mode: "collections", items: [] }));
};
State.currentPage = "novel_collections";
State.pages.novel_collections = { mode: "collections", items: [] };
assert.strictEqual(reopenRecentCollection(), true);
assert.strictEqual(State.recentCollections.novel_collections, null);
assert.deepStrictEqual(State.recentCollections.collections, { collectionId: 31, collectionName: "Recent" });
assert.strictEqual(calls.notices.at(-1), "shortcut.recent_missing");

State.recentCollections.comic_collections = { collectionId: 8, collectionName: "Gone" };
forgetRecentCollection("comic_collections", 8);
assert.strictEqual(State.recentCollections.comic_collections, null);
forgetRecentCollection("collections", 999);
assert.deepStrictEqual(State.recentCollections.collections, { collectionId: 31, collectionName: "Recent" });

State.currentPage = "library";
State.pages.library = { mode: "grid_or_list", items: [{ id: "b2", title: "Selected Book" }] };
State.selected.library = "b2";
State.settings = { shortcutBindings: { open_resource: "KeyO" } };
assert.strictEqual(dispatchShortcutInput("KeyO"), true);
assert.deepStrictEqual(calls.open.at(-1), ["library", "b2"]);
State.pages.library = { mode: "grid_or_list", items: [] };
assert.strictEqual(clearInvalidCurrentSelectionAfterResourceChange(), true);
assert.strictEqual(State.selected.library, undefined);
assert.strictEqual(calls.notices.at(-1), "shortcut.selection_stale");
State.pages.library = { mode: "grid_or_list", items: [{ id: "b2", title: "Selected Book" }] };
State.selected.library = "b2";

State.currentPage = "text_novel";
State.pages.text_novel = { mode: "list", items: [{ id: "n8", title: "Selected Novel" }] };
State.selected.text_novel = "n8";
State.settings.shortcutBindings = { quick_add: "KeyA" };
assert.strictEqual(dispatchShortcutInput("KeyA"), true);
assert.deepStrictEqual(calls.quick.at(-1), ["text_novel", "n8"]);

State.currentPage = RANDOM_RECOMMENDATIONS_PAGE;
State.recommendations = {
  mode: "recommendations",
  columns: [
    { key: "books", sourcePage: "library", items: [{ id: "rb1", title: "Recommended Book" }] },
    { key: "novels", sourcePage: "text_novel", items: [{ id: "rn1", title: "Recommended Novel" }] },
    { key: "comics", sourcePage: "comic", items: [{ id: "rc1", title: "Recommended Comic" }] },
  ],
};
for (const [sourcePage, id] of [["library", "rb1"], ["text_novel", "rn1"], ["comic", "rc1"]]) {
  State.recommendationSelection = { sourcePage, id };
  const context = selectedResourceActionContext();
  assert.strictEqual(context.page, sourcePage);
  assert.strictEqual(context.item.id, id);
  executeAction("open_resource", context);
  if (sourcePage !== "comic") executeAction("open_folder", context);
  executeAction("quick_add", context);
  executeAction("edit_cover", context);
  executeAction("remove_from_library", context);
}
assert.deepStrictEqual(calls.open.slice(-3), [["library", "rb1"], ["text_novel", "rn1"], ["comic", "rc1"]]);
assert.deepStrictEqual(calls.quick.slice(-3), [["library", "rb1"], ["text_novel", "rn1"], ["comic", "rc1"]]);
assert.deepStrictEqual(calls.library.slice(-3), [["library", "rb1"], ["text_novel", "rn1"], ["comic", "rc1"]]);
State.recommendationSelection = { sourcePage: "comic", id: "rc1" };
invalidateRandomRecommendations(true);
assert.strictEqual(State.recommendationSelection, null);
assert.strictEqual(calls.notices.at(-1), "shortcut.selection_stale");

State.currentPage = RANDOM_RECOMMENDATIONS_PAGE;
State.recommendations = {
  mode: "recommendations",
  columns: [{ key: "comics", sourcePage: "comic", items: [{ id: "c9", title: "Selected Comic" }] }],
};
State.recommendationSelection = { sourcePage: "comic", id: "c9" };
State.settings.shortcutBindings.open_resource = "MouseForward";
assert.strictEqual(handleNativeShortcutInput("MouseForward"), true);
assert.deepStrictEqual(calls.open.at(-1), ["comic", "c9"]);

State.currentPage = "library";
State.settings.shortcutBindings.open_resource = "KeyO";
let prevented = 0;
const keyEvent = (target, overrides = {}) => ({
  code: "KeyO", ctrlKey: false, altKey: false, shiftKey: false, metaKey: false,
  repeat: false, target,
  preventDefault() { prevented += 1; }, stopPropagation() {},
  ...overrides,
});
const input = new FakeNode("input");
assert.strictEqual(handleShortcutKeydown(keyEvent(input)), false);
nodes.overlay.classList.remove("hidden");
assert.strictEqual(handleShortcutKeydown(keyEvent(new FakeNode())), false);
nodes.overlay.classList.add("hidden");
assert.strictEqual(handleShortcutKeydown(keyEvent(new FakeNode(), { repeat: true })), false);
assert.strictEqual(handleShortcutKeydown(keyEvent(new FakeNode())), true);
assert.strictEqual(prevented, 1);

const savedBindings = [];
State.bridge.setShortcutBinding = (actionId, token, callback) => {
  savedBindings.push([actionId, token]);
  if (token === "KeyQ") {
    callback(JSON.stringify({ ok: false, error: "duplicate", conflictAction: "open_resource", bindings: State.settings.shortcutBindings }));
  } else {
    callback(JSON.stringify({ ok: true, error: "", conflictAction: "", bindings: { ...State.settings.shortcutBindings, [actionId]: token } }));
  }
};
beginShortcutCapture("quick_add");
assert.strictEqual(handleShortcutKeydown(keyEvent(new FakeNode(), { code: "KeyQ" })), true);
assert.strictEqual(State.shortcutCaptureAction, "quick_add");
assert.strictEqual(calls.notices.at(-1), "shortcut.binding_duplicate");
assert.strictEqual(handleNativeShortcutInput("MouseBack"), true);
assert.strictEqual(State.shortcutCaptureAction, "");
assert.deepStrictEqual(savedBindings, [["quick_add", "KeyQ"], ["quick_add", "MouseBack"]]);
beginShortcutCapture("edit_cover");
assert.strictEqual(handleShortcutKeydown(keyEvent(new FakeNode(), { code: "Escape" })), true);
assert.strictEqual(State.shortcutCaptureAction, "");
beginShortcutCapture("exit_collection");
assert.strictEqual(handleShortcutKeydown(keyEvent(new FakeNode(), { code: "BrowserBack" })), true);
assert.strictEqual(State.shortcutCaptureAction, "");
assert.deepStrictEqual(savedBindings.at(-1), ["exit_collection", "MouseBack"]);
beginShortcutCapture("reopen_recent_collection");
assert.strictEqual(handleShortcutMouseDown({
  button: 4,
  preventDefault() { prevented += 1; },
  stopPropagation() {},
}), true);
assert.strictEqual(State.shortcutCaptureAction, "");
assert.deepStrictEqual(savedBindings.at(-1), ["reopen_recent_collection", "MouseForward"]);
const afterMouseForward = savedBindings.length;
assert.strictEqual(handleShortcutSideButton({
  button: 4,
  type: "auxclick",
  preventDefault() { prevented += 1; },
  stopPropagation() {},
}), true);
assert.strictEqual(savedBindings.length, afterMouseForward);
beginShortcutCapture("open_folder");
assert.strictEqual(handleShortcutSideButton({
  button: 3,
  type: "auxclick",
  preventDefault() { prevented += 1; },
  stopPropagation() {},
}), true);
assert.deepStrictEqual(savedBindings.at(-1), ["open_folder", "MouseBack"]);
`;

vm.runInContext(fs.readFileSync(appPath, "utf8") + "\n" + assertions, context, { filename: appPath });
process.stdout.write("SHORTCUTS_BEHAVIOR_OK\n");
