#!/usr/bin/env node

import assert from 'node:assert/strict';

import { findParagraphWidthViolations } from './validate-report-source.mjs';

const violationCount = (source) => findParagraphWidthViolations(source).length;

const rejected = [
  ['global paragraph measure', '<style>p { max-width: 72ch; }</style>'],
  ['grouped global paragraph measure', '<style>h4, p { max-inline-size: 60ch; }</style>'],
  [
    'nested global paragraph measure',
    '<style>@media (min-width: 900px) { p { max-width: var(--measure); } }</style>',
  ],
  ['inherited global paragraph measure', '<style>p { max-width: inherit; }</style>'],
  ['body-wide paragraph measure', '<style>body p { max-width: 78ch !important; }</style>'],
];

for (const [name, source] of rejected) {
  assert.equal(violationCount(source), 1, `${name} should be rejected`);
}

const accepted = [
  ['Intro summary measure', '<style>.report-intro__summary { max-width: 70ch; }</style>'],
  ['explicit split-copy measure', '<style>.split-layout__copy p { max-width: 60ch; }</style>'],
  ['nested scoped paragraph measure', '<style>.article-copy { p { max-width: 60ch; } }</style>'],
  ['non-restrictive paragraph width', '<style>p { max-width: 100%; }</style>'],
  ['paragraph width reset', '<style>p { max-inline-size: none; }</style>'],
  ['paragraph without a width rule', '<style>p { color: var(--ink); }</style>'],
  ['commented paragraph rule', '<style>/* p { max-width: 10ch; } */</style>'],
];

for (const [name, source] of accepted) {
  assert.equal(violationCount(source), 0, `${name} should be accepted`);
}

console.log('validate-report-source tests: PASS');
