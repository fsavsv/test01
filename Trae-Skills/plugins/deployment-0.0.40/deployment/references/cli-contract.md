# Deployment CLI Contract

The Skill recommends FunctionWeb when static output exceeds 99 published files,
excluding the generated manifest, and follows the bundled adapter workflow.
This workflow threshold does not describe service upload quotas.
Upload admission is controlled by the service. Preserve CLI error messages and
available `error.details`, including filenames, actual sizes/counts and limits.
Validation failures are blocking; do not change deployment type to bypass them.

Use the CLI bundled with this Skill through the platform shell:

- Linux and macOS: `sh "<skill-dir>/scripts/trae-deploy"`
- Windows: `cmd.exe /d /s /c ""<skill-dir>\bin\win32-x64\trae-deploy.exe" <arguments>"`

Resolve `<skill-dir>` from the loaded Skill location. This document refers to the selected
command as `<trae-deploy>`. Do not call another executable with the same name from the
workspace `PATH`.

On Windows, replace `<arguments>` with the requested CLI arguments inside the outer
quotes. Keep `cmd.exe` as the entry point; do not launch the `.exe` directly.

## Output

The CLI writes:

- one JSON result to stdout; and
- short progress messages to stderr.

Parse stdout as the command result. Do not parse progress text as state.

Successful result:

```json
{
  "ok": true,
  "data": {},
  "log_id": "request log identifier"
}
```

Build and deploy log commands return a local file descriptor:

```json
{
  "ok": true,
  "data": {
    "log_type": "build",
    "log_file": "/absolute/system-temp/trae-deploy/session/deployment/build.log",
    "size_bytes": 1048576,
    "sha256": "hex digest"
  },
  "log_id": "request log identifier"
}
```

Runtime log commands return entries inline rather than a local file:

```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "timestamp_ms": 1735689600000,
        "content": "server started",
        "stream": "stdout",
        "revision_number": 3
      }
    ],
    "next_cursor": "",
    "query_start_time_ms": 1735686000000
  },
  "log_id": "request log identifier"
}
```

Failed result:

```json
{
  "ok": false,
  "error": {
    "code": "STABLE_ERROR_CODE",
    "message": "human-readable summary",
    "retryable": false,
    "details": {}
  },
  "log_id": "request log identifier"
}
```

Use `error.code`, `error.retryable`, and structured `details` for decisions. Use
`error.message` for the user-facing summary.

## Exit Codes

| Exit code | Meaning |
|-|-|
| `0` | Command completed successfully |
| `2` | Invalid command input or local source contract |
| `3` | Deployment access is unavailable |
| `4` | The deployment service rejected the operation |
| `5` | Temporary network or service failure |
| `6` | The monitored Deployment reached a failed, cancelled, or timed-out result |

The JSON result is authoritative when both JSON and an exit code are available.

## Commands

Site lifecycle commands:

```text
<trae-deploy> sites pause --site-id ID
<trae-deploy> sites resume --site-id ID
<trae-deploy> sites delete --site-id ID
```

All three commands are high-risk operations and must never be selected as an automatic
recovery or cleanup action. Immediately before running any of them:

1. Run `sites get --site-id ID`.
2. Show the user the exact Site name, URL, ID, current status, requested operation, and
   its impact.
3. Obtain explicit user agreement for that specific Site and operation.

A general request to deploy, fix an error, free quota, clean up, or manage Sites is not
agreement. Prior agreement for another Site or another lifecycle operation is not
transferable. If explicit agreement is absent or ambiguous, do not run the command.
After an authorized operation, verify the resulting state with `sites get`.

`sites delete` removes the service. The control plane first withdraws any active route
and releases provider resources, then hides the Site target while retaining deployment
history.

### Enum Reference

CLI arguments use the canonical text tokens below. The CLI converts them to the stable
integer codes required by the control plane. Never pass a raw integer to a CLI enum
argument. Repeat list filter flags to select multiple values, for example:

`deployments list --site-id ID --status building --status deploying`

