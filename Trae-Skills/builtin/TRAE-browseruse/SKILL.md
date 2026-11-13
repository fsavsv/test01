---
name: "TRAE-browseruse"
description: "Browser automation operation guide. Invoke when the user wants to browse websites, access URLs, scrape pages, test frontend UI, or run multi-step actions such as click, fill forms, and verify elements. Load this skill before using browser tools."
user-invocable: false
metadata: { version: "1.0.1", last_modified: "2026-10-13T15:23:17+08:00" }
---

# Browser Use Guide

Use browser tools to navigate, interact with pages, and extract data. Call almost every browser tool inside Exec (`await tools.<name>(args)`). The only exception is `browser_waiting_for_user_interaction`, which must be a standalone tool call.

Do not invent tools or rename parameters. Signatures below match the live tools.

---

## Tool calling mode

### Must run inside Exec

`browser_navigate`, `browser_navigate_back`, `browser_tabs`, `browser_snapshot`, `browser_take_screenshot`, `browser_get_attribute`, `browser_get_input_value`, `browser_is_checked`, `browser_is_enabled`, `browser_is_visible`, `browser_console_messages`, `browser_network_requests`, `browser_search`, `browser_click`, `browser_type`, `browser_fill`, `browser_fill_form`, `browser_hover`, `browser_scroll`, `browser_press_key`, `browser_select_option`, `browser_drag`, `browser_upload_file`, `browser_handle_dialog`, `browser_evaluate`, `browser_wait_for`

### Must be a standalone tool call (never inside Exec)

Use `browser_waiting_for_user_interaction` only for CAPTCHAs, security confirmations, payment approvals, irreversible actions, or other steps requiring user judgment, and always call it standalone. Tool limitations, element-location failures, and click or drag failures do not justify user handoff; if bounded recovery attempts still cannot make progress, end the task, explain the blocker and the step the user must handle, and do not call this tool to wait for takeover.

---

## Exec runtime

Call Exec as:

```
run_mcp(server_name="integrated_code_mode", tool_name="Exec", args={"code": "<js>"})
```

`args` is a JSON object. The only accepted field is `code`. Other field names (`script`, `command`, `program`) are ignored and yield "code is empty".

Globals: `tools`, `text`, `exit`, `image`, `ALL_TOOLS`, plus standard ECMAScript builtins. No Node (`require`, `process`, `Buffer`), no page DOM (`document`, `window`), no `fetch`.

- `text(value)` — only way to show a result to the model. Top-level `return` is a SyntaxError. Pass **small** strings or JSON of extracted fields. Never `text()` a full accessibility tree, raw `network_requests`, or `document.body` unless you are stuck and need refs.
- `image(rawToolResult)` — screenshot reader. Pass the raw tool object (`__images`), never a path. Do not screenshot to "have a look".

Rules:

- Keep Browser calls sequential inside one Exec. Do not use `Promise.all` for Browser calls because runtimes differ and shared tab/ref state can race.
- Within one Exec, run deterministic operations that need no new page-state decision and retain valid refs, followed by their cheapest verification; return to the model only for an unknown ref, page branch, user handoff, failure recovery, terminal result, or batch checkpoint, rather than splitting a continuous flow into one action per Exec.
- Do not write polling loops or multi-minute waits inside one Exec.
- Tool errors reject the Promise — try/catch. `text()` before a crash is kept.
- Nested tool results are invisible until `text(...)`.

### Tool results

Browser tools usually return `{ content: [{ type: "text", text: string }], status: number }`; `status: 0` indicates success, and any other value indicates failure.

---

## Tool reference

Optional on almost every tool: `viewId` (omit = last interacted tab). `browser_tabs` uses positional `index`, not `viewId`.

### `browser_navigate`

`browser_navigate({ url, viewId?, newTab?, position?, extraHeaders? })`

- `url` must be `http://` or `https://`. Other schemes → `ERR_ACCESS_DENIED`.
- `position`: `"active"` | `"side"`.
- `newTab: true` may not focus the tab. If the next call has no `viewId`, `tabs list` + `activate` **in the same Exec**.
- `extraHeaders` last for the tab lifetime. `{}` clears.

### `browser_navigate_back`

`browser_navigate_back({ viewId? })`

### `browser_tabs`

`browser_tabs({ action, index? })` — `list` | `new` | `close` | `select` | `activate`. `index` is list position. `activate` foregrounds (needed for timers that pause in background).

When the target `index` is known, call `select` directly. Otherwise, call `list` first, confirm the target index, and then select it.

### `browser_snapshot`

