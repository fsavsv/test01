# Static Web Deployment

Use this reference after the project has been classified as `StaticWeb`.

## Eligibility

A project is eligible when it is either:

- directly publishable static content; or
- a frontend project with a deterministic production build output.

The published output must contain a non-empty `index.html`. Reject server-rendered or
API-serving applications that require a running process.

## Inspect

Read:

- `package.json`, when present
- the package-manager lock file
- framework configuration
- existing build scripts
- candidate output directories

Determine:

- package manager
- production build command
- final output directory
- whether the output already exists or must be built

Do not infer an output directory only from a framework default when the repository
overrides it.

## Build Selection

Prefer the repository's existing production build script.

When no suitable script exists, create or adjust project build configuration only through
the normal file-editing workflow and only when it does not change application behavior.
The CLI never creates a build adapter.

Do not:

- rewrite frontend features;
- change API endpoints;
- inject environment-specific secrets;
- replace the project's package manager; or
- add an unrelated framework dependency.

## Prepare the Source Directory

Create a fresh directory with the platform-specific temporary-directory command in
`SKILL.md`. Use its returned absolute path as `<source-dir>` without replacing it with
`/tmp/...` or a workspace path.

For an existing publishable output directory, copy its required static files into
`<source-dir>/public/`.

When a build is required:

- run the repository's production build command;
- verify the configured output directory exists; and
- copy that output into `<source-dir>/public/`.

When no build is required, copy the directly publishable project files into
`<source-dir>/public/`.

Exclude caches, VCS metadata, test output, logs, credentials, `.env` files, archives,
source maps that are not intended for publication, and unrelated generated output.

## Output Requirements

The CLI platform contract requires the prepared `public/` directory to:

- exist after the required build step;
- contain a non-empty `index.html`;
- contain only regular publishable files;
- contain no absolute paths or parent-directory traversal;
- contain no symbolic links;
- contain no credentials or local environment files.

The CLI creates `<source-dir>/manifest.json`. Do not create or edit it manually.

When static output exceeds 99 published files, recommend FunctionWeb.
This is a workflow threshold, not a service upload quota.
Preserve the full output and run the bundled
`scripts/prepare-static-function.mjs --source-dir <source-dir>` with Node.js.
Continue as `function-web` using its returned directory, execution config and deployment
type. This threshold fallback is automatic; do not remove resources to stay static.
See **Route Large Static Output** in `SKILL.md`.

## Create Deployment

Write `{}` to the execution config file. StaticWeb does not accept build or runtime
configuration.

Run:

`deployments create --site-id <site-id> --title "<deployment-purpose>" --description "<deployment-details>" --type static-web --source-dir <directory> --execution-config <file> --app-tags <tag-id[,tag-id...]>`

Use the content classification completed in `SKILL.md` and pass every applicable tag.
Do not run this command when any restricted tag applies.

Treat a pre-upload failure as a local project-contract failure. Report the invalid path,
missing entrypoint, object-count limit, size limit, or unsafe file category identified by
the CLI.

Upload admission is controlled by the service. Validation failures remain blocking;
preserve the CLI diagnostic rather than changing deployment type to bypass an error.

The command validates `public/`, generates `manifest.json`, obtains upload destinations,
uploads the manifest plus every declared file, and creates the Deployment only after all
uploads succeed. Do not inspect or display temporary upload details.

Do not patch the temporary copy. If application source is defective, patch the user
project, rebuild or recopy into a fresh source directory, and create again.

## Common Failures

### Missing index

Confirm that the copied directory is the production output root rather than its parent.
Rebuild when required, then copy it into a fresh `public/` directory.

### Too many files

Do not remove arbitrary application assets. Explain the file-count limit and identify
whether generated source maps, reports, caches, or test output were included by mistake.
Before upload, if the prepared output has more than 99 required published files,
recommend FunctionWeb and use the adapter while preserving every resource.

### Output too large

Identify large generated files. Exclude only files that are not required by the
application. Do not silently compress or remove required assets.
Preserve the CLI or service diagnostic when upload validation fails.

### Unsafe files

Stop when the CLI detects secrets, traversal paths, symbolic links, or unsupported file
types. Explain the path category without printing file contents.

## Completion

After create succeeds, return to the main Skill workflow to monitor the Deployment.