Control-plane JSON fields remain integers. Decode every enum field with this table.
`response-only` means the value can appear in JSON but must not be passed as a CLI
argument. Code `0` is always an unknown compatibility value and is invalid in requests.

| Enum | JSON field | CLI token | Integer | Meaning |
|-|-|-|-|-|
| `DeployType` | `deploy_type` | `response-only` | `0` | Unknown; reject in requests |
| `DeployType` | `deploy_type` | `static-web` | `1` | Static files published from `public/` |
| `DeployType` | `deploy_type` | `function-web` | `2` | Node.js 20 server application |
| `DeployTargetType` | `target_type` | `response-only` | `1` | Site target; currently the only target type |
| `DeployTargetAccessPolicy` | `access_policy` | `response-only` | `0` | Unknown; reject in requests |
| `DeployTargetAccessPolicy` | `access_policy` | `private` | `1` | Only the owner can access the site |
| `DeployTargetAccessPolicy` | `access_policy` | `public` | `2` | Public site access |
| `DeployTargetDisplayStatus` | `display_status` | `response-only` | `0` | Unknown derived target status |
| `DeployTargetDisplayStatus` | `display_status` | `not-deployed` | `1` | Target has no completed deployment |
| `DeployTargetDisplayStatus` | `display_status` | `deploying` | `2` | Target has an active deployment |
| `DeployTargetDisplayStatus` | `display_status` | `online` | `3` | Current release is online |
| `DeployTargetDisplayStatus` | `display_status` | `paused` | `4` | Current release is paused |
| `DeployTargetDisplayStatus` | `display_status` | `offlining` | `5` | Target is being taken offline |
| `DeployTargetDisplayStatus` | `display_status` | `offline` | `6` | Target is offline |
| `DeployTargetDisplayStatus` | `display_status` | `failed` | `7` | Latest target operation failed |
| `DeploymentOperationType` | `operation_type` | `response-only` | `0` | Unknown; reject in filters |
| `DeploymentOperationType` | `operation_type` | `deploy` | `1` | Normal deployment |
| `DeploymentOperationType` | `operation_type` | `rollback` | `2` | Rollback deployment |
| `DeploymentOperationType` | `operation_type` | `offline` | `3` | Offline operation |
| `DeploymentStatus` | `status` | `response-only` | `0` | Unknown; reject in filters |
| `DeploymentStatus` | `status` | `pending-build` | `1` | Waiting to start build processing |
| `DeploymentStatus` | `status` | `building` | `2` | Build stage is running |
| `DeploymentStatus` | `status` | `waiting-deploy-artifact-audit` | `3` | Waiting for source or artifact audit |
| `DeploymentStatus` | `status` | `deploying` | `4` | Resource preparation is running |
| `DeploymentStatus` | `status` | `waiting-url-audit` | `5` | Waiting for deployed URL audit |
| `DeploymentStatus` | `status` | `publishing` | `6` | Publishing the release |
| `DeploymentStatus` | `status` | `offlining` | `7` | Removing the release from service |
| `DeploymentStatus` | `status` | `releasing` | `8` | Releasing provider resources |
| `DeploymentStatus` | `status` | `succeeded` | `9` | Terminal success |
| `DeploymentStatus` | `status` | `failed` | `10` | Terminal failure |
| `DeploymentStatus` | `status` | `cancelled` | `11` | Terminal cancellation |
| `DeploymentStatus` | `status` | `promoting` | `12` | Promoting the prepared resource |
| `DeploymentStageType` | `current_stage`, `tasks[].stage_type` | `response-only` | `0` | Unknown stage |
| `DeploymentStageType` | `current_stage`, `tasks[].stage_type` | `response-only` | `1` | Build |
| `DeploymentStageType` | `current_stage`, `tasks[].stage_type` | `response-only` | `2` | Deploy |
| `DeploymentStageType` | `current_stage`, `tasks[].stage_type` | `response-only` | `3` | Publish |
| `DeploymentStageType` | `current_stage`, `tasks[].stage_type` | `response-only` | `4` | Release |
| `DeploymentStageType` | `current_stage` | `response-only` | `5` | Deploy artifact audit |
| `DeploymentStageType` | `current_stage` | `response-only` | `6` | URL audit |
| `DeploymentStageType` | `current_stage`, `tasks[].stage_type` | `response-only` | `7` | Promote |
| `DeploymentTaskStatus` | `tasks[].status` | `response-only` | `0` | Unknown task status |
| `DeploymentTaskStatus` | `tasks[].status` | `response-only` | `1` | Pending |
| `DeploymentTaskStatus` | `tasks[].status` | `response-only` | `2` | Running |
| `DeploymentTaskStatus` | `tasks[].status` | `response-only` | `3` | Reconciling an external job |
| `DeploymentTaskStatus` | `tasks[].status` | `response-only` | `4` | Succeeded |
| `DeploymentTaskStatus` | `tasks[].status` | `response-only` | `5` | Skipped |
| `DeploymentTaskStatus` | `tasks[].status` | `response-only` | `6` | Failed |
| `DeploymentTaskStatus` | `tasks[].status` | `response-only` | `7` | Cancellation requested |
| `DeploymentTaskStatus` | `tasks[].status` | `response-only` | `8` | Cancelled |
| `DeploymentExecutionMode` | `tasks[].execution_mode` | `response-only` | `0` | Unknown execution mode |
| `DeploymentExecutionMode` | `tasks[].execution_mode` | `response-only` | `1` | Stage is skipped |
| `DeploymentExecutionMode` | `tasks[].execution_mode` | `response-only` | `2` | Control-plane internal execution |
| `DeploymentExecutionMode` | `tasks[].execution_mode` | `response-only` | `3` | Provider external job |
| `DeployReleaseStatus` | `serving_status`, `deploy_target_release.release_status` | `response-only` | `0` | Unknown release status |
| `DeployReleaseStatus` | `serving_status`, `deploy_target_release.release_status` | `response-only` | `1` | Online |
| `DeployReleaseStatus` | `serving_status`, `deploy_target_release.release_status` | `response-only` | `2` | Paused |
| `DeployReleaseStatus` | `serving_status`, `deploy_target_release.release_status` | `response-only` | `3` | Offlining |
| `DeployReleaseStatus` | `serving_status`, `deploy_target_release.release_status` | `response-only` | `4` | Offline |
| `DeployResourceType` | `resource_type` | `response-only` | `0` | Unknown resource snapshot |
| `DeployResourceType` | `resource_type` | `response-only` | `1` | Audit resource snapshot |
| `DeployResourceType` | `resource_type` | `response-only` | `2` | Production resource snapshot |
| `DeployConfigApplyStatus` | `config_apply_status` | `response-only` | `0` | Unknown config application status |
| `DeployConfigApplyStatus` | `config_apply_status` | `response-only` | `1` | Desired config is applied |
| `DeployConfigApplyStatus` | `config_apply_status` | `response-only` | `2` | Desired config requires redeployment |
| `DeploymentAuditGateType` | `audit_gates[].gate_type` | `response-only` | `0` | Unknown audit gate |
| `DeploymentAuditGateType` | `audit_gates[].gate_type` | `response-only` | `1` | Source or artifact audit gate |
| `DeploymentAuditGateType` | `audit_gates[].gate_type` | `response-only` | `2` | Deployed URL audit gate |
| `DeploymentAuditDecision` | `audit_gates[].decision` | `response-only` | `0` | Unknown audit decision |
| `DeploymentAuditDecision` | `audit_gates[].decision` | `response-only` | `1` | Pending |
| `DeploymentAuditDecision` | `audit_gates[].decision` | `response-only` | `2` | Approved |
| `DeploymentAuditDecision` | `audit_gates[].decision` | `response-only` | `3` | Requires manual review |
| `DeploymentAuditDecision` | `audit_gates[].decision` | `response-only` | `4` | Rejected |
| `DeploymentAuditDecision` | `audit_gates[].decision` | `response-only` | `5` | Audit execution failed |
| `DeploymentAuditDecision` | `audit_gates[].decision` | `response-only` | `6` | Audit result expired |
| `DeploymentAuditDecision` | `audit_gates[].decision` | `response-only` | `7` | Gate skipped |