`browser_snapshot({ viewId?, strategy?, maxDepth?, maxNodes?, includeIgnored?, interactive?, compact?, selector? })`

- Huge dashboards: always pass `compact: true` and consider `maxNodes`.

### `browser_take_screenshot`

`browser_take_screenshot({ filename?, fullPage?, ref?, viewId? })`

Use only when the tree cannot describe the pixels, then call `image(shot)`.

### `browser_get_attribute`

`browser_get_attribute({ ref, name, viewId? })`

Prefer one `browser_evaluate` over many `browser_get_attribute` calls.

### `browser_console_messages`

`browser_console_messages({ viewId? })`

### `browser_network_requests`

`browser_network_requests({ viewId? })`

Do not `text` the full list.

### `browser_click`

`browser_click({ ref, doubleClick?, button?, modifiers?, offsetX?, offsetY?, viewId? })`

- `button`: `"left"` | `"right"` | `"middle"`. `modifiers`: Alt / Control / Meta / Shift. Offsets from top-left; omit = center.

### `browser_type`

`browser_type({ ref, text, clear?, submit?, slowly?, viewId? })`

- Default appends. `clear: true` replaces. `submit: true` presses Enter.
- If an input does not accept `fill`, use `browser_type({ clear: true })`; use `slowly: true` only when normal typing still fails and the control depends on per-key events.

### `browser_fill`

`browser_fill({ ref, value, viewId? })`

Atomically clear and set the value.

### `browser_fill_form`

`browser_fill_form({ fields, viewId?, take_screenshot_afterwards? })`

- Preferred for 2+ fields. Field: `{ ref, value, clear? }` (`clear` defaults true).

### `browser_hover`

`browser_hover({ ref, viewId? })`

Take a compact snapshot before clicking a new menu item.

### `browser_scroll`

`browser_scroll({ ref?, direction?, amount?, deltaX?, deltaY?, scrollIntoView?, viewId? })`

- Omit `ref` to scroll the page. `direction`: up / down / left / right.

### `browser_press_key`

`browser_press_key({ key, viewId? })`

Targets the **focused** node. Click or fill first.

### `browser_select_option`

`browser_select_option({ ref, values, viewId? })`

Pass option **value** attributes, not visible labels. If the value is unknown, read the `<option>` list once with `browser_evaluate`, then select.

### `browser_drag`

`browser_drag({ sourceRef, targetRef?, targetX?, targetY?, viewId? })`

Use either `targetRef` or coordinates.

### `browser_upload_file`

`browser_upload_file({ ref, filePath, viewId? })`

`filePath` is local; `ref` is the file input.

### `browser_handle_dialog`

`browser_handle_dialog({ accept, promptText?, viewId? })`

Set `accept` to `true` to accept the dialog or `false` to dismiss it. When accepting a prompt, use `promptText` to enter its value. Call it before the click that opens a native alert, confirm, or prompt; do not retry the previous click.

### `browser_evaluate`

`browser_evaluate({ script, viewId? })`

- Field name is `script` (not `code` / `expression`). Use an explicit top-level `return`; the engine wraps scripts automatically, so do not add an IIFE.
- Use only to read and inspect the page; do not modify the DOM, click, submit, navigate, or make network requests.
- Guard missing nodes with `?.`. Return primitives or serializable plain objects directly; do not call `JSON.stringify` inside the script or return DOM nodes, `innerHTML`, or full-page text.
- Deduplicate extracted lists, and do not return both matched fields and a large text block containing the same content. Keep each result under 20KB to avoid producing truncated output that cannot be parsed. Return only fields needed for the current task; when later steps require a before-and-after comparison, the relevant baseline fields are required task data and must be preserved.

### `browser_wait_for`

`browser_wait_for({ text, timeout?, viewId? })` or `browser_wait_for({ textGone, timeout?, viewId? })`

- Wait for text to appear (`text`) or observed text to disappear (`textGone`). Provide exactly one non-empty condition.
- Use after navigation or an action when page results are still pending. Choose a real completion signal; if unknown, inspect the page first. Skip waiting if already complete.
- `timeout` caps the condition check in milliseconds; return occurs as soon as it is met. Never pass `timeout` alone.

---

## Hard rules

