"use strict";

/* Text Rules Web panel (phase 1 + phase 2 affordances) */
const TR = {
  open: false,
  path: "",
  rules: {},
  catalog: null,
  samples: [],
  samplePath: "",
  presets: [],
  field: "title",
  ruleIndex: 0,
  stepIndex: 0,
  previewTimer: null,
  dirty: false,
};

function ensureTextRulesHost() {
  let host = $("textRulesOverlay");
  if (host) {
    installTrWheelGuard(host);
    return host;
  }
  host = elem("div", "tr-overlay hidden");
  host.id = "textRulesOverlay";
  document.body.appendChild(host);
  installTrWheelGuard(host);
  return host;
}

/*
 * On Windows, hovering the mouse wheel over a native <select> silently
 * changes its selected value (no click/focus needed) and fires `change`.
 * The Text Rules mid column packs several selects (source/category/type/
 * params) inside a scrollable .tr-col, so a plain scroll gesture can
 * misfire a rebuild while the user only meant to scroll. Intercept wheel
 * events targeting a <select> here and forward the delta to the real
 * scroll container instead of letting the browser change the value.
 */
function installTrWheelGuard(host) {
  if (host._trWheelGuardInstalled) return;
  host._trWheelGuardInstalled = true;
  host.addEventListener("wheel", (e) => {
    const select = e.target && e.target.closest ? e.target.closest("select") : null;
    if (!select) return;
    e.preventDefault();
    const scroller = select.closest(".tr-col") || select.closest(".tr-drawer-body");
    if (scroller) scroller.scrollTop += e.deltaY;
  }, { passive: false });
}

function closeTextRulesPanel() {
  const host = $("textRulesOverlay");
  if (host) {
    host.classList.add("hidden");
    clear(host);
  }
  TR.open = false;
  if (TR.previewTimer) {
    clearTimeout(TR.previewTimer);
    TR.previewTimer = null;
  }
}

function openTextRulesPanel(data) {
  if (!data || !data.ok) return;
  TR.open = true;
  TR.path = data.path || "";
  TR.rules = normalizeRulesMap(data.rules || {});
  TR.catalog = data.catalog || {};
  TR.samples = data.samples || [];
  TR.samplePath = data.samplePath || (TR.samples[0] && TR.samples[0].path) || "";
  TR.presets = Array.isArray(data.presets) ? data.presets : [];
  TR.field = "title";
  TR.ruleIndex = 0;
  TR.stepIndex = 0;
  TR.dirty = false;
  ensureFieldRules(TR.field);
  renderTextRulesPanel();
  scheduleTextRulePreview();
}

function normalizeRulesMap(raw) {
  const out = { title: [], author: [], series: [], tag: [] };
  Object.keys(out).forEach((field) => {
    const list = raw[field];
    out[field] = Array.isArray(list) ? list.map(normalizeRule).filter(Boolean) : [];
  });
  return out;
}

function normalizeRule(item) {
  if (!item || typeof item !== "object") return null;
  return {
    field: String(item.field || TR.field || "title"),
    source: String(item.source || "stem"),
    steps: Array.isArray(item.steps)
      ? item.steps.map((s) => {
          if (!s || typeof s !== "object") return null;
          const type = String(s.type || "trim");
          const params = Object.assign({}, s);
          delete params.type;
          return { type, params };
        }).filter(Boolean)
      : [],
  };
}

function ensureFieldRules(field) {
  if (!TR.rules[field]) TR.rules[field] = [];
  if (!TR.rules[field].length) {
    TR.rules[field].push({ field, source: "stem", steps: [{ type: "trim", params: {} }] });
  }
  if (TR.ruleIndex >= TR.rules[field].length) TR.ruleIndex = Math.max(0, TR.rules[field].length - 1);
}

function currentRules() {
  ensureFieldRules(TR.field);
  return TR.rules[TR.field];
}

function currentRule() {
  const list = currentRules();
  return list[TR.ruleIndex] || null;
}