Audit stages are aggregate Deployment states backed by `audit_gates`; the control plane
does not create synthetic audit Tasks. Therefore `tasks[].stage_type` uses Build,
Deploy, Publish, Release, or Promote, but not codes `5` or `6`.

The control plane has an internal security-suspension release state. User-facing APIs
normalize it to `DeployReleaseStatus=2` and `DeployTargetDisplayStatus=4`, both shown as
Paused. Integer `5` is not part of the public `DeployReleaseStatus` contract.

### Sites

- `sites list [--current-session] [--page-no PAGE_NO] [--page-size PAGE_SIZE] [--access-policy POLICY] [--display-status STATUS]`
- `sites quota`
- `sites get --site-id ID`
- `sites create --name NAME [--description DESCRIPTION] [--access-policy POLICY]`
- `sites update --site-id ID [--name NAME] [--description DESCRIPTION]`
- `sites update-config --site-id ID [--access-policy POLICY] [--cpu-millicores VALUE] [--memory-bytes VALUE] [--qps-limit VALUE] [--daily-egress-limit-bytes VALUE]`
- `sites pause --site-id ID`
- `sites resume --site-id ID`
- `sites delete --site-id ID`
- `sites refresh-screenshot --site-id ID`

### Deployments

- `deployments list --site-id ID [--page-no PAGE_NO] [--page-size PAGE_SIZE] [--status STATUS] [--operation OPERATION] [--type TYPE]`
- `deployments get --deployment-id ID`
- `deployments create --site-id ID [--title TITLE] [--description DESCRIPTION] --type TYPE --source-dir DIR --execution-config FILE --app-tags TAG[,TAG...]`
- `deployments cancel --deployment-id ID`
- `deployments retry --deployment-id ID`
- `deployments rollback --site-id ID --deployment-id ID`

