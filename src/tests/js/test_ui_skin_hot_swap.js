"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const appPath = process.argv[2];
if (!appPath) throw new Error("app.js path is required");

class FakeClassList {
  constructor(values = []) { this.values = new Set(values); }
  add(value) { this.values.add(value); }
  remove(value) { this.values.delete(value); }
  contains(value) { return this.values.has(value); }
  toggle(value, force) {
    const active = force === undefined ? !this.values.has(value) : Boolean(force);
    if (active) this.values.add(value);
    else this.values.delete(value);
    return active;
  }
}

function fakeElement(tagName = "div") {
  const listeners = new Map();
  const attributes = new Map();
  const node = {
    tagName: tagName.toUpperCase(),
    dataset: {},
    classList: new FakeClassList(),
    children: [],
    parentNode: null,
    hidden: false,
    disabled: false,
    media: "",
    rel: "",
    href: "",
    sheet: null,
    innerHTML: "",
    appendChild(child) {
      child.parentNode = this;
      this.children.push(child);
      return child;
    },
    removeChild(child) {
      this.children = this.children.filter((item) => item !== child);
      child.parentNode = null;
      return child;
    },
    remove() {
      if (this.parentNode) this.parentNode.removeChild(this);
    },
    setAttribute(name, value) {
      const text = String(value);
      attributes.set(name, text);
      if (name === "href") this.href = text;
      if (name === "media") this.media = text;
      if (name.startsWith("data-")) {
        const key = name.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
        this.dataset[key] = text;
      }
    },
    getAttribute(name) {
      if (name === "href") return attributes.has(name) ? attributes.get(name) : this.href;
      if (name === "media") return attributes.has(name) ? attributes.get(name) : this.media;
      return attributes.has(name) ? attributes.get(name) : null;
    },
    addEventListener(type, callback) {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(callback);
    },
    removeEventListener(type, callback) {
      listeners.set(type, (listeners.get(type) || []).filter((item) => item !== callback));
    },
    dispatch(type) {
      if (type === "load") this.sheet = {};
      (listeners.get(type) || []).slice().forEach((callback) => callback({ target: this }));
    },
  };
  Object.defineProperty(node, "firstChild", { get() { return this.children[0] || null; } });
  return node;
}

const head = fakeElement("head");
const mount = fakeElement("div");
mount.hidden = true;
const glassButton = fakeElement("button");
glassButton.dataset.uiSkinOption = "glass";
glassButton.classList.add("active");
const vaporwaveButton = fakeElement("button");
vaporwaveButton.dataset.uiSkinOption = "vaporwave";

function initialSkinLink(href) {
  const link = fakeElement("link");
  link.rel = "stylesheet";
  link.href = href;
  link.media = "all";
  link.sheet = {};
  link.setAttribute("data-skin-link", "");
  link.setAttribute("data-skin", "glass");
  head.appendChild(link);
  return link;
}

const glassLinks = [
  initialSkinLink("app://app/css/skins/glass/tokens.css"),
  initialSkinLink("app://app/css/skins/glass/components.css"),
];

const document = {
  activeElement: null,
  body: { dataset: { uiSkin: "glass", theme: "night" } },
  head,
  documentElement: { style: { setProperty() {} } },
  addEventListener() {},
  createElement: fakeElement,
  getElementById(id) { return id === "vwSceneMount" ? mount : null; },
  querySelector() { return null; },
  querySelectorAll(selector) {
    if (selector === "link[data-skin-link]") {
      return head.children.filter((node) => node.dataset.skinLink !== undefined);
    }
    if (selector === "[data-ui-skin-option]") return [glassButton, vaporwaveButton];
    return [];
  },
};

const context = {
  assert,
  console,
  document,
  window: { innerWidth: 1200, innerHeight: 800 },
  setTimeout,
  clearTimeout,
  setInterval: () => 1,
  clearInterval() {},
};
vm.createContext(context);