function rulesJsonForSave() {
  const payload = {};
  Object.keys(TR.rules).forEach((field) => {
    const list = TR.rules[field] || [];
    if (!list.length) return;
    payload[field] = list.map((rule) => ({
      field,
      source: rule.source,
      steps: (rule.steps || []).map((step) => Object.assign({ type: step.type }, step.params || {})),
    }));
  });
  return JSON.stringify(payload);
}

function fieldRulesJson() {
  const list = currentRules();
  return JSON.stringify(list.map((rule) => ({
    field: TR.field,
    source: rule.source,
    steps: (rule.steps || []).map((step) => Object.assign({ type: step.type }, step.params || {})),
  })));
}

function markDirty() {
  TR.dirty = true;
  scheduleTextRulePreview();
}

function scheduleTextRulePreview() {
  if (TR.previewTimer) clearTimeout(TR.previewTimer);
  TR.previewTimer = setTimeout(() => {
    TR.previewTimer = null;
    runTextRulePreview();
  }, 220);
}

function runTextRulePreview() {
  if (!TR.open || !State.bridge) return;
  const resultEl = $("trPreviewResult");
  const diagEl = $("trPreviewDiag");
  if (!resultEl) return;
  State.bridge.previewTextRule(TR.path, fieldRulesJson(), TR.samplePath || "", (json) => {
    const d = safeParse(json) || {};
    resultEl.classList.remove("ok", "fail");
    if (!d.ok) {
      resultEl.classList.add("fail");
      resultEl.textContent = d.error || "Preview failed";
      if (diagEl) diagEl.textContent = "";
      return;
    }
    resultEl.classList.add(d.success ? "ok" : "fail");
    resultEl.textContent = d.success ? (d.value || "(empty)") : (d.error || d.value || "(failed)");
    if (diagEl) {
      const bits = [];
      if (d.detectedEncoding) {
        const conf = (typeof d.encodingConfidence === "number") ? d.encodingConfidence.toFixed(2) : "";
        bits.push("encoding: " + d.detectedEncoding + (conf ? " (" + conf + ")" : ""));
      }
      if (d.warning) bits.push(d.warning);
      if (d.failedStep) bits.push("failed: " + d.failedStep);
      if (d.txtFirstLine) bits.push("first line: " + d.txtFirstLine);
      diagEl.textContent = bits.join(" · ");
    }
  });
}

function runMultiPreview() {
  if (!TR.open || !State.bridge) return;
  const box = $("trMultiList");
  if (!box) return;
  box.textContent = t("text.rules.preview.running", "Running…");
  State.bridge.previewTextRulesMulti(TR.path, fieldRulesJson(), (json) => {
    const d = safeParse(json) || {};
    clear(box);
    if (!d.ok) {
      box.textContent = d.error || "Multi preview failed";
      return;
    }
    (d.items || []).forEach((item) => {
      const row = elem("div", "tr-multi-item" + (item.success ? "" : " fail"));
      row.appendChild(elem("div", "tr-multi-name", item.name || item.path));
      row.appendChild(elem("div", "tr-multi-value", item.success ? (item.value || "(empty)") : (item.error || "fail")));
      box.appendChild(row);
    });
  });
}

