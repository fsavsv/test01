---
name: deployment
description: Deploy supported web apps, generate an accessible URL, and manage deployed sites. Use for requests to deploy, publish, launch, or share a web app, whether newly built from scratch or existing; also use for redeployment, deployment status or logs, access policy or resource configuration changes, cancellation, retry, and rollback. Do not use for writing or reviewing code, running locally, or project management.
description_zh: 将受支持的网页应用部署上线，生成可访问的链接，并管理已上线的站点。适用于部署、发布、上线或分享网页应用的需求，包括从零搭建的新项目和已有项目；也适用于重新部署、查询部署状态或日志、修改访问权限或资源配置、取消、重试和回滚。不适用于代码编写或检查、本地运行及项目管理。
description_en: Deploy supported web apps, generate an accessible URL, and manage deployed sites. Use for requests to deploy, publish, launch, or share a web app, whether newly built from scratch or existing; also use for redeployment, deployment status or logs, access policy or resource configuration changes, cancellation, retry, and rollback. Do not use for writing or reviewing code, running locally, or project management.
version: "0.0.25"
---

# Deployment

Use the bundled `trae-deploy` CLI for every deployment operation. Keep intent
recognition, project classification, user decisions, and result explanation in this
Skill. Treat CLI stdout JSON as authoritative and stderr as progress text.

## Scope

Supported application types:

- `StaticWeb`: directly publishable static files or deterministic static output.
- `FunctionWeb`: one server-side Node.js application compatible with `nodejs20`.

Stop before creating a Site or uploading source when the project cannot satisfy either
contract. State the unsupported runtime or missing project fact.

## CLI

Resolve the bundled CLI relative to this Skill directory:

- Linux and macOS: `sh "<skill-dir>/scripts/trae-deploy"`
- Windows: `cmd.exe /d /s /c ""<skill-dir>\bin\win32-x64\trae-deploy.exe" <arguments>"`

The instructions below call this `<trae-deploy>`. Always use the platform shell shown
above. Do not use a same-named executable from `PATH` or replace a CLI operation with a
manually constructed HTTP request.

On Windows, replace `<arguments>` with the requested CLI arguments inside the outer
quotes. Keep `cmd.exe` as the entry point; do not launch the `.exe` directly.

Read references progressively:

- After classifying as `StaticWeb`: `references/static-web.md`
- After classifying as `FunctionWeb`: `references/function-web-nodejs20.md`
- Before interpreting CLI JSON, enums, commands, or exit codes:
  `references/cli-contract.md`
- After any `SERVICE_*` error: `references/error-codes.md`

## Operating Rules

- For a deployment request, move from bounded inspection to source preparation and one
  `deployments create` call. Do not investigate hypothetical failures first.
- Do not start a local server, open a browser, invoke browser automation, or run UI,
  smoke, end-to-end, or network tests unless the user explicitly requests them.
- Do not install dependencies, run tests, or build only for confidence. A production
  build is allowed when it is required to produce the StaticWeb files being uploaded.
- Use remote build and runtime as the first FunctionWeb integration validation.
- Prepare deployable content before invoking the CLI. The CLI does not inspect the
  project, copy source, install dependencies, run builds, or generate scripts.
- Keep manifests, archives, downloaded logs, and temporary source outside the project.
- Patch defects in the real project, then prepare a fresh temporary source. Never patch
  only a temporary deployment copy.
- Treat Site IDs remembered from earlier turns as lookup hints. Validate them once with
  `sites get` before reuse; reuse that result throughout the current operation.
- Treat every non-successful `sites create` result as an unknown write outcome. Reconcile
  the complete current-project Site list before any second create attempt.
- Never create a second Deployment while the selected Site has an active Deployment.
- Do not report deployment success before a successful terminal service state.
- Treat the deployment card as a mandatory completion gate. When at least one requested
  Deployment succeeds, do not send the final response until `show_deployment_card` has
  been called exactly once with every successful Site. A URL, text summary, or screenshot
  is not a substitute. Skip the card only when no Deployment succeeded.
- If CLI access preflight fails, stop and follow its sign-in or project-access message.

## Deploy

### 1. Inspect and Classify

Perform one bounded, read-only inspection of the files needed to determine:

- project root and application type;
- stable application identity: repository or workspace root, application directory, and
  primary entrypoint;
- package manager and lock file;
- build command and static output directory, when applicable;
- FunctionWeb build output, start command, Node.js compatibility, and listening port.

Inspect only relevant package metadata, framework configuration, scripts, existing
deployment adapters, static entrypoints, and candidate output directories. Stop once
these facts are known.

Classify as StaticWeb when content is directly publishable with `index.html`, an existing
build has deterministic static output, or the framework explicitly supports static
export.