### Logs

- `logs build --deployment-id ID`
- `logs deploy --deployment-id ID`
- `logs runtime --site-id ID [--since DURATION | --start-time-ms TIMESTAMP] [--end-time-ms TIMESTAMP] [--keyword TEXT] [--stream stdout|stderr] [--limit LIMIT] [--cursor CURSOR]`

## Command Rules

Every command validates the trusted project context and deployment access before
performing its operation. When this preflight fails, the command returns exit code `3`
and a structured error. Stop and follow the CLI's user-facing sign-in or project-access
instruction.

### sites list

Use when no validated site ID is available. The response contains `page_no`, `page_size`,
and `total_pages`. Increment `page_no` until the current page reaches `total_pages`.
`--access-policy` and `--display-status` are repeatable and accept only the canonical
tokens in the enum table.

Without an explicit scope option, the CLI lists Sites in the current project. The shared
default Project is the exception: it lists only Sites created by the current chat
session so Sites from unrelated sessions are not mixed into the result.

Use `--current-session` to explicitly list only Sites created by the current chat
session, regardless of whether the current Project is shared or ordinary.

`--all` lists every Site visible to the current account across Projects and sessions.
The option is intentionally hidden from CLI help. Never use it autonomously. Use it
only when the user explicitly requests an all-Site view; otherwise explain that it
broadens the query beyond the current Project and session, then obtain explicit user
confirmation before invoking it. `--all` and `--current-session` are mutually exclusive.

### sites quota

Returns separate Site and deployment-resource quotas for the current account.
`site_count`, `site_limit`, and `site_remaining` describe Site capacity.
`resource_count` is the number of occupied `(site, deploy_type)` resources,
`resource_limit` is the sum of effective per-type limits, and `resource_remaining` is
the sum of remaining capacity. Online, paused, suspended, and offlining Sites occupy
their deployed resource type. An Offline or deleted Site does not.