function renderTextRulesPanel() {
  const host = ensureTextRulesHost();
  clear(host);
  host.classList.remove("hidden");

  const card = elem("div", "tr-host");
  const panel = elem("div", "tr-panel");

  /* header */
  const header = elem("div", "tr-header");
  const titleBlock = elem("div");
  titleBlock.appendChild(elem("h2", null, t("text.rules.title", "Text Rules")));
  titleBlock.appendChild(elem("div", "tr-path", fmt(t("text.rules.root", "Path: {path}"), { path: TR.path })));
  header.appendChild(titleBlock);
  const headerActions = elem("div", "tr-header-actions");
  const regexBtn = elem("button", "ghost-btn", t("text.rules.regex.button", "Common Regex"));
  regexBtn.addEventListener("click", () => openTrSideDrawer("regex"));
  const helpBtn = elem("button", "ghost-btn", t("text.rules.help.button", "Usage Guide"));
  helpBtn.addEventListener("click", () => openTrSideDrawer("help"));
  headerActions.appendChild(regexBtn);
  headerActions.appendChild(helpBtn);
  header.appendChild(headerActions);
  panel.appendChild(header);

  /* body: placeholder only — content is (re)built by renderTrBody() so
     routine edits never tear down this shell / replay its entrance animation. */
  const body = elem("div", "tr-body");
  panel.appendChild(body);

  /* footer */
  const footer = elem("div", "tr-footer");
  const actions = elem("div", "tr-footer-actions");
  const cancel = elem("button", "ghost-btn", t("text.rules.cancel", "Cancel"));
  cancel.addEventListener("click", () => closeTextRulesPanel());
  const save = elem("button", "primary-btn", t("text.rules.save", "Save"));
  save.addEventListener("click", () => saveTextRulesPanel());
  actions.appendChild(cancel);
  actions.appendChild(save);
  footer.appendChild(actions);
  panel.appendChild(footer);

  card.appendChild(panel);
  host.appendChild(card);
  host.onclick = (e) => {
    if (e.target === host) closeTextRulesPanel();
  };

  renderTrBody();
}

/*
 * Rebuilds only the three .tr-col columns inside the already-mounted shell.
 * Every routine edit (field switch, add/delete/move rule or step, source/
 * category/type change, template/preset apply) calls this instead of
 * renderTextRulesPanel() — it never touches .tr-overlay/.tr-host, so the
 * overlayIn/modalIn entrance animation never replays and a simple edit no
 * longer looks like a full-panel "white flash / reload".
 */
function renderTrBody() {
  const host = $("textRulesOverlay");
  if (!host) return;
  const body = host.querySelector(".tr-body");
  if (!body) return;

  const scrollTops = Array.prototype.map.call(body.querySelectorAll(".tr-col"), (c) => c.scrollTop);
  clear(body);
  body.appendChild(buildTrLeftCol());
  body.appendChild(buildTrMidCol());
  body.appendChild(buildTrRightCol());
  Array.prototype.forEach.call(body.querySelectorAll(".tr-col"), (c, i) => {
    if (scrollTops[i] != null) c.scrollTop = scrollTops[i];
  });
}

function buildTrLeftCol() {
  const col = elem("div", "tr-col");
  col.appendChild(elem("div", "small-note", t("text.rules.fields", "Fields")));
  const tabs = elem("div", "tr-field-tabs");
  const fields = (TR.catalog.fields || [
    { id: "title", label: "Title" },
    { id: "author", label: "Author" },
    { id: "series", label: "Series" },
    { id: "tag", label: "Tag" },
  ]);
  fields.forEach((f) => {
    const btn = elem("button", TR.field === f.id ? "active" : "", f.label || f.id);
    btn.addEventListener("click", () => {
      TR.field = f.id;
      TR.ruleIndex = 0;
      TR.stepIndex = 0;
      ensureFieldRules(TR.field);
      renderTrBody();
      scheduleTextRulePreview();
    });
    tabs.appendChild(btn);
  });
  col.appendChild(tabs);

  col.appendChild(elem("div", "small-note", t("text.rules.chain", "Rule Chain")));
  const list = elem("div", "tr-rule-list");
  currentRules().forEach((rule, idx) => {
    const item = elem("button", "tr-rule-item" + (idx === TR.ruleIndex ? " active" : ""),
      "#" + (idx + 1) + " · " + (rule.source || "?"));
    item.addEventListener("click", () => {
      TR.ruleIndex = idx;
      TR.stepIndex = 0;
      renderTrBody();
      scheduleTextRulePreview();
    });
    list.appendChild(item);
  });
  col.appendChild(list);

  const row = elem("div", "tr-actions-row");
  const add = elem("button", "ghost-btn", t("text.rules.add_rule", "Add Rule"));
  add.addEventListener("click", () => {
    currentRules().push({ field: TR.field, source: "stem", steps: [{ type: "trim", params: {} }] });
    TR.ruleIndex = currentRules().length - 1;
    markDirty();
    renderTrBody();
  });
  const del = elem("button", "ghost-btn", t("text.rules.delete_rule", "Delete Rule"));
  del.addEventListener("click", () => {
    const rules = currentRules();
    if (rules.length <= 1) return;
    rules.splice(TR.ruleIndex, 1);
    TR.ruleIndex = Math.min(TR.ruleIndex, rules.length - 1);
    markDirty();
    renderTrBody();
  });
  const up = elem("button", "ghost-btn", "↑");
  up.title = t("text.rules.move_up", "Move up");
  up.addEventListener("click", () => moveRule(-1));
  const down = elem("button", "ghost-btn", "↓");
  down.title = t("text.rules.move_down", "Move down");
  down.addEventListener("click", () => moveRule(1));
  row.appendChild(add);
  row.appendChild(del);
  row.appendChild(up);
  row.appendChild(down);
  col.appendChild(row);
  return col;
}