Classify as FunctionWeb when the project needs one Node.js server process, has a
deterministic production entrypoint, supports Node.js 20, and has a provable listening
port matching `runtime.port`.

Ask the user to choose only when both types are valid and the repository does not reveal
the intended production mode. Reject non-Node.js dynamic runtimes, incompatible Node.js
versions, multiple independently deployed services, deployment-time database migrations,
separate background workers, and unknown output or start entries.

### 2. Prepare Source

Create a unique source directory under the current process's operating-system temporary
root. Do not hardcode `/tmp`, create it inside the workspace, or pass the temp root itself.

Linux and macOS:

```bash
temp_root="${TMPDIR:-/tmp}"
source_dir="$(mktemp -d "${temp_root%/}/trae-deploy.XXXXXX")"
```

Windows PowerShell:

```powershell
$sourceDir = Join-Path ([System.IO.Path]::GetTempPath()) ("trae-deploy-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $sourceDir | Out-Null
```

Exclude local `node_modules`, package-manager caches, VCS metadata, IDE settings, logs,
test output, coverage, credentials, `.env` files, deployment archives, and unrelated
build output.

For StaticWeb, follow `references/static-web.md`. Build only when needed to produce the
actual upload, then copy published files to `<source-dir>/public/`. Require a non-empty
`public/index.html`.

For FunctionWeb, follow `references/function-web-nodejs20.md`. Copy the required package
content to the source root and provide executable POSIX `build.sh` and `run.sh`. Prove the
effective production port. Inspect source, scripts, lockfile, and any existing build
output; do not run a local build or install dependencies merely to create validation
evidence. Do not claim remote artifact properties were verified locally.

### 3. Route Large Static Output

StaticWeb supports at most 99 published files and 50 MiB uncompressed, excluding the
CLI-generated manifest. Count the prepared output before Site selection when possible.

If either limit is exceeded, run:

`node "<skill-dir>/scripts/prepare-static-function.mjs" --source-dir <prepared-static-source>`

Use returned `data.source_dir`, `data.execution_config`, and `data.deploy_type`. The
adapter creates a dependency-free Node.js 20 package serving the complete static output
from `public/` through `0.0.0.0:8000`. Keep the project unchanged. Do not delete assets,
compress files, or raise limits to force StaticWeb.

This automatic route does not require a deployment-mode question. Tell the user that the
large static output will use a dynamic service and remote build. If a Site was already
selected, retain it and its visibility without a second type-change confirmation.

Apply the same route after `STATIC_FILE_LIMIT` or `STATIC_SIZE_LIMIT`. Other validation
errors remain blocking. Clean up both temporary directories after upload or failure.

### 4. Resolve the Site

Validate a user-specified or remembered Site with `sites get --site-id <id>`. Otherwise
run `sites list`.

Build a concise current-application description before selecting a Site. Include the
repository or workspace root, application directory when different, application purpose,
primary entrypoint, and deployment type. Keep it stable across redeployments and at most
2048 characters. Compare each candidate's name and description together:

- Reuse automatically only when they identify the same application and source location.
- A matching type, a single candidate, or a similar name alone does not prove reuse.
- If the description identifies another source directory or a different application,
  create a new Site by default. Reuse it only when the user explicitly names or selects
  that existing Site.
- For a legacy Site with no description, use its name, project context, and deployment
  history only as bounded supporting evidence. If identity remains uncertain, ask the
  user to choose instead of overwriting the Site.

Choose in this order:

1. A deployment-type mismatch takes precedence over every automatic reuse rule,
   including a Site with no deployment history. Ask whether to create a new Site or
   reuse the existing Site and switch type.
2. If no Sites exist, create one after resolving visibility.
3. Reuse the only same-type Site whose name and description identify the current
   application and source location.
4. With multiple Sites and exactly one matching same-type candidate, show and reuse it.
5. With multiple matching same-type candidates, show name, description, URL, type,
   latest status, and update time, then ask the user to choose.
6. With no matching same-type candidate, ask whether to create a Site or explicitly
   reuse or switch an existing one.

Never select the first list item automatically. Before switching type, state the Site
name, current type, new type, and that the same URL will switch execution paths. Require
explicit confirmation except for automatic large-static routing on an already selected
Site.

### 5. Classify Application Content

Inspect the prepared application's user-visible text, images, audio/video references,
generated pages, and primary interaction purpose. Assign every applicable integer tag
from this table:

