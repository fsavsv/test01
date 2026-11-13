import { lstat, readdir, realpath, mkdtemp, mkdir, copyFile, writeFile, rm } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

// Routing thresholds match the CLI's static limits.
const STATIC_ROUTING_FILE_LIMIT = 99;
const STATIC_ROUTING_SIZE_LIMIT = 50 * 1024 * 1024;

function fail(code, message) {
  throw Object.assign(new Error(message), { code });
}

export async function prepare(sourceDir) {
  const source = await realpath(sourceDir);
  const temp = await realpath(os.tmpdir());
  const relative = path.relative(temp, source);
  if (!relative || relative.startsWith('..') || path.isAbsolute(relative)) {
    fail('SOURCE_DIR_OUTSIDE_TEMP', 'Use a dedicated prepared source directory under os.tmpdir().');
  }
  const publicDir = path.join(source, 'public');
  if (!(await lstat(publicDir)).isDirectory()) fail('STATIC_PUBLIC_MISSING', 'public must be a real directory.');
  const files = [];
  async function scan(directory, prefix = '') {
    for (const name of await readdir(directory)) {
      const lower = name.toLowerCase();
      if (['.git', 'node_modules', '.ssh', 'credentials', 'id_rsa', 'id_ed25519'].includes(lower)
          || lower.startsWith('.env') || lower.endsWith('.pem') || lower.endsWith('.key')) {
        fail('HIGH_RISK_FILE', `Prohibited path: ${path.join(prefix, name)}`);
      }
      const absolute = path.join(directory, name);
      const stat = await lstat(absolute);
      if (stat.isSymbolicLink()) fail('SYMLINK_NOT_ALLOWED', 'Symbolic links are not supported.');
      if (stat.isDirectory()) await scan(absolute, path.join(prefix, name));
      else if (stat.isFile()) files.push({ absolute, relative: path.join(prefix, name), size: stat.size });
      else fail('UNSUPPORTED_FILE_TYPE', 'Only regular files are supported.');
    }
  }
  await scan(publicDir);
  if (!files.some(file => file.relative === 'index.html' && file.size > 0)) {
    fail('STATIC_INDEX_MISSING', 'public/index.html must be non-empty.');
  }
  const total = files.reduce((size, file) => size + file.size, 0);
  if (files.length <= STATIC_ROUTING_FILE_LIMIT && total <= STATIC_ROUTING_SIZE_LIMIT) {
    fail('STATIC_WITHIN_LIMITS', 'Use static-web for sources with at most 99 files and 50 MiB.');
  }
  const output = await mkdtemp(path.join(temp, 'trae-static-function-'));
  try {
    for (const file of files) {
      const destination = path.join(output, 'public', file.relative);
      await mkdir(path.dirname(destination), { recursive: true });
      await copyFile(file.absolute, destination);
    }
    const pkg = { name: 'trae-static-function', version: '1.0.0', private: true,
      type: 'module', engines: { node: '>=20' }, scripts: { start: 'node server.mjs' } };
    await writeFile(path.join(output, 'package.json'), JSON.stringify(pkg, null, 2));
    await writeFile(path.join(output, 'package-lock.json'), JSON.stringify({
      name: pkg.name, version: pkg.version, lockfileVersion: 3, requires: true,
      packages: { '': { name: pkg.name, version: pkg.version, engines: pkg.engines } },
    }, null, 2));
    await copyFile(new URL('../assets/static-server.mjs', import.meta.url), path.join(output, 'server.mjs'));
    await writeFile(path.join(output, 'build.sh'),
      '#!/bin/sh\nset -eu\nmkdir -p dist\ncp server.mjs run.sh package.json dist/\ncp -R public dist/public\nchmod 755 dist/run.sh\n', { mode: 0o755 });
    await writeFile(path.join(output, 'run.sh'),
      '#!/bin/sh\nset -eu\nexec node server.mjs\n', { mode: 0o755 });
    const config = path.join(output, 'execution-config.json');
    await writeFile(config, JSON.stringify({
      schema_version: 1,
      build: { runtime_key: 'nodejs20', build_script: 'build.sh', output_dir: 'dist',
        environment: {}, timeout_seconds: 3600 },
      runtime: { runtime_key: 'nodejs20', start_script: 'run.sh', port: 8000,
        environment: { PORT: '8000' } },
    }, null, 2));
    return { source_dir: output, execution_config: config, deploy_type: 'function-web',
      file_count: files.length, total_size_bytes: total };
  } catch (error) {
    await rm(output, { recursive: true, force: true });
    throw error;
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    if (process.argv.length !== 4 || process.argv[2] !== '--source-dir') {
      fail('INVALID_ARGUMENT', 'Usage: prepare-static-function.mjs --source-dir <prepared-static-source>');
    }
    console.log(JSON.stringify({ ok: true, data: await prepare(process.argv[3]) }));
  } catch (error) {
    console.log(JSON.stringify({ ok: false, error: { code: error.code || 'PREPARATION_FAILED', message: error.message } }));
    process.exitCode = 2;
  }
}
