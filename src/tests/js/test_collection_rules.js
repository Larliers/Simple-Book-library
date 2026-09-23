"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const appPath = process.argv[2];
if (!appPath) throw new Error("app.js path is required");

class FakeClassList {
  constructor() { this.values = new Set(); }
  add(...values) { values.forEach((value) => this.values.add(value)); }
  remove(...values) { values.forEach((value) => this.values.delete(value)); }
  contains(value) { return this.values.has(value); }
}

class FakeNode {
  constructor(tag = "div") {
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.parentElement = null;
    this.listeners = {};
    this.attributes = {};
    this.className = "";
    this.classList = new FakeClassList();
    this.dataset = {};
    this.style = {};
    this.textContent = "";
    this.value = "";
    this.checked = false;
    this.disabled = false;
    this.isConnected = true;
  }
  get firstChild() { return this.children[0] || null; }
  appendChild(node) { node.parentElement = this; this.children.push(node); return node; }
  removeChild(node) { this.children.splice(this.children.indexOf(node), 1); node.parentElement = null; }
  remove() { if (this.parentElement) this.parentElement.removeChild(this); this.isConnected = false; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  dispatch(name, event = {}) { if (this.listeners[name]) this.listeners[name]({ preventDefault() {}, ...event }); }
  focus() { document.activeElement = this; }
  contains(node) { return node === this || this.children.some((child) => child.contains(node)); }
  querySelectorAll() { return walk(this, () => true).slice(1); }
  querySelector() { return this.querySelectorAll()[0] || null; }
}

function walk(root, predicate) {
  const result = [];
  const visit = (node) => {
    if (predicate(node)) result.push(node);
    node.children.forEach(visit);
  };
  visit(root);
  return result;
}

const nodes = { contextMenu: new FakeNode(), overlay: new FakeNode(), toastStack: new FakeNode() };
nodes.contextMenu.classList.add("hidden");
nodes.overlay.classList.add("hidden");
const body = new FakeNode("body");
const document = {
  body,
  activeElement: null,
  createElement: (tag) => new FakeNode(tag),
  createTextNode: (text) => { const node = new FakeNode("#text"); node.textContent = String(text); return node; },
  getElementById: (id) => nodes[id] || null,
  addEventListener() {},
};
const context = vm.createContext({
  console,
  assert,
  document,
  walk,
  window: { innerWidth: 1200, innerHeight: 900 },
  setTimeout: (fn) => { fn(); return 1; },
  clearTimeout() {},
  JSON,
  Math,
  Set,
});

const assertions = `
State.strings = {};
let previewPayload = null;
let savePayload = null;
let clearedResource = null;
let controlsLockedDuringSave = false;
const previewResponse = JSON.stringify({
  ok: true,
  previewToken: "preview-1",
  preview: {
    summary: { matched: 1, add: 1, remove: 0, manual_kept: 0, excluded: 0 },
    matched: { total: 1, page: 1, pageSize: 20, items: [{ sourceName: "Alpha" }] },
    add: { total: 1, page: 1, pageSize: 20, items: [{ sourceName: "Alpha" }] },
    remove: { total: 0, page: 1, pageSize: 20, items: [] },
    manualKept: { total: 0, page: 1, pageSize: 20, items: [] },
    excluded: { total: 0, page: 1, pageSize: 20, items: [] },
  },
});
State.bridge = {
  previewCollectionRule(id, json, callback) {
    previewPayload = JSON.parse(json);
    callback(previewResponse);
  },
  saveCollectionRule(id, json, callback) {
    savePayload = JSON.parse(json);
    controlsLockedDuringSave = walk(host, (node) => ["BUTTON", "INPUT", "SELECT"].includes(node.tagName)).every((node) => node.disabled);
    callback(JSON.stringify({ ok: false, error: "storage_error" }));
  },
  clearCollectionRuleExclusion(id, resourceId, callback) {
    clearedResource = resourceId;
    callback(JSON.stringify({ ok: true, rule: { exclusions: [], excludedCount: 0 } }));
  },
};
const detail = {
  id: 7,
  name: "Design",
  kind: "book",
  enabled: true,
  rule: { version: 1, matchMode: "all", conditions: [{ operator: "contains", value: "Alpha", caseSensitive: false }] },
  exclusions: [{ resourceId: "book-9", title: "Excluded", sourceName: "Excluded" }],
  excludedCount: 1,
};
const host = document.createElement("div");
const controller = buildCollectionRuleEditor(host, detail, {});
const buttons = () => walk(host, (node) => node.tagName === "BUTTON");
const byText = (text) => buttons().find((node) => node.textContent === text);
const preview = byText("Preview");
const save = byText("Save");
assert.strictEqual(save.disabled, true, "saving must be locked until preview");
byText("Add condition").dispatch("click");
assert.strictEqual(controller.draft.conditions.length, 2);
preview.dispatch("click");
assert.strictEqual(previewPayload.rule.conditions[0].value, "Alpha");
assert.strictEqual(previewPayload.rule.conditions.length, 1, "blank draft rows must be omitted from the saved rule payload");
assert.strictEqual(save.disabled, false, "current preview must unlock save");
const keyword = walk(host, (node) => node.tagName === "INPUT" && node.value === "Alpha")[0];
keyword.value = "Beta";
keyword.dispatch("input");
assert.strictEqual(save.disabled, true, "editing must invalidate the preview token");
preview.dispatch("click");
save.dispatch("click");
assert.strictEqual(savePayload.previewToken, "preview-1");
assert.strictEqual(savePayload.rule.conditions[0].value, "Beta");
assert.strictEqual(controlsLockedDuringSave, true, "all editor controls must lock during submit");
assert.strictEqual(save.disabled, false, "failed save must unlock the editor for retry");

let delayedPreview = null;
State.bridge.previewCollectionRule = (id, json, callback) => { delayedPreview = callback; };
keyword.value = "Gamma"; keyword.dispatch("input");
preview.dispatch("click");
keyword.value = "Delta"; keyword.dispatch("input");
delayedPreview(previewResponse);
assert.strictEqual(save.disabled, true, "a late preview for an edited draft must stay invalid");

const enabled = walk(host, (node) => node.tagName === "INPUT" && node.attributes.type !== "search")[0];
enabled.checked = false;
enabled.dispatch("change");
const removeChoice = walk(document.body, (node) => node.tagName === "BUTTON" && node.textContent === "Remove automatic members")[0];
assert.ok(removeChoice, "turning off an active rule must ask how to handle automatic members");
removeChoice.dispatch("click");
assert.strictEqual(controller.draft.disableMode, "remove");

const restore = byText("Restore");
restore.dispatch("click");
assert.strictEqual(clearedResource, "book-9");

const triggerCard = document.createElement("article");
let focusRestoredBeforeAction = false;
State.contextMenuTrigger = triggerCard;
const focusAction = menuAction("Focus test", () => { focusRestoredBeforeAction = document.activeElement === triggerCard; });
focusAction.focus();
focusAction.dispatch("click");
assert.strictEqual(focusRestoredBeforeAction, true, "context actions must restore the trigger before opening a modal");

let collectionRuleListRequests = 0;
let settingsRenders = 0;
const originalRenderSettings = renderSettings;
renderSettings = () => { settingsRenders += 1; };
State.collectionRules = { summaries: [], selectedId: 0, query: "", loading: false, loaded: false };
State.currentPage = "settings";
State._settingsSection = "collection_rules";
State.bridge.getCollectionRules = (callback) => { collectionRuleListRequests += 1; callback("[]"); };
renderSettingsCollectionRules(document.createElement("div"));
renderSettingsCollectionRules(document.createElement("div"));
assert.strictEqual(collectionRuleListRequests, 1, "an empty collection list must be treated as loaded");
assert.strictEqual(State.collectionRules.loaded, true);
assert.strictEqual(settingsRenders, 1);
renderSettings = originalRenderSettings;
console.log("COLLECTION_RULES_BEHAVIOR_OK");
`;

vm.runInContext(fs.readFileSync(appPath, "utf8") + "\n" + assertions, context, { filename: appPath });
