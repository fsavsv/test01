---
name: plugin-discovery
x-trae-main-agent-only: true
description: Discover and recommend suitable plugins when the user's task needs an external app, service, or capability unavailable through built-in or already connected tools.
---

# Plugin discovery

## Scope

This skill discovers and recommends plugins. It does not directly install, enable, disable, uninstall, or authorize plugins. Installation and connection are user actions in the recommendation card through the existing host flows. Do not treat a recommendation as permission to perform management operations.

For an explicit plugin-management request, use an available tool that actually supports the requested operation; do not invent a management tool or substitute another recommendation for the requested action.

## When to discover

Use an available built-in capability first, then an already installed and connected plugin. If those cannot fulfill the task, discover a suitable integration early when the user asks to use an external app, access account data, or perform a specialized workflow. The user does not need to say “plugin”. Examples: “How can I test APIs with Postman?”, “List my files in Tencent Docs”, or “Read my Figma design files”.

Search before substituting a long manual tutorial, inspecting unrelated project files, writing a custom integration script, opening a browser login flow, or asking the user to paste account data. If discovery is unavailable or no result supports the task, explain that and continue with available tools or an appropriate manual fallback. Web and scripts remain valid fallbacks; they are not banned.

Do not search merely because the topic mentions an app or an API. Pure conceptual questions, syntax explanations, or tasks fully supported by connected tools do not need plugin discovery. Loading this skill never requires recommending a plugin: first verify task fit.

## Build a search query

Translate the task into search keywords before calling `search_plugins`:

- If the user names a provider or product, search its name first (for example, `Postman` or `Figma`). Keep the brand; do not append the whole task or substitute another provider. Add a capability term only when needed to distinguish results. If the named provider is not found, the second search may use a known alias or localized name for the same provider (for example, `腾讯文档` → `Tencent Docs`), not a different provider or a generic category.
- Without a named provider, extract one core capability into about 2–4 keywords, such as `API testing debugging` or `database table schema`. Do not guess a brand merely to obtain results. Search separate capabilities separately only when each is necessary for the task.
- Omit conversational wording (such as “help me” or “are there any problems”), unrelated project context, secrets, personal information, file contents and concrete account/resource IDs. Do not turn the entire user request into a query.
- Read the returned descriptions to check task fit. If there is no suitable result, make at most one additional search. First narrow to the most specific capability phrase in the same language (`database table schema` → `table schema`), dropping broad action words such as `query` or `manage`. Use a common synonym or language variant only when it fits the catalog language or the first query already expresses the narrow capability; do not translate to English automatically. Do not change an explicitly requested provider to get a match. Stop after two searches for the same capability; do not broaden repeatedly until something appears.

Examples (query construction, not an instruction to recommend a particular plugin):

| User task | First query | Optional second query if no suitable result |
| --- | --- | --- |
| Test an API with Postman | `Postman` | `Postman API` |
| Help me check an API for problems | `API testing debugging` | `API testing` |
| Manage API collections and environment variables | `API collections environment variables` | `collections environments` |
| Check CI for a GitHub pull request | `GitHub` | `GitHub CI` |
| View database table schemas | `database table schema` | `table schema` |

Keyword search is not semantic understanding: a result may match only part of a query. A matching name or high rank alone does not establish suitability. If the descriptions do not support the requested capability, do not recommend; explain the gap and continue independent work.

Search results include a verified `installed` field. Prefer usable installed capabilities; do not recommend an installed plugin for another installation. Installed does not mean connected or authorized: check available state and tools before claiming access. Never invent IDs or treat the currently loaded tool list as a complete directory.

Search may also return a sparse sibling `suggestion_history` list, keyed by `registry` and `plugin_id`. `last_suggested_at` is the latest accepted suggestion time; `recent_suggestion_count` counts accepted suggestions over the past 7 × 24 hours. Unless the user explicitly asks for that plugin again, do not recommend it again within 7 days. Use the history to decide, not as proof that the user saw, installed, or authorized a plugin. Missing history means no recorded history was returned, not that every past recommendation is known.

## Suggest and continue

When mentioning a plugin to the user, prefer the name from its returned `i18n.display_name` map matching the current conversation language (`zh-cn` for Chinese, `en` for English, `ja` for Japanese); the top-level `display_name` is not automatically localized. For example, in Chinese, use `i18n.display_name["zh-cn"]` such as `腾讯文档`. If that translation is unavailable, use the existing `display_name` or `name`.

When an uninstalled plugin materially helps, call `suggest_plugins` with exactly one entry: the exact `plugin_id` from search and a short reason tied to the user's task and the returned capabilities. Searching can return multiple alternatives; recommending cannot. For a request comparing Postman and Vercel, search as needed, compare their actual capabilities, and choose at most one best fit to recommend. Do not force a recommendation if the task does not establish a useful choice.

Recommend at most one plugin for the same user request. Do not split an oversized batch into repeated one-plugin calls or resend a recent card. Accept a rejected or suppressed result without choosing another plugin solely to bypass it. Recommendation history is not guaranteed to be enforced by the host; follow these limits yourself.

A suggestion is optional and never blocks independent work. Continue the task as far as available tools allow. The card uses the existing installation and authorization flows. Installation and authorization do not fill the input. Only clicking the card’s Use action requests a draft in the original conversation; only the user sends it. Never claim installation or authorization succeeded without verified state, and only use newly connected capabilities after they become available. Do not request host tokens, service metadata or credentials as model-visible content. These tools belong to the Main Agent; do not delegate discovery or recommendation to a subagent.

Use only tools actually exposed in the current session. If the host does not expose discovery, do not invent a tool, bypass it with manual HTTP, inspect login files, or ask the user for a token. Continue with available capabilities and explain the missing integration when it affects the task.