### sites get

Use before reusing a site remembered from conversation history.

### sites create

`--access-policy` accepts `private` or `public`. When omitted, the CLI does not send
`access_policy`, and the server defaults to private. The deployment Skill creates private
Sites by default and selects public access only when the user explicitly requests it.
`--description` is optional at the CLI compatibility
layer, accepts at most 2048 characters, and records the stable application identity and
source location. The deployment Skill always supplies it.

Before create, retain the complete current-project Site ID set. Treat every
non-successful create result as an unknown write outcome: list every Site page, compare
against that set, and match newly appeared Sites by name, exact description, and access
policy. Validate one unique match with `sites get` and reuse it. If multiple matches
exist, require user selection. A second create is allowed only after the refreshed
complete list proves that no matching Site was persisted and the structured error
permits retry; never repeat it in a loop.

### sites update

Requires at least one of `--name` or `--description`. The name must contain 1 to 128
characters. Description accepts at most 2048 characters; pass an empty value to clear it.

### sites update-config

Requires at least one config option. `--access-policy` accepts `private` or `public`.
Numeric limits must be positive. Omitted fields retain their current desired values.
Resource or route changes can require a redeployment before the effective configuration
matches the desired configuration.

### sites refresh-screenshot

Requires an Online Site with a main visit URL and an available local screenshot service.
The command sends the runtime authorization and lane headers while probing the URL. A 2xx
or 3xx response proceeds immediately. Readiness probes retry for up to 30 seconds, with
a maximum five-second timeout per request. A 4xx or 5xx response is retried within that
window and then proceeds to capture, because the application may intentionally render an
error response. If no HTTP response is received during that period, the command fails with
`SITE_NOT_READY`. It captures a 1440-pixel-wide PNG, uploads it through a
control-plane-issued destination, updates `screenshot_uri`, and removes the temporary local
image. Run it only after a Deployment reaches `Succeeded`.

Site list and detail responses return `screenshot_url` for the original image and
`screenshot_thumbnail_url` for a 480-pixel-wide WebP thumbnail when available.
Use the thumbnail for Site cards and the original for full-size viewing.
Both download URLs expire after 12 hours, bounded by the storage signing limit;
query the Site again to obtain fresh URLs after expiration.
Both fields are omitted when the Site has no screenshot.

This is a best-effort post-deployment operation. A non-zero result does not change the
successful Deployment status and must not trigger a deployment retry or rollback.

### deployments list

The response contains `page_no`, `page_size`, and `total_pages`. Increment `page_no`
until the current page reaches `total_pages`. `--status`, `--operation`, and `--type`
are repeatable and accept only the canonical tokens in the enum table.

### deployments create

Consumes an already prepared source directory. The directory must be under the operating
system temporary directory and must not be the user project or a directory inside it.
`--title` is optional at the CLI compatibility layer, accepts at most 256 characters,
and describes the purpose of this deployment. `--description` is also optional at the
CLI compatibility layer, accepts at most 2048 characters, and records the source
location, deployed application area, and material purpose or change. The deployment
Skill always supplies both fields.

`--app-tags` is required, accepts repeated options or a comma-separated integer list, and
must contain every content category that applies to the prepared application. The
deployment Skill owns the classification mapping and classification instructions.

The CLI rejects unknown IDs. If a restricted classification is present, it returns local error
`APP_CONTENT_BLOCKED` before reading the execution config, scanning or packaging source,
uploading files, or calling the control plane. Classification metadata is not included
in the presign or Deployment creation request.

The CLI canonicalizes both `--source-dir` and the temporary root returned by the current
process runtime. These paths must have an ancestor relationship after canonicalization.
On macOS, `$TMPDIR` commonly points under `/var/folders`; a hardcoded `/tmp/...` is
therefore outside the accepted root. Create the source directory with the platform
command in `SKILL.md`, pass the returned absolute path unchanged, and never pass the
temporary root itself.