1. Click, type, fill, hover, select, and upload with a current `[ref=eN]`; use `browser_evaluate` only to read the page, never to modify it or trigger actions.
2. Keep actions in the same tab sequential; after navigation or a click, verify the result before continuing.
3. A successful tool call means only that the action ran, not that the requested outcome occurred; determine completion from the actual page state.
4. List or switch tabs only when needed; use `newTab: true` when multiple pages must remain open.
5. Iframes cannot be operated directly; open a known iframe URL in a new tab, otherwise stop.
6. Wait for page state with an explicit condition and time limit; do not use fixed sleeps, long polling, or repeated attempts without progress.
7. Do not output full snapshots, network logs, or screenshots, and do not inspect framework internals; return only the minimum information needed for the task.
8. Complete browser validation through real UI interactions and page evidence by default; call `SearchCodebase` at most once only when UI evidence suggests that a feature may not exist and source inspection is necessary for diagnosis, treat source findings as supplemental rather than a substitute for browser operations, and return to the UI to verify the final conclusion.

---

## Read and verify page state

Choose a tool based on the information you need rather than always preferring one method.

1. If the current page or an existing tool result already contains the required information, use it directly instead of navigating or reading the same information again. Stop searching or opening more pages once all fields required by the current task are covered.
2. When the field or DOM selector is known, use `browser_evaluate` to extract the required data.
3. When you need to operate an element but do not have a valid ref, take a snapshot:
   - If the target region is known, use `browser_snapshot({ selector: "form#checkout" })`.
   - If the target location is unknown, use `browser_snapshot({ compact: true, interactive: true })`.
   - Take a full snapshot only when those snapshots do not provide enough information.
4. When you have a valid ref, use `browser_get_input_value`, `browser_is_checked`, `browser_is_enabled`, or `browser_is_visible` to read the corresponding state.
5. Use `browser_evaluate` to inspect style values or element dimensions. Use `browser_take_screenshot` and `image()` only when you need to inspect final pixel output, Canvas, image content, or the overall visual presentation.

Return only the information needed for the current task. Do not output a full page snapshot, `document.body.innerText`, or complete network log. When later steps require comparison with an earlier page state, preserve stable identifiers and the relevant baseline fields in the structured result; do not discard prerequisite evidence merely to reduce the current output. When debugging information is necessary, filter the relevant portion using keywords, regular expressions, or field conditions, and limit both the number of results and the returned text length.

---

## Multiple tabs

1. Run browser calls sequentially; do not place them in `Promise.all`, which can cause conflicts in tab ownership and ref state.
2. When the current page already contains the required data, read or search it there instead of opening duplicate pages.
3. Use multiple tabs only when different targets have independent URLs and their page states must remain open.
4. Keep at most 3–4 agent-created temporary tabs open by default, and never close pre-existing or user-requested tabs. Call `browser_tabs({ action: "list" })` only when returning to an older tab; calls without `viewId` use the last interacted tab.

---

## Snapshot and refs

`[ref=eN]` die when their DOM region changes.

| Risk | Operations | Refs | Next |
|---|---|---|---|
| High | navigate, navigate_back, click that navigates | All stale | New compact snapshot before the next click |
| Medium | AJAX click, hover menu, select that rewrites the form | Region maybe stale | Re-snapshot that region if you must click it |
| Low | type, fill, fill_form, Tab/Enter, static select, scroll | Valid | Keep going |

Stale ref: compact snapshot, new ref, retry **once**. Do not reuse the dead ref.

---

## Waiting and progress checks

1. `browser_wait_for` returns as soon as its condition is met; `timeout` is only the maximum wait. Set a reasonable bound based on the page's expected response time and avoid unbounded waits.
2. Choose one signal that proves the page has finished changing: use `text` to wait for result text to appear, `textGone` to wait for loading text to disappear, or wait for a target element to reach the expected state. Do not wait on several conditions in sequence or use a root node that is always present to decide whether the page is ready. If there is no clear signal, take one compact snapshot to inspect the page state or error.
3. Read the result after navigation, and use at most one conditional wait if the page content has not appeared. Recheck after a click that changes page state. Fill, type, and static select operations usually need no wait; wait after scrolling only when it triggers lazy loading.
4. Do not use fixed sleeps. After a conditional wait times out, inspect the current page state before deciding whether to change the condition, continue, or stop; do not repeat the failed wait unchanged.
5. Record the current progress before waiting and check it again after each wait. If there is no progress twice in a row, stop and investigate; do not loop waits inside one Exec. Continue waiting only when the task itself requires real time to pass, such as video playback or a countdown.
6. After submitting a server-side asynchronous job such as an export, analysis, or build, record its task ID, current state, and completion signal. Perform only bounded status checks; if it is still incomplete, return the current progress instead of waiting or polling repeatedly.

---

## Batch tasks

