#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const safeMaxValues = new Set([
  'none',
  '100%',
  'initial',
  'unset',
  'revert',
  'revert-layer',
]);

const preserveLines = (match) => match.replace(/[^\n]/g, ' ');
const stripComments = (source) => source.replace(/\/\*[\s\S]*?\*\//g, preserveLines);

const findTerminator = (source, start) => {
  let quote = null;
  let parentheses = 0;

  for (let index = start; index < source.length; index += 1) {
    const character = source[index];
    const previous = source[index - 1];

    if (quote) {
      if (character === quote && previous !== '\\') quote = null;
      continue;
    }
    if (character === '"' || character === "'") {
      quote = character;
      continue;
    }
    if (character === '(') parentheses += 1;
    if (character === ')') parentheses = Math.max(0, parentheses - 1);
    if (parentheses === 0 && (character === '{' || character === ';')) {
      return { character, index };
    }
  }

  return null;
};

const findClosingBrace = (source, openIndex) => {
  let depth = 1;
  let quote = null;

  for (let index = openIndex + 1; index < source.length; index += 1) {
    const character = source[index];
    const previous = source[index - 1];

    if (quote) {
      if (character === quote && previous !== '\\') quote = null;
      continue;
    }
    if (character === '"' || character === "'") {
      quote = character;
      continue;
    }
    if (character === '{') depth += 1;
    if (character === '}') depth -= 1;
    if (depth === 0) return index;
  }

  return source.length - 1;
};

const groupingAtRule = /^@(container|document|layer|media|scope|supports)\b/i;
const globalParagraphSelectors = new Set(['p', 'body p', 'html p', 'html body p', ':root p']);

const walkRules = (source, sourceOffset, visit) => {
  let cursor = 0;

  while (cursor < source.length) {
    const terminator = findTerminator(source, cursor);
    if (!terminator) return;
    if (terminator.character === ';') {
      cursor = terminator.index + 1;
      continue;
    }

    const prelude = source.slice(cursor, terminator.index).trim();
    const closeIndex = findClosingBrace(source, terminator.index);
    const body = source.slice(terminator.index + 1, closeIndex);
    const preludeStart = cursor + source.slice(cursor, terminator.index).search(/\S|$/);

    if (groupingAtRule.test(prelude)) {
      walkRules(body, sourceOffset + terminator.index + 1, visit);
    } else if (prelude && !prelude.startsWith('@')) {
      visit(prelude, body, sourceOffset + preludeStart);
    }

    cursor = closeIndex + 1;
  }
};

const cssBlocks = (source) => {
  const blocks = [];
  const stylePattern = /<style\b[^>]*>([\s\S]*?)<\/style>/gi;

  for (const match of source.matchAll(stylePattern)) {
    const contentOffset = match.index + match[0].indexOf(match[1]);
    blocks.push({ source: match[1], offset: contentOffset });
  }

  const looksLikeHtml = /<!doctype\s+html|<html\b|<body\b|<style\b/i.test(source);
  return blocks.length > 0 || looksLikeHtml ? blocks : [{ source, offset: 0 }];
};

const lineAt = (source, index) => source.slice(0, index).split('\n').length;

export const findParagraphWidthViolations = (source, sourceName = '<source>') => {
  const normalizedSource = source.replace(/\r\n/g, '\n');
  const violations = [];

  for (const block of cssBlocks(normalizedSource)) {
    const css = stripComments(block.source);
    walkRules(css, block.offset, (selectorText, body, selectorOffset) => {
      const hasGlobalParagraphSelector = selectorText
        .split(',')
        .some((selector) =>
          globalParagraphSelectors.has(selector.trim().toLowerCase().replace(/\s+/g, ' '))
        );
      if (!hasGlobalParagraphSelector) return;

      const widthPattern = /(?:^|;)\s*(max-width|max-inline-size)\s*:\s*([^;}]+)/gi;
      for (const match of body.matchAll(widthPattern)) {
        const value = match[2].replace(/\s*!important\s*$/i, '').trim().toLowerCase();
        if (safeMaxValues.has(value) || /^calc\(\s*100%\s*\)$/i.test(value)) continue;
        violations.push({
          source: sourceName,
          line: lineAt(normalizedSource, selectorOffset),
          property: match[1].toLowerCase(),
          value: match[2].trim(),
        });
      }
    });
  }

  return violations;
};

const attribute = (tag, name) =>
  tag.match(new RegExp(`\\b${name}\\s*=\\s*["']([^"']+)["']`, 'i'))?.[1];

const inspectFile = (inputPath) => {
  const resolvedPath = path.resolve(inputPath);
  const source = fs.readFileSync(resolvedPath, 'utf8');
  const violations = findParagraphWidthViolations(source, resolvedPath);

  if (path.extname(resolvedPath).toLowerCase() !== '.html') return violations;

  const linkedStyles = new Set();
  for (const match of source.matchAll(/<link\b[^>]*>/gi)) {
    const tag = match[0];
    const rel = attribute(tag, 'rel') ?? '';
    const href = attribute(tag, 'href');
    if (!/\bstylesheet\b/i.test(rel) || !href || /^(?:[a-z]+:|\/\/|#)/i.test(href)) continue;

    const cleanHref = href.split(/[?#]/, 1)[0];
    const linkedPath = path.resolve(path.dirname(resolvedPath), decodeURIComponent(cleanHref));
    if (!linkedStyles.has(linkedPath) && fs.existsSync(linkedPath)) {
      linkedStyles.add(linkedPath);
      violations.push(
        ...findParagraphWidthViolations(fs.readFileSync(linkedPath, 'utf8'), linkedPath)
      );
    }
  }

  return violations;
};

const run = (inputPaths) => {
  if (inputPaths.length === 0) {
    console.error('Usage: node validate-report-source.mjs <report.html|styles.css> [...]');
    return 2;
  }

  const violations = [];
  for (const inputPath of inputPaths) {
    try {
      violations.push(...inspectFile(inputPath));
    } catch (error) {
      console.error(`report source gate: ERROR — ${inputPath}: ${error.message}`);
      return 2;
    }
  }

  if (violations.length > 0) {
    console.error('report source gate: FAIL');
    for (const violation of violations) {
      console.error(
        `- ${violation.source}:${violation.line} global p sets ${violation.property}: ${violation.value}`
      );
    }
    return 1;
  }

  console.log('report source gate: PASS');
  return 0;
};

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);
if (isMain) process.exit(run(process.argv.slice(2)));
