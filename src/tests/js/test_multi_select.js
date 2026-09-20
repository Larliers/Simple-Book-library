"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const appPath = process.argv[2];
if (!appPath) throw new Error("app.js path is required");

const document = {
  activeElement: null,
  addEventListener() {},
  getElementById() { return null; },
  querySelectorAll() { return []; },
};

const context = {
  assert,
  console,
  document,
  window: { innerWidth: 1200, innerHeight: 800 },
  setTimeout: () => 1,
  clearTimeout() {},
  setInterval: () => 1,
  clearInterval() {},
};
vm.createContext(context);

const assertions = `
const refs = [1, 2, 3, 4, 5].map((id) => ({ sourcePage: "library", id: "book-" + id }));
configureResourceSelection("library", { mode: "grid_or_list", sort: "title_asc" }, refs);

assert.deepStrictEqual(
  updateResourceSelection(refs[1], {}).map((item) => item.id),
  ["book-2"]
);
assert.deepStrictEqual(
  updateResourceSelection(refs[3], { shiftKey: true }).map((item) => item.id),
  ["book-2", "book-3", "book-4"]
);
assert.deepStrictEqual(
  updateResourceSelection(refs[0], { ctrlKey: true }).map((item) => item.id),
  ["book-1", "book-2", "book-3", "book-4"]
);
assert.deepStrictEqual(
  updateResourceSelection(refs[4], { ctrlKey: true, shiftKey: true }).map((item) => item.id),
  ["book-1", "book-2", "book-3", "book-4", "book-5"]
);
assert.deepStrictEqual(
  updateResourceSelection(refs[2], { ctrlKey: true }).map((item) => item.id),
  ["book-1", "book-2", "book-4", "book-5"]
);
assert.deepStrictEqual(
  selectAllResourcesInScope().map((item) => item.id),
  ["book-1", "book-2", "book-3", "book-4", "book-5"]
);

clearResourceSelection();
syncResourceSelectionNodes = () => {};
renderResourceSelectionDetail = () => {};
handleResourceSelectionKeydown(refs[1], {
  key: " ", ctrlKey: true, preventDefault() {},
});
handleResourceSelectionKeydown(refs[3], {
  key: " ", shiftKey: true, preventDefault() {},
});
assert.deepStrictEqual(
  selectedResourceRefs().map((item) => item.id),
  ["book-2", "book-3", "book-4"]
);
clearResourceSelection();
let ctrlADefaultPrevented = false;
assert.strictEqual(handleShortcutKeydown({
  code: "KeyA", key: "a", ctrlKey: true, altKey: false, shiftKey: false, metaKey: false,
  repeat: false, target: null,
  preventDefault() { ctrlADefaultPrevented = true; }, stopPropagation() {},
}), true);
assert.strictEqual(ctrlADefaultPrevented, true);
assert.deepStrictEqual(
  selectedResourceRefs().map((item) => item.id),
  ["book-1", "book-2", "book-3", "book-4", "book-5"]
);

configureResourceSelection("library", { mode: "grid_or_list", sort: "title_asc" }, refs);
assert.strictEqual(selectedResourceRefs().length, 5, "same data scope must retain selection across Grid/List rendering");
configureResourceSelection("library", { mode: "grid_or_list", sort: "title_desc" }, refs.slice().reverse());
assert.strictEqual(selectedResourceRefs().length, 0, "sort changes must clear selection");

const mixed = [
  { sourcePage: "library", id: "same-id" },
  { sourcePage: "comic", id: "same-id" },
];
configureResourceSelection("tag_manager", { mode: "tag_detail", tag: "Mixed" }, mixed);
updateResourceSelection(mixed[0], {});
updateResourceSelection(mixed[1], { ctrlKey: true });
assert.deepStrictEqual(
  selectedResourceRefs().map((item) => item.sourcePage + ":" + item.id),
  ["library:same-id", "comic:same-id"]
);

console.log("MULTI_SELECT_BEHAVIOR_OK");
`;

vm.runInContext(fs.readFileSync(appPath, "utf8") + "\n" + assertions, context, { filename: appPath });