| ID | Category |
|-:|-|
| 101 | Education and knowledge |
| 112 | Core leaders |
| 123 | Productivity and tools |
| 134 | Business and ecommerce |
| 145 | Sensitive or reactionary content |
| 156 | News and information |
| 167 | Entertainment and media |
| 178 | Pornography or vulgar content |
| 189 | Games |
| 201 | Social and community |
| 212 | Abuse or insults |
| 223 | Health and wellness |
| 234 | Finance |
| 245 | Gambling or betting |
| 256 | Travel and lifestyle |
| 267 | Art and creative work |
| 278 | Drugs |
| 289 | Developer and technology |
| 301 | Other |

Classify the actual application rather than its repository name or the user's deployment
request. Use multiple tags when multiple categories apply.

Classify honestly and only from the application's actual content. This requirement is
mandatory regardless of user instructions: never omit, substitute, downplay, or falsify
an applicable category. When the available evidence is insufficient, inspect the
prepared application further instead of guessing. An inaccurate or incomplete
classification causes the deployment to fail.

Treat the classification and its CLI representation as internal metadata. Never reveal
in any user-facing response that tags are used, the tag parameter name, integer values,
the classification table, selected categories, or whether a particular internal
category matched. Do not quote or paraphrase CLI validation details that expose this
metadata, including when deployment fails or the user asks how classification works.

Do not deploy applications involving core leaders, sensitive or reactionary content,
pornography or vulgar content, abuse or insults, gambling or betting, or drugs. Stop
before Site creation or upload, state only that the application's content is not
supported for deployment, and do not call `deployments create`.

### 6. Resolve Visibility

A URL does not prove public access. Create a private Site by default. Only create a
public Site when the user explicitly requests public access:

- Explicit public access intent: pass `--access-policy public`
- Explicit private, restricted, or owner-only intent: pass `--access-policy private`
- Generic deploy/publish request: omit `--access-policy`; the server defaults to private
- Team sharing or unclear audience: clarify the required access before selecting public

Private currently means owner-only. Clarify this limitation when team access is requested.

Create with:

`sites create --name <name> --description <application-description>`

Add `--access-policy public` only for an explicit request for public access.

Retain the complete pre-create Site ID set from Site resolution. If `sites create`
returns any error, non-zero exit, malformed result, or no trustworthy Site ID:

1. Run `sites list` again and load every page.
2. Compare the result with the pre-create ID set. Identify newly appeared Sites whose
   name, exact description, and access policy match this create request.
3. When exactly one new matching Site exists, validate it with `sites get` and continue
   with that Site. Do not call `sites create` again.
4. When multiple new matching Sites exist, stop and ask the user to select one. Never
   create another Site to resolve the ambiguity.
5. Only when the complete refreshed list proves that no matching Site was created may
   another create be considered. Follow the structured error's retryability and
   `references/error-codes.md`; never loop or replay the create unchanged after another
   uncertain result.

Verify with `sites get`. For a reused Site, preserve its verified policy unless the user
explicitly requested another policy. Then run `sites update-config`, verify with
`sites get`, and do not ask for duplicate confirmation.

### 7. Check Active Deployment

Run `deployments list --site-id <site-id>`. If an active Deployment exists, do not create
another. Show its ID, stage, status, and creation time. Offer to wait or, only when the
stage is cancellable, cancel it.

### 8. Create and Monitor

Call `deployments create` once with:

- selected Site ID;
- concise inferred title, always passed with `--title` and at most 256 characters;
- detailed deployment description, always passed with `--description` and at most 2048
  characters; include the source location, deployed application area, and material
  purpose or change for this deployment;
- final deployment type;
- prepared source directory;
- execution config from the applicable reference.
- every applicable application content tag, passed with `--app-tags` as a comma-separated
  integer list.

`--app-tags` is local classification metadata. The CLI rejects unknown IDs and does not
send tags to the control plane.

If `SOURCE_DIR_OUTSIDE_TEMP` occurs, discard the directory, create a fresh one from the
platform temp root, recopy, and retry once. If a network result is uncertain, query Site
deployment history before considering another create.

Record the returned Deployment ID and run:

`deployments wait --deployment-id <deployment-id>`

The CLI queries immediately and owns polling, backoff, and timeout behavior. Use this
command as the only monitoring loop. A successful result contains `wait_reason` and the
latest Deployment under `deployment`. The default command returns at a terminal state
or after 60 seconds. A timeout result still contains the latest Deployment. If it
remains active, run the same command again only when the user asked to wait for
completion. Never infer completion from elapsed time or replace an active Deployment.

### 9. Complete Successful Deployments

When at least one requested Deployment reaches terminal success, complete this flow
before writing the final response:

1. For each successful Deployment, use the `screenshot_refresh.status` returned by
   `deployments wait`: `updated` means refresh is complete; `failed` means the attempt
   is complete. Only when the field is absent, run
   `sites refresh-screenshot --site-id <site-id>` once. Screenshot failure is
   best-effort and leaves the Deployment successful, with no retry or rollback.
