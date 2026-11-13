# Trae disk storage manual

This document records Trae disk-storage facts only. It does not define environment detection, disk-scanning commands, diagnosis flow, ranking, or answer format.

## Path placeholders

| Placeholder | Meaning |
|---|---|
| `<HOME>` | Home directory of the user on the machine being examined. |
| `<USER_DATA>` | Resolved local Trae product-data directory for the installed product, region, channel, and build. |
| `<EXTENSIONS>` | Resolved user-installed extensions directory for the examined local or remote Trae environment. |
| `<REMOTE_DATA>` | Remote SSH server-data root selected by the connected Trae product. |

Do not treat an entire platform parent such as macOS `Application Support`, Windows `%APPDATA%`, or Linux configuration roots as Trae data. Resolve the product-specific child first.

### Resolving `<USER_DATA>`

Resolve the actual local product-data directory in this order:

1. If `VSCODE_PORTABLE` is set, use `<VSCODE_PORTABLE>/user-data`.
2. Otherwise, if `VSCODE_APPDATA` is set, use `<VSCODE_APPDATA>/<PRODUCT_NAME>`.
3. Otherwise, if the running product was started with `--user-data-dir`, use that explicit path.
4. Otherwise, use the platform default:

| Platform | Default `<USER_DATA>` |
|---|---|
| macOS | `<HOME>/Library/Application Support/<PRODUCT_NAME>` |
| Windows | `%APPDATA%\<PRODUCT_NAME>`; if `%APPDATA%` is unavailable, use `%USERPROFILE%\AppData\Roaming\<PRODUCT_NAME>` |
| Linux | `${XDG_CONFIG_HOME:-<HOME>/.config}/<PRODUCT_NAME>` |

`<PRODUCT_NAME>` is the installed product's actual name, including its region, channel, or build suffix. For example, the default Linux path for **Trae CN** is `<HOME>/.config/Trae CN` when `XDG_CONFIG_HOME` is not set.

Prefer an explicit path visible in the current process arguments or environment over a platform default. Confirm the resolved directory exists and belongs to the examined Trae installation before applying any cleanup rule.

## Ownership and accounting

- Count every path confirmed to be written by Trae as Trae disk usage, regardless of its location or whether it can be cleaned safely.
- Include `<HOME>/.trae-aicc`, `<HOME>/.trae-aicc-internal`, `<HOME>/.git-ai`, and their descendants in Trae disk usage.
- Keep unknown ownership separate. A name containing `trae`, `ai`, `git`, `cache`, or `vm` is not proof of ownership.
- Do not count a parent together with its child. Displayed non-overlapping components must reconcile with the reported total, allowing normal rounding differences.

Cleanability is independent of ownership and accounting.

## Confirmed cleanup rules

| Exact path or category | Purpose | Cleanup fact |
|---|---|---|
| `<USER_DATA>/logs` / **Log Files** | Local Trae logs | Clean through Resources Explorer. |
| `<USER_DATA>/ModularData/ckg_server` and `<USER_DATA>/User/globalStorage/.ckg/storage` / **CKG Index Storage** | CKG index databases | Clean through Resources Explorer. Do not delete arbitrary files from their parent directories. |
| `<USER_DATA>/ModularData/ai-agent/snapshot` / **Chat Snapshot Files** | AI session snapshots | Clean through Resources Explorer so product metadata stays consistent. |
| `<EXTENSIONS>` | User-installed extensions | Uninstall only selected, unneeded extensions through the corresponding local or Remote SSH section of the Extensions UI. Do not delete the whole extensions root. |
| `<USER_DATA>/VMCache` | Local Trae VM cache | The exact resolved directory can be deleted directly without using a product cleanup action. Do not generalize this rule to another path containing `VM` or `cache`. |
| A plugin-exclusive child inside `<USER_DATA>/User/workspaceStorage/<workspace-id>` | Per-workspace data written by one installed extension | Consider deleting only the confirmed plugin-exclusive child, or uninstalling the unneeded extension through the Extensions UI. Warn that cleanup may remove that extension's workspace state, indexes, caches, history, or other data and may require regeneration or reconfiguration. Never delete the workspace entry or the whole `workspaceStorage` root. |

These are the only confirmed user-cleanable Trae paths or categories in this manual.

For `workspaceStorage`, require direct ownership evidence before applying the exception. A child named with the extension identifier, such as `redhat.java`, is useful evidence only after confirming that the identifier matches an installed extension and that the measured files are contained within that child. A hash-like `<workspace-id>`, `workspace.json`, `state.vscdb`, or proximity to a plugin directory is not sufficient evidence. If ownership is unclear or the large data is shared at the workspace-entry level, treat it as not safely deletable.

### Resources Explorer route

1. Open the Command Palette.
2. Run **Help: TRAE Process Explorer**.
3. Open **Resources Explorer → Disk**.
4. Select **Log Files**, **CKG Index Storage**, or **Chat Snapshot Files** and use the cleanup action shown by the product.

**Others** is not an equivalent cleanup category.

Any Trae-written path not listed in a confirmed cleanup table cannot be safely deleted. Do not infer an exception from names such as ShipIt, updater, Dev, LOCAL, preview, inactive-instance, `cache`, `snapshot`, `storage`, `temp`, `vm`, or `data`.

## Remote SSH server roots

The connected product selects one remote server-data root under `<HOME>`:

| Product | `<REMOTE_DATA>` |
|---|---|
| Trae CN | `<HOME>/.trae-cn-server` |
| Trae | `<HOME>/.trae-server` |
| TRAE SOLO CN | `<HOME>/.trae-solo-cn-server` |
| TRAE SOLO | `<HOME>/.trae-solo-server` |
| TRAE CN Enterprise | `<HOME>/.trae-cn-enterprise-server` |
| TRAE SOLO CN Enterprise | `<HOME>/.trae-solo-cn-enterprise-server` |

Use the root that actually exists for the connected product. Do not combine several roots unless each is confirmed to belong to a real installation on that host.

## Confirmed Remote SSH cleanup rules

| Path | Purpose | Cleanup fact |
|---|---|---|
| `<REMOTE_DATA>/extensions` | Extensions installed on the remote host | Uninstall selected user extensions through the Remote SSH section of the Extensions UI. Do not delete the whole directory. |
| `<REMOTE_DATA>/data/logs/<session>` | Remote server session logs | Old, inactive session directories can be deleted. Never delete the active session. The product normally removes empty/old sessions and retains roughly the ten most recent sessions. |
| `<REMOTE_DATA>/manager-logs/<connection-session>` | Remote connection-manager logs | Old, inactive session directories and `alog_*` temporary directories can be deleted. Never delete the active session. The product normally removes these automatically and retains roughly the ten most recent sessions. |

These are the only confirmed user-cleanable paths under `<REMOTE_DATA>`. Every other path under the remote root cannot be safely deleted, even if its name suggests a runtime, old version, cache, log, temporary file, PID, token, or installation lock.