1. Before a batch, complete one item end to end and verify that the workflow and completion condition work.
2. Process one item or a bounded small batch per Exec; after verification, update `done` and `pending`.
3. On resume or after a partial failure, process only `pending` or failed items. Do not repeat `done` items or rerun the whole batch; stop the batch and reassess if the same workflow keeps failing.
4. Return only structured fields needed for the current task through `text()`. When reading multiple pages, reduce each page to a fixed set of fields, then deduplicate and trim the whole batch; do not accumulate raw tool results, full text, or duplicate content. Preserve the corresponding stable identifiers and baseline fields when later comparison across pages or steps is required.

---

## Failure handling

1. After a tool fails, inspect the error and current page state, and return only the information needed to diagnose it.
2. For click, drag, screenshot, keypress, and similar trial-and-error sequences, use the current URL, key page state, and completed progress as a progress fingerprint; try the same action or observation pattern at most twice, and after two consecutive rounds with an unchanged fingerprint, take only one fresh snapshot and change strategy, then report the blocker immediately if progress still does not resume instead of continuing repetitions with no information gain.
3. If a ref is missing or stale, obtain a new ref and retry once; that retry still counts toward failures for the same objective.
4. After a Browser bridge or CDP timeout, select the intended tab again and retry once.
5. Only for `Invalid parameter` or `Unknown tool`, inspect that tool's definition in `ALL_TOOLS` and correct the call once.
6. After three consecutive failed Browser steps, summarize the blocker and change strategy.
7. At 10 Browser Exec calls for the same task or 3 wall-clock minutes, re-plan once from a progress fingerprint containing the current URL, key page state, and completed progress. Continue only when progress is verified and the hard limits have not been reached.
8. Hard limits are 30 Browser Exec calls or 10 wall-clock minutes. At either limit, finish the current atomic action, persist the checkpoint, and return the verified result or blocker. Extend only for an explicitly requested real-time workflow whose progress checks prove forward movement; ordinary unattended or batch work must checkpoint and stop.
9. When resuming after an interruption, read the current URL and completion state again. If continuity cannot be verified or recovery still fails, change strategy or report the blocker.
10. If a page overlay blocks the target, dismiss it once after confirming that it is safe, then inspect the page state again.
11. On a 403 response, stop and report it.
12. If the page is blank, take one compact snapshot to inspect its state. If it still has no content, inspect relevant console errors, then filter network requests only if needed.

---

## Safety

1. Never bypass or dismiss a CAPTCHA, security interstitial, challenge page, or "site not secure" warning; hand control to the user when human action is required.
2. Do not confirm irreversible account or data changes unless the user explicitly requested the action.

---

## Common operation examples

### Navigate, interact, and verify

1. When the fields to read are known, extract them after navigation:

```javascript
await tools.browser_navigate({ url: "https://example.com/report/a" });
const data = await tools.browser_evaluate({
  script: `return {
    url: location.href,
    title: document.title,
    h1: document.querySelector('h1')?.textContent?.trim() ?? ''
  }`
});
text(data?.content?.[0]?.text ?? data);
```

2. When the page structure is unknown or you need an interaction ref, take a compact interactive snapshot after navigation:

```javascript
await tools.browser_navigate({ url: "https://example.com" });
const snap = await tools.browser_snapshot({ compact: true, interactive: true });
text(snap);
```

3. When the result field is known after a click, read and verify it directly:

```javascript
await tools.browser_click({ ref: "e42" });
const result = await tools.browser_evaluate({
  script: `return {
    url: location.href,
    output: document.querySelector('.output')?.textContent?.trim() ?? ''
  }`
});
text(result?.content?.[0]?.text ?? result);
```

If the page structure changed and further interaction is needed, take another snapshot to obtain fresh refs:

```javascript
await tools.browser_click({ ref: "e42" });
const snap = await tools.browser_snapshot({ compact: true, interactive: true });
text(snap);
```

### Fill and submit a form

Prefer `browser_fill` or `browser_fill_form` for form fields. If a submitted value was not applied or the page did not respond, read the input value once to confirm, then use `browser_type({ clear: true })`. Use `slowly: true` only if normal typing still fails and the control depends on per-key events. Try each method once rather than repeating the same fill method.

```javascript
await tools.browser_fill_form({
  fields: [
    { ref: "e10", value: "Jane Doe" },
    { ref: "e12", value: "jane@example.com" }
  ]
});
await tools.browser_select_option({ ref: "e9", values: ["support"] });
await tools.browser_click({ ref: "e20" });

const result = await tools.browser_evaluate({
  script: `return document.querySelector('[role="alert"]')?.textContent?.trim() ?? ''`
});
text(result?.content?.[0]?.text ?? result);
```