const assertions = `
(async () => {
  const persisted = [];
  const backgrounds = [];
  const toasts = [];
  const sceneMount = document.getElementById("vwSceneMount");
  const skinButtons = document.querySelectorAll("[data-ui-skin-option]");
  const initialGlassLinks = document.querySelectorAll("link[data-skin-link]")
    .filter((link) => link.dataset.skin === "glass");
  const modalIdentity = { id: "open-modal" };
  State.bridge = {
    setUiSkin(skin) { persisted.push(skin); },
    setPageBackground(skin, theme) { backgrounds.push([skin, theme]); },
  };
  State.settings = { uiSkin: "glass", sentinel: "keep" };
  State.currentPage = "library";
  State.searchQuery = "needle";
  State.searchQueries.library = "needle";
  State.scrollPos.library = 321;
  State.selected.library = { id: "book-7" };
  State.resourceSelection.scopeKey = "library|grid";
  State.resourceSelection.order = [{ sourcePage: "library", id: "book-7" }];
  State.resourceSelection.selectedKeys = new Set([resourceSelectionKey(State.resourceSelection.order[0])]);
  State.modalReturnFocus = modalIdentity;
  showToast = (title, message, kind) => toasts.push([title, message, kind]);
  renderSettings = () => { throw new Error("skin switching must not rebuild Settings"); };
  loadBootstrap = () => { throw new Error("skin switching must not reload bootstrap"); };
  selectPage = () => { throw new Error("skin switching must not navigate"); };

  const preserved = {
    currentPage: State.currentPage,
    searchQuery: State.searchQuery,
    scroll: State.scrollPos.library,
    selected: State.selected.library,
    selectionScope: State.resourceSelection.scopeKey,
    selectionKeys: [...State.resourceSelection.selectedKeys],
    modal: State.modalReturnFocus,
  };

  const toVaporwave = setUiSkin("vaporwave");
  await Promise.resolve();
  const vaporwaveLinks = document.querySelectorAll("link[data-skin-link]")
    .filter((link) => link.dataset.skin === "vaporwave");
  assert.strictEqual(vaporwaveLinks.length, 5, "target skin stylesheets should be preloaded");
  assert.strictEqual(State.uiSkin, "glass", "current skin must remain until every target stylesheet loads");
  assert.ok(initialGlassLinks.every((link) => link.media === "all"), "current styles must remain active during preload");
  assert.ok(vaporwaveLinks.every((link) => link.media === "not all"), "preloaded styles must stay inactive");
  assert.deepStrictEqual(persisted, [], "target skin must not persist before it is visible");

  vaporwaveLinks.forEach((link) => link.dispatch("load"));
  assert.strictEqual(await toVaporwave, true);
  assert.strictEqual(State.uiSkin, "vaporwave");
  assert.strictEqual(State.settings.uiSkin, "vaporwave");
  assert.strictEqual(document.body.dataset.uiSkin, "vaporwave");
  assert.ok(initialGlassLinks.every((link) => link.media === "not all"));
  assert.ok(vaporwaveLinks.every((link) => link.media === "all"));
  assert.strictEqual(sceneMount.hidden, false);
  assert.strictEqual(sceneMount.children.length, 1);
  assert.deepStrictEqual(persisted, ["vaporwave"]);
  assert.deepStrictEqual(backgrounds, [["vaporwave", "night"]]);
  assert.strictEqual(skinButtons[0].classList.contains("active"), false);
  assert.strictEqual(skinButtons[1].classList.contains("active"), true);
  assert.strictEqual(skinButtons[1].getAttribute("aria-pressed"), "true");

  assert.strictEqual(State.currentPage, preserved.currentPage);
  assert.strictEqual(State.searchQuery, preserved.searchQuery);
  assert.strictEqual(State.scrollPos.library, preserved.scroll);
  assert.strictEqual(State.selected.library, preserved.selected);
  assert.strictEqual(State.resourceSelection.scopeKey, preserved.selectionScope);
  assert.deepStrictEqual([...State.resourceSelection.selectedKeys], preserved.selectionKeys);
  assert.strictEqual(State.modalReturnFocus, preserved.modal);

  const stylesheetCount = document.querySelectorAll("link[data-skin-link]").length;
  assert.strictEqual(await setUiSkin("glass"), true);
  assert.strictEqual(document.querySelectorAll("link[data-skin-link]").length, stylesheetCount);
  assert.strictEqual(State.uiSkin, "glass");
  assert.ok(initialGlassLinks.every((link) => link.media === "all"));
  assert.ok(vaporwaveLinks.every((link) => link.media === "not all"));
  assert.strictEqual(sceneMount.hidden, true);
  assert.strictEqual(sceneMount.children.length, 0);
  assert.deepStrictEqual(persisted, ["vaporwave", "glass"]);
  assert.deepStrictEqual(backgrounds, [["vaporwave", "night"], ["glass", "night"]]);

  const settingsNodeIdentity = { id: "settings-node" };
  State.currentPage = "settings";
  State.settingsNodeIdentity = settingsNodeIdentity;
  await handleSettingsChanged(JSON.stringify({ uiSkin: "vaporwave", sentinel: "keep" }));
  assert.strictEqual(State.uiSkin, "vaporwave", "settings push should use the hot-swap entry point");
  assert.strictEqual(State.settingsNodeIdentity, settingsNodeIdentity, "skin-only push must preserve Settings DOM state");
  assert.deepStrictEqual(persisted, ["vaporwave", "glass"], "settings push must not persist back through the bridge");
  await handleSettingsChanged(JSON.stringify({ uiSkin: "glass", sentinel: "keep" }));
  State.currentPage = "library";

  vaporwaveLinks.forEach((link) => link.remove());
  const beforeFailurePersistCount = persisted.length;
  const failedSwitch = setUiSkin("vaporwave");
  await Promise.resolve();
  const retryLinks = document.querySelectorAll("link[data-skin-link]")
    .filter((link) => link.dataset.skin === "vaporwave");
  retryLinks[0].dispatch("error");
  retryLinks.slice(1).forEach((link) => link.dispatch("load"));
  assert.strictEqual(await failedSwitch, false);
  assert.strictEqual(State.uiSkin, "glass");
  assert.strictEqual(State.settings.uiSkin, "glass");
  assert.ok(initialGlassLinks.every((link) => link.media === "all"));
  assert.strictEqual(persisted.length, beforeFailurePersistCount);
  assert.strictEqual(toasts.length, 1);
  assert.strictEqual(toasts[0][2], "warning");

  console.log("UI_SKIN_HOT_SWAP_BEHAVIOR_OK");
})()
`;

const result = vm.runInContext(
  fs.readFileSync(appPath, "utf8") + "\n" + assertions,
  context,
  { filename: appPath }
);

Promise.resolve(result).catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