function moveRule(delta) {
  const rules = currentRules();
  const to = TR.ruleIndex + delta;
  if (to < 0 || to >= rules.length) return;
  const tmp = rules[TR.ruleIndex];
  rules[TR.ruleIndex] = rules[to];
  rules[to] = tmp;
  TR.ruleIndex = to;
  markDirty();
  renderTrBody();
}

function buildTrMidCol() {
  const col = elem("div", "tr-col");
  const rule = currentRule();
  if (!rule) {
    col.appendChild(elem("div", "small-note", "No rule"));
    return col;
  }

  col.appendChild(elem("label", "field-label", t("text.rules.source", "Source")));
  const source = elem("select", "sort-select");
  source.id = "trSource";
  (TR.catalog.sources || []).forEach((s) => {
    const opt = document.createElement("option");
    opt.value = s.id;
    opt.textContent = s.label || s.id;
    if (s.id === rule.source) opt.selected = true;
    source.appendChild(opt);
  });
  source.addEventListener("change", () => {
    rule.source = source.value;
    markDirty();
    renderTrBody();
  });
  col.appendChild(source);

  col.appendChild(elem("div", "small-note", t("text.rules.steps", "Steps")));
  const stepsBox = elem("div", "tr-steps");
  (rule.steps || []).forEach((step, idx) => {
    stepsBox.appendChild(buildStepCard(rule, step, idx));
  });
  col.appendChild(stepsBox);

  const addStep = elem("button", "ghost-btn", t("text.rules.add_step", "Add Step"));
  addStep.addEventListener("click", () => {
    rule.steps.push({ type: "trim", params: {} });
    TR.stepIndex = rule.steps.length - 1;
    markDirty();
    renderTrBody();
  });
  col.appendChild(addStep);

  const subtle = elem("div", "tr-subtle");
  subtle.appendChild(elem("div", "small-note", t("text.rules.templates", "Templates")));
  const tplRow = elem("div", "tr-actions-row");
  (TR.catalog.templates || []).forEach((tpl) => {
    const btn = elem("button", "ghost-btn", tpl.label || tpl.id);
    btn.addEventListener("click", () => {
      const nr = normalizeRule(tpl.rule);
      if (!nr) return;
      const targetField = tpl.field || TR.field;
      if (!TR.rules[targetField]) TR.rules[targetField] = [];
      TR.rules[targetField].push(nr);
      TR.field = targetField;
      TR.ruleIndex = TR.rules[targetField].length - 1;
      markDirty();
      renderTrBody();
    });
    tplRow.appendChild(btn);
  });
  subtle.appendChild(tplRow);

  subtle.appendChild(elem("div", "small-note", t("text.rules.presets", "My Presets")));
  const presetRow = elem("div", "tr-actions-row");
  const savePreset = elem("button", "ghost-btn", t("text.rules.preset.save", "Save as preset"));
  savePreset.addEventListener("click", () => saveCurrentAsPreset());
  presetRow.appendChild(savePreset);
  (TR.presets || []).forEach((preset, idx) => {
    const btn = elem("button", "ghost-btn", preset.name || ("Preset " + (idx + 1)));
    btn.title = preset.kind || "rule";
    btn.addEventListener("click", () => applyPreset(preset));
    const delP = elem("button", "ghost-btn", "×");
    delP.title = t("text.rules.preset.delete", "Delete preset");
    delP.addEventListener("click", (e) => {
      e.stopPropagation();
      deletePreset(idx);
    });
    presetRow.appendChild(btn);
    presetRow.appendChild(delP);
  });
  subtle.appendChild(presetRow);
  col.appendChild(subtle);
  return col;
}