For `static-web`, the input contains `public/`. The command validates paths, file count,
total size, `public/index.html`, symbolic links, and high-risk files. It then generates
`manifest.json`, obtains batch upload destinations, and uploads the manifest plus every
declared `public/**` file.

For `function-web`, the input root contains the complete package content, including
`build.sh`, `run.sh`, package metadata, lock file, source, and required runtime files. The
command validates the package contract, creates deterministic `package.zip`, obtains an
upload destination, and uploads the archive. Package validation confirms the root
adapter scripts, but it cannot execute the remote build. The runtime later starts from
`build.output_dir` and resolves `runtime.start_script` relative to that directory, so
`build.sh` must place an executable start script and all runtime dependencies in the
configured output directory. Exclude the local workspace's `node_modules` from the
uploaded source package, but do not exclude remotely installed dependencies from the
runtime artifact: when the runtime entry imports external packages, the build must
either emit a self-contained bundle or place production dependencies under
`<output_dir>/node_modules`.

The StaticWeb execution config must be `{}`. The FunctionWeb execution config has
`schema_version=1` plus optional `build` and `runtime` objects. The control plane applies
its current defaults to known omitted fields:

- build: `runtime_key=nodejs20`, `build_script=build.sh`, `output_dir=dist`,
  `timeout_seconds=3600`;
- runtime: `runtime_key=nodejs20`, `start_script=run.sh`, `port=8000`;
- empty `environment`.

Unknown fields are ignored rather than forwarded. Build `timeout_seconds` is valid only
inside `build`; runtime has no timeout field. See `function-web-nodejs20.md` for the
canonical JSON.

Only after every upload succeeds does the CLI call the control plane to create the
Deployment. The CLI must not inspect the project, choose files, copy source, install
dependencies, run build commands, or generate build and start scripts. Upload
destinations remain in memory and are never returned.

Call once for one source directory and site decision. Record the returned Deployment ID
before querying its progress.

`SOURCE_DIR_OUTSIDE_TEMP` is a pre-upload local validation failure. Discard the prepared
directory, create a new directory from the current process's system temporary root,
recopy the same package, and retry once. Do not retry the rejected path.

When the response is uncertain because of a connection failure, query Deployment history
before creating another Deployment.

### deployments get

Use this command for one current-state query. Use `deployments wait` as the only
monitoring loop.

### deployments wait

Wait for a Deployment while the CLI owns immediate querying, adaptive polling, and
timeout handling:

```text
<trae-deploy> deployments wait --deployment-id ID
<trae-deploy> deployments wait --deployment-id ID --status building --status succeeded
<trae-deploy> deployments wait --deployment-id ID --change
<trae-deploy> deployments wait --deployment-id ID --timeout-seconds 600
```

The default timeout is 60 seconds. Valid values are 1 through 3600 seconds.

- With no mode flag, return when the Deployment is terminal or the timeout expires.
- Repeat `--status` to return when any selected status is observed. A terminal state
  that was not selected still exits the wait because the selected state can no longer
  be reached.
- `--change` returns when status, stage, progress, or any Task status differs from the
  initial query.
- `--change` and `--status` are mutually exclusive.

Every successful result contains the query that caused the command to exit:

```json
{
  "ok": true,
  "data": {
    "wait_reason": "terminal",
    "elapsed_seconds": 8,
    "deployment": {
      "deployment_id": "dep_example",
      "status": 9
    },
    "screenshot_refresh": {
      "status": "updated"
    },
    "tips": [
      "Deployment reached terminal success.",
      "Site screenshot was refreshed successfully."
    ]
  },
  "log_id": "response log ID"
}
```

`wait_reason` is `terminal`, `status_match`, `state_changed`, or `timeout`. Timeout is a
successful observation result and includes the latest non-terminal Deployment. In the
default mode, terminal Failed or Cancelled remains exit code `6`; error details contain
the same `wait_reason`, `elapsed_seconds`, and latest `deployment`. When an explicitly
selected Failed or Cancelled status is observed, the command exits successfully with
`wait_reason=status_match`.