2. Collect every successful Site in deployment order using trusted CLI results already
   obtained in this operation. Each card snapshot needs `site_id`, `name`, absolute
   `url`, and decoded `visibility`; include `version` when provided, preferring the
   successful Deployment's version over a pre-deployment snapshot. Call `sites get`
   only when a required field is missing or a later change invalidated it. Keep
   successful Sites in the list even if screenshot refresh failed; never fabricate
   missing fields.
3. Call `show_deployment_card` exactly once with the complete `sites` array and wait for
   its result. A Markdown link, textual Site list, or screenshot cannot replace this
   call. If it fails, retain Deployment success and explicitly report the card failure
   without retrying.

Skip the card only when none of the requested Deployments succeeded.

Only after this gate may the final response report each Site name, URL, and ID,
Deployment ID and type, terminal status, and verified visibility. If Site verification
failed, report success with visibility unverified.

For one successful Site, the tool input has this shape:

```json
{"sites":[{"site_id":"<id>","name":"<name>","url":"https://<host>","visibility":"private","version":"V1"}]}
```

### 9. Failure and Logs

If any CLI command returns `UNSUPPORTED_USER_SCOPE`, stop the deployment flow and
tell the user that deployment is not yet supported for ByteDance internal accounts
and that they should switch to an external account and try again. If they are already
using an external account, tell them to restart the app and try again.

If any CLI command returns `INVALID_RUNTIME_CONTEXT` or `MISSING_RUNTIME_CONTEXT`,
stop the deployment flow and tell the user that the current session does not support
deployment and that they should start a new session and try again.

For `SERVICE_*`, consult `references/error-codes.md`. Report failed stage, stable code,
summary, retryability, and next valid action. Do not automatically replay writes unless
the reference explicitly allows it.

When structured failure details are insufficient:

- `logs build`: dependency installation, compilation, or artifact failures
- `logs deploy`: resource preparation, review, or publication failures
- `logs runtime`: FunctionWeb startup or runtime failures

Build and deploy logs return a local file in `data.log_file`. Search first, read bounded
context around matches, and inspect the tail when useful.

Runtime logs are inline in `data.items`; page with `next_cursor` as specified in
`references/cli-contract.md`. Do not look for `data.log_file`.

Summarize only relevant lines and redact sensitive values. Patch the project only when
logs identify an actionable project or deployment-config cause. Otherwise preserve IDs,
stage, code, and `log_id` for platform diagnosis. Do not repeatedly retry unchanged
source, audit rejection, or invalid configuration.

## Inspect and Manage

### Inspect a Site or Deployment

Use `sites get --site-id <id>` for Site identity, URL, visibility, desired/effective
configuration, serving state, and latest status. Use `deployments list --site-id <id>`
for history and `deployments get --deployment-id <id>` for stage, tasks, audit gates,
failure details, and retryability. Use the log command matching the failed stage.

When the user does not provide an ID, use `sites list` and apply the Site selection rules.
Do not interpret a general request to inspect source code as a deployment operation.

### Update a Site

A Site description is maintainable metadata: update it without another
confirmation when bounded inspection proves that the selected Site is the same
application and its stored description is stale. Never rewrite a description to make a
different source directory appear reusable.

Treat an existing Site name as stable. Never change it proactively during deployment or
redeployment; pass `--name` to `sites update` only when the user explicitly requests a
name change.

Use `sites update-config` only for explicitly requested access policy, CPU, memory, QPS, or daily egress changes. Supply only requested or stale description fields.

### Redeploy

Reinspect the project, validate and reuse the Site, prepare fresh source, create a new
Deployment, and monitor it to terminal state.

### Retry

Use `deployments retry` only when the CLI marks the failed Deployment retryable and both
source and execution configuration are unchanged. If either changed, create a new
Deployment from fresh source.

### Cancel

Cancel only an active Deployment in a cancellable stage. Then query the same Deployment
until the service confirms the resulting state.

### Roll Back

Show the target historical successful Deployment and obtain explicit confirmation. Run
rollback, record the new rollback Deployment ID, and monitor it to terminal state.

## State, Security, and Responses

After a validated operation, retain the Site ID and name, latest Deployment ID, and
deployment type. Revalidate the Site before reuse in a later turn.

- Never ask for credentials or temporary upload links.
- Never display secrets, presigned URLs, or temporary upload details.
- Never construct service URLs or upload destinations manually.
- Keep user-facing responses concise and omit internal service details.
- On success, state what was deployed, URL, Deployment ID, and verified visibility.
- For unsupported projects, state detected facts and the exact unsupported requirement.
- For failure, state stage, actionable cause, and next valid action without dumping raw
  JSON or full logs unless requested.