function stepMeta(type) {
  const steps = (TR.catalog && TR.catalog.steps) || [];
  return steps.find((s) => s.type === type) || { type, label: type, params: [], defaults: {}, category: "clean" };
}

function buildStepCard(rule, step, idx) {
  const meta = stepMeta(step.type);
  const card = elem("div", "tr-step-card" + (idx === TR.stepIndex ? " selected" : ""));
  card.addEventListener("click", () => { TR.stepIndex = idx; });

  const head = elem("div", "tr-step-head");
  head.appendChild(elem("strong", null, "#" + (idx + 1)));
  const tools = elem("div", "tr-actions-row");
  const up = elem("button", "ghost-btn", "↑");
  up.addEventListener("click", (e) => { e.stopPropagation(); moveStep(rule, idx, -1); });
  const down = elem("button", "ghost-btn", "↓");
  down.addEventListener("click", (e) => { e.stopPropagation(); moveStep(rule, idx, 1); });
  const del = elem("button", "ghost-btn", "×");
  del.addEventListener("click", (e) => {
    e.stopPropagation();
    if (rule.steps.length <= 1) return;
    rule.steps.splice(idx, 1);
    TR.stepIndex = Math.min(TR.stepIndex, rule.steps.length - 1);
    markDirty();
    renderTrBody();
  });
  tools.appendChild(up);
  tools.appendChild(down);
  tools.appendChild(del);
  head.appendChild(tools);
  card.appendChild(head);

  const catSelect = elem("select", "sort-select");
  const categories = TR.catalog.categories || [];
  categories.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c.id;
    opt.textContent = c.label || c.id;
    if (c.id === meta.category) opt.selected = true;
    catSelect.appendChild(opt);
  });
  card.appendChild(catSelect);

  const typeSelect = elem("select", "sort-select");
  function fillTypes(category) {
    clear(typeSelect);
    ((TR.catalog.steps || []).filter((s) => s.category === category)).forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s.type;
      opt.textContent = s.label || s.type;
      if (s.type === step.type) opt.selected = true;
      typeSelect.appendChild(opt);
    });
  }
  fillTypes(meta.category || "clean");
  catSelect.addEventListener("change", () => {
    fillTypes(catSelect.value);
    if (typeSelect.options.length) {
      step.type = typeSelect.value;
      const nm = stepMeta(step.type);
      step.params = Object.assign({}, nm.defaults || {});
      markDirty();
      renderTrBody();
    }
  });
  typeSelect.addEventListener("change", () => {
    step.type = typeSelect.value;
    const nm = stepMeta(step.type);
    step.params = Object.assign({}, nm.defaults || {});
    markDirty();
    renderTrBody();
  });
  card.appendChild(typeSelect);

  const grid = elem("div", "tr-step-grid");
  (meta.params || []).forEach((p) => {
    const wrap = elem("label", "field");
    wrap.appendChild(elem("span", "field-label", p.key));
    const widget = String(p.widget || "text");
    let input;
    if (widget.startsWith("select:")) {
      input = elem("select", "sort-select");
      widget.slice(7).split("|").forEach((v) => {
        const opt = document.createElement("option");
        opt.value = v;
        opt.textContent = v;
        if (String(step.params[p.key] ?? "") === v) opt.selected = true;
        input.appendChild(opt);
      });
    } else if (widget === "bool") {
      input = elem("select", "sort-select");
      [["true", "true"], ["false", "false"]].forEach(([v, label]) => {
        const opt = document.createElement("option");
        opt.value = v;
        opt.textContent = label;
        const cur = step.params[p.key];
        const curBool = cur === true || cur === "true" || cur === 1 || cur === "1";
        if ((v === "true") === curBool) opt.selected = true;
        input.appendChild(opt);
      });
    } else if (widget === "textarea") {
      input = document.createElement("textarea");
      input.className = "tr-textarea";
      input.rows = 3;
      input.value = step.params[p.key] != null ? String(step.params[p.key]) : "";
    } else {
      input = document.createElement("input");
      input.className = "tr-input";
      input.type = widget === "number" ? "number" : "text";
      input.value = step.params[p.key] != null ? String(step.params[p.key]) : "";
    }
    input.addEventListener("change", () => {
      let val = input.value;
      if (widget === "number") val = Number(val);
      if (widget === "bool") val = val === "true";
      step.params[p.key] = val;
      markDirty();
    });
    input.addEventListener("input", () => {
      if (widget === "number" || widget === "bool") return;
      step.params[p.key] = input.value;
      markDirty();
    });
    wrap.appendChild(input);
    grid.appendChild(wrap);
  });
  card.appendChild(grid);
  return card;
}