Whenever the observed Deployment status is Succeeded, `wait` performs one best-effort
screenshot refresh before returning. The stdout JSON then includes
`screenshot_refresh.status` as `updated` or `failed` and a `tips` string array whose
entries are separate display lines. Screenshot failure never changes Deployment success.
For `failed`, `screenshot_refresh` also includes `error_code` and `message`. These fields
are omitted when the observed Deployment has not succeeded. Callers must not run a
second screenshot refresh after `updated` or `failed`.

### deployments retry

Use only when `retryable` is true and source plus execution configuration are unchanged.

### deployments rollback

Requires a historical successful Deployment and explicit user confirmation.

### logs build and logs deploy

Select the log type from the failed stage. The CLI requests a short-lived download
descriptor, downloads the object to a session-isolated system temporary directory,
verifies the expected size and SHA-256, and returns the absolute path as `data.log_file`.

The CLI must:

- stream to an incomplete file and atomically rename only after verification;
- remove partial files after failed or interrupted downloads;
- restrict the file to the current user;
- keep the presigned URL in memory only;
- omit the URL from stdout, stderr, metadata, and errors; and
- never forward deployment-service credentials or routing headers to object storage.

Inspect `data.log_file` with available file or command tools. Search first, read bounded
context around matches, and inspect the file tail when useful. Do not load the full file
into model context unless it is small.

### logs runtime

Runtime logs are returned inline as `data.items`; each item contains `timestamp_ms`,
`content`, `stream`, and `revision_number`. The response also contains `next_cursor` and
`query_start_time_ms`. It does not create a local log file.

The default window is the previous hour. `--since` accepts a positive integer followed
by `ms`, `s`, `m`, `h`, or `d`. Use `--start-time-ms` for an exact lower bound;
`--since` and `--start-time-ms` are mutually exclusive. `--end-time-ms` sets an exact
upper bound. `--keyword` filters log content, `--stream` accepts only `stdout` or
`stderr`, and `--limit` accepts `1` through `100`. A keyword must not exceed 256 bytes
or contain control characters. A cursor must not exceed 4096 bytes.

When `next_cursor` is non-empty, request the next page with the same filters and time
bounds. Pass the returned `query_start_time_ms` as `--start-time-ms` together with
`--cursor`; do not recompute a relative `--since` window. If the first request included
`--end-time-ms`, preserve it for every page. Stop when `next_cursor` is empty.

## Retry Behavior

Retry read operations after temporary failures with bounded backoff.

Do not independently repeat a create command after any non-successful or uncertain
response. For `sites create`, reconcile the complete Site list against the pre-create
Site ID set and reuse a uniquely matched persisted Site. For `deployments create`,
query Site deployment history first.

Do not use `deployments retry` after changing source or execution configuration.

## Temporary Files

Store prepared source directories, command JSON, and downloaded logs in a
temporary working directory outside the user's project. Delete workflow files after use.
Harness cleans the session directory when the session ends.

Do not commit prepared sources, command output, or downloaded logs to the
user's project.

## Security

- Do not ask the user for credentials or service connection settings.
- Do not print secrets or temporary upload details.
- Do not pass arbitrary request bodies or service URLs to the CLI.
- Do not replace a supported CLI command with a generic HTTP request.
- Do not persist full logs unless the user explicitly requests a diagnostic artifact.
- Do not expose presigned log URLs or forward service authorization to object storage.
- Do not write manifests or archives to the user project.

## User-Facing Errors

For local validation errors, report the invalid project requirement and the affected
relative path when available.

For rejected operations, report the stable error code, summary, and valid next action.

For temporary failures, preserve the site and Deployment IDs needed to resume safely.

For terminal deployment failures, report the failed stage before querying additional
logs.

## Diagnostic Command

### check

`check` validates the runtime context and login, then performs a bounded site-list
request. Its output contains summarized check status and a request log ID, without
credentials, identity values, site data, or service addresses.