function moveStep(rule, idx, delta) {
  const to = idx + delta;
  if (to < 0 || to >= rule.steps.length) return;
  const tmp = rule.steps[idx];
  rule.steps[idx] = rule.steps[to];
  rule.steps[to] = tmp;
  TR.stepIndex = to;
  markDirty();
  renderTrBody();
}

function buildTrRightCol() {
  const col = elem("div", "tr-col");
  col.appendChild(elem("div", "small-note", t("text.rules.preview", "Preview")));

  const sampleLabel = elem("label", "field-label", t("text.rules.sample", "Sample TXT"));
  col.appendChild(sampleLabel);
  const sample = elem("select", "sort-select");
  sample.id = "trSample";
  if (!TR.samples.length) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = t("text.rules.sample.empty", "(no TXT found)");
    sample.appendChild(opt);
  } else {
    TR.samples.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s.path;
      opt.textContent = s.rel || s.name || s.path;
      if (s.path === TR.samplePath) opt.selected = true;
      sample.appendChild(opt);
    });
  }
  sample.addEventListener("change", () => {
    TR.samplePath = sample.value;
    scheduleTextRulePreview();
  });
  col.appendChild(sample);

  const result = elem("div", "tr-preview-result");
  result.id = "trPreviewResult";
  result.textContent = "…";
  col.appendChild(result);
  const diag = elem("div", "small-note");
  diag.id = "trPreviewDiag";
  col.appendChild(diag);

  const multiHead = elem("div", "tr-actions-row");
  multiHead.appendChild(elem("div", "small-note", t("text.rules.multi", "Multi-sample")));
  const runMulti = elem("button", "ghost-btn", t("text.rules.multi.run", "Run 20"));
  runMulti.addEventListener("click", () => runMultiPreview());
  multiHead.appendChild(runMulti);
  col.appendChild(multiHead);
  const multi = elem("div", "tr-multi-list");
  multi.id = "trMultiList";
  col.appendChild(multi);
  return col;
}

function saveTextRulesPanel() {
  if (!State.bridge) return;
  State.bridge.saveTextRules(TR.path, rulesJsonForSave(), (json) => {
    const d = safeParse(json) || {};
    if (!d.ok) {
      showToast(t("text.rules.save_failed", "Save failed"), d.error || "", "warning");
      return;
    }
    TR.dirty = false;
    closeTextRulesPanel();
  });
}

function saveCurrentAsPreset() {
  const rule = currentRule();
  if (!rule) return;
  const name = window.prompt(t("text.rules.preset.name_prompt", "Preset name"), "Preset");
  if (!name) return;
  const preset = {
    id: "p_" + Date.now(),
    kind: "rule",
    name: String(name).trim(),
    source: rule.source,
    steps: (rule.steps || []).map((s) => Object.assign({ type: s.type }, s.params || {})),
  };
  TR.presets = (TR.presets || []).concat([preset]);
  State.bridge.setTextRulePresets(JSON.stringify(TR.presets), (json) => {
    const d = safeParse(json) || {};
    if (d.ok) TR.presets = d.presets || TR.presets;
    renderTrBody();
  });
}

function applyPreset(preset) {
  if (!preset) return;
  const steps = Array.isArray(preset.steps)
    ? preset.steps.map((s) => {
        const type = String(s.type || "trim");
        const params = Object.assign({}, s);
        delete params.type;
        return { type, params };
      })
    : [{ type: "trim", params: {} }];
  if (preset.kind === "steps") {
    const rule = currentRule();
    if (!rule) return;
    rule.steps = steps;
  } else {
    currentRules().push({
      field: TR.field,
      source: String(preset.source || "stem"),
      steps,
    });
    TR.ruleIndex = currentRules().length - 1;
  }
  markDirty();
  renderTrBody();
}

function deletePreset(idx) {
  TR.presets = (TR.presets || []).filter((_, i) => i !== idx);
  State.bridge.setTextRulePresets(JSON.stringify(TR.presets), (json) => {
    const d = safeParse(json) || {};
    if (d.ok) TR.presets = d.presets || TR.presets;
    renderTrBody();
  });
}

function openTrSideDrawer(kind) {
  const host = ensureTextRulesHost();
  let drawer = host.querySelector(".tr-drawer");
  if (drawer) drawer.remove();
  drawer = elem("div", "tr-drawer");
  const head = elem("div", "tr-drawer-head");
  head.appendChild(elem("h3", null, kind === "regex"
    ? t("text.rules.regex.title", "Common Regex")
    : t("text.rules.help.title", "Text Rules Guide")));
  const close = elem("button", "ghost-btn", "×");
  close.addEventListener("click", () => drawer.remove());
  head.appendChild(close);
  drawer.appendChild(head);
  const body = elem("div", "tr-drawer-body");
  if (kind === "regex") {
    (TR.catalog.regexExamples || []).forEach((ex) => {
      const card = elem("div", "tr-drawer-card");
      card.appendChild(elem("strong", null, ex.purpose || ex.id));
      card.appendChild(elem("div", "small-note", ex.sample || ""));
      const code = elem("code", "tr-code", ex.regex || "");
      card.appendChild(code);
      card.appendChild(elem("div", "small-note", ex.result || ""));
      const copy = elem("button", "ghost-btn", t("text.rules.regex.copy", "Copy"));
      copy.addEventListener("click", () => {
        try { navigator.clipboard.writeText(ex.regex || ""); } catch (e) {}
      });
      card.appendChild(copy);
      body.appendChild(card);
    });
  } else {
    (TR.catalog.helpSections || []).forEach((sec) => {
      body.appendChild(elem("h4", null, sec.title || ""));
      (sec.lines || []).forEach((line) => body.appendChild(elem("p", "small-note", line)));
    });
  }
  drawer.appendChild(body);
  host.appendChild(drawer);
}

function wireTextRulesSignal(bridge) {
  if (!bridge || !bridge.textRulesOpen) return;
  bridge.textRulesOpen.connect((json) => {
    const data = safeParse(json);
    if (data) openTextRulesPanel(data);
  });
}
