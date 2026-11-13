#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptsDir = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.dirname(scriptsDir);

const read = (relativePath) =>
  fs.readFileSync(path.join(rootDir, relativePath), 'utf8').replace(/\r\n/g, '\n');

const failures = [];
const check = (condition, message) => {
  if (!condition) failures.push(message);
};

const normalize = (source) => source.replace(/\s+/g, ' ').trim();

const hasHeroPaletteInvalidation = (source) => {
  const normalized = normalize(source);
  return (
    /fallback|replaced|removed|rejected/i.test(normalized) &&
    /invalidate|discard|reset|re-resolve|resolve again/i.test(normalized) &&
    /palette|color/i.test(normalized)
  );
};

const extractRuleBodies = (source, selector) => {
  const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return [...source.matchAll(new RegExp(`${escapedSelector}\\s*\\{([^}]*)\\}`, 'g'))].map(
    (match) => match[1]
  );
};

const extractRuleBodiesContaining = (source, selectorFragment) =>
  [...source.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter((match) => match[1].includes(selectorFragment))
    .map((match) => match[2]);

const extractMediaBlocks = (source) => {
  const blocks = [];
  const mediaStart = /@media\s+([^\{]+)\{/g;
  let match;

  while ((match = mediaStart.exec(source)) !== null) {
    let depth = 1;
    let cursor = mediaStart.lastIndex;
    let quote = null;

    for (; cursor < source.length && depth > 0; cursor += 1) {
      const character = source[cursor];
      const previous = source[cursor - 1];

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
    }

    if (depth === 0) {
      blocks.push({
        condition: normalize(match[1]),
        body: source.slice(mediaStart.lastIndex, cursor - 1),
      });
      mediaStart.lastIndex = cursor;
    }
  }

  return blocks;
};

const hasStageAutoHeightFallback = (blocks, conditionPattern) =>
  blocks.some(
    ({ condition, body }) =>
      conditionPattern.test(condition) &&
      /\.report-intro--stage/.test(body) &&
      /min-block-size\s*:\s*auto\s*;/.test(body)
  );

const skill = read('SKILL.md');
const colorSystem = read('references/color-system.md');
const defaultTheme = read('references/default-theme.md');
const elementUsage = read('references/element-usage.md');
const layoutContract = read('references/layout-contract.md');
const qaChecklist = read('references/qa-checklist.md');
const visualBadcaseGates = read('references/visual-badcase-gates.md');
const interactivePrd = read('references/interactive-prd.md');
const imageGuide = read('diagrams/image-guide.md');
const chartContract = read('references/chart-contract.md');
const diagramContract = read('references/diagram-contract.md');
const shellScaffold = read('scripts/new-report.sh');
const powershellScaffold = read('scripts/new-report.ps1');
const reportSourceValidator = read('scripts/validate-report-source.mjs');

const planMatch = skill.match(/### 1\. Plan\n([\s\S]*?)\n### 2\./);
check(planMatch, 'SKILL.md must contain a bounded Plan section.');

if (planMatch) {
  const plan = planMatch[1];
  const compactPresetLines =
    plan.match(/`Color preset: <canonical preset name> — cue: <resolved visual cue>`/g) ?? [];
  check(
    compactPresetLines.length === 1,
    'Plan must define exactly one compact Color preset line with its cue.'
  );
  const compactIntroModeLines =
    plan.match(
      /`Intro mode: <contained\|integrated\|stage> — cue: <content\/material cue>`/g
    ) ?? [];
  check(
    compactIntroModeLines.length === 1,
    'Plan must define exactly one compact Intro mode line with the three canonical modes and its cue.'
  );
  check(!/```css|:root\s*\{/.test(plan), 'Plan must not contain or request a CSS token block.');
  check(
    !/^#{1,6}\s+Design Style|Hero 图片|整体气质|推荐框/m.test(plan),
    'Plan must not repeat the Design Style checklist.'
  );
}

const workflowMatch = skill.match(/## Workflow\n([\s\S]*?)\n## Compatibility/);
check(workflowMatch, 'SKILL.md must contain a bounded Workflow section.');
const workflow = workflowMatch?.[1] ?? '';
const resolveIntroMediaStep = workflow.indexOf('### 4. Resolve Opening Intro Media');
const injectPaletteStep = workflow.indexOf('### 5. Inject One Palette');
check(
  resolveIntroMediaStep >= 0 &&
    injectPaletteStep >= 0 &&
    resolveIntroMediaStep < injectPaletteStep,
  'The workflow must resolve accepted Intro media before locking and injecting the final palette.'
);
if (resolveIntroMediaStep >= 0 && injectPaletteStep > resolveIntroMediaStep) {
  const mediaResolutionStep = workflow.slice(resolveIntroMediaStep, injectPaletteStep);
  check(
    /accepted Hero|valid no-image fallback/i.test(mediaResolutionStep),
    'The media-resolution step must end in an accepted Hero or a valid no-image fallback.'
  );
}
if (planMatch) {
  check(
    /defer the final palette[\s\S]{0,160}(?:accepted Hero|valid no-image fallback)/i.test(
      planMatch[1]
    ) && !/one active palette selected from the prompt\/content cues/.test(planMatch[1]),
    'The Plan must defer a Hero-led final palette until media resolves.'
  );
}

const colorDecisionMatch = colorSystem.match(/## Decision Order\n([\s\S]*?)\n## /);
check(colorDecisionMatch, 'The color contract must contain a bounded Decision Order section.');
if (colorDecisionMatch) {
  const decisionOrder = normalize(colorDecisionMatch[1]);
  const explicitDirectionIndex = decisionOrder.indexOf('explicit user or brand');
  const acceptedHeroIndex = decisionOrder.indexOf('accepted Hero');
  const contentCueIndex = decisionOrder.indexOf('prompt and content cues');
  check(
    explicitDirectionIndex >= 0 &&
      acceptedHeroIndex > explicitDirectionIndex &&
      contentCueIndex > acceptedHeroIndex,
    'Color priority must be explicit user/brand direction, accepted Hero, then prompt/content cues.'
  );
}

check(
  /explicit user or brand[\s\S]{0,180}accepted Hero[\s\S]{0,180}prompt and content/i.test(
    normalize(visualBadcaseGates)
  ),
  'The Priority 0 palette gate must preserve user/brand, accepted-Hero, then content priority.'
);

check(
  /warm-neutral drafting baseline[\s\S]{0,220}accepted Hero[\s\S]{0,180}(?:prompt|content)/i.test(
    normalize(colorSystem)
  ) &&
    /warm-neutral drafting baseline[\s\S]{0,180}(?:never|must not)[\s\S]{0,80}unchanged/i.test(
      normalize(colorSystem)
    ),
  'The warm drafting baseline must be replaced from an accepted Hero or the no-Hero content fallback.'
);

check(
  /remap both page\/report and chart\/data layers/i.test(normalize(colorSystem)) &&
    /neutral[\s\S]{0,120}(?:temperature|warm\/cool)[\s\S]{0,120}(?:light\/dark|value)/i.test(
      normalize(colorSystem)
    ),
  'A resolved cue must remap both token layers, including neutral temperature and value.'
);

check(
  /dark teal[\s\S]{0,120}gray-heavy[\s\S]{0,180}(?:user|brand)[\s\S]{0,100}accepted Hero/i.test(
    normalize(visualBadcaseGates)
  ),
  'Hero-led cool or dark neutrals must not be rejected as an ad-hoc palette.'
);

check(
  hasHeroPaletteInvalidation(colorSystem) && hasHeroPaletteInvalidation(imageGuide),
  'Hero fallback or replacement must invalidate and re-resolve a Hero-led palette.'
);

check(
  /accepted Hero[\s\S]{0,240}Color preset[\s\S]{0,160}cue/i.test(normalize(qaChecklist)) &&
    /static decision-record check only[\s\S]{0,160}does not add (?:browser|rendered)[\s\S]{0,160}(?:palette|color) harmony[\s\S]{0,120}`NOT RUN`/i.test(
      normalize(qaChecklist)
    ),
  'Static QA must trace the palette to accepted Hero media without claiming rendered color harmony.'
);

check(
  /Style[\s\S]{0,220}(?:must not|may not)[\s\S]{0,120}(?:select|override|remap)[\s\S]{0,100}(?:palette|color)/i.test(
    normalize(defaultTheme)
  ),
  'Style may tune presentation but must not select, override, or remap the resolved palette.'
);

check(
  /crop[\s\S]{0,120}(?:materially|significantly)[\s\S]{0,120}(?:re-resolve|resolve again)[\s\S]{0,100}palette/i.test(
    normalize(defaultTheme)
  ),
  'A material crop change must re-resolve the Hero-led palette.'
);

check(
  /references\/default-theme\.md` \| Every report-like deliverable before styling/.test(skill),
  'Progressive routing must load the default design contract for every report-like deliverable.'
);
check(
  /Contract ID:\s*`report-default-v1`/.test(defaultTheme),
  'The default design reference must publish contract ID report-default-v1.'
);

const designRuleIds = [...defaultTheme.matchAll(/\bDS-(\d{2})\b/g)].map((match) => match[1]);
const uniqueDesignRuleIds = [...new Set(designRuleIds)];
check(
  uniqueDesignRuleIds.length === 12 &&
    uniqueDesignRuleIds.every((id, index) => id === String(index + 1).padStart(2, '0')),
  'The default design reference must define exactly DS-01 through DS-12.'
);
check(
  /`Color preset: <canonical preset name> — cue: <resolved visual cue>`/.test(colorSystem),
  'The color contract must define the same compact Plan record.'
);
check(
  /Custom:<stable-id>/.test(colorSystem),
  'Custom palettes must use a stable ID in the compact Plan record.'
);

const authorityFiles = [
  'SKILL.md',
  ...fs.readdirSync(path.join(rootDir, 'references')).map((name) => `references/${name}`),
  'scripts/new-report.sh',
  'scripts/new-report.ps1',
];
const pageBgDefinitions = authorityFiles.filter((relativePath) =>
  /--page-bg\s*:/.test(read(relativePath))
);
check(
  pageBgDefinitions.length === 1 && pageBgDefinitions[0] === 'references/color-system.md',
  `The full color token block must have one authority; found --page-bg in: ${pageBgDefinitions.join(', ') || 'none'}.`
);

const shellTemplateMatch = shellScaffold.match(/<< 'HTML'\n([\s\S]*?)\nHTML\n/);
const powershellTemplateMatch = powershellScaffold.match(/\$HTML_CONTENT = @'\n([\s\S]*?)\n'@\n/);
check(shellTemplateMatch, 'Unable to extract the shell HTML scaffold.');
check(powershellTemplateMatch, 'Unable to extract the PowerShell HTML scaffold.');

if (shellTemplateMatch && powershellTemplateMatch) {
  const shellTemplate = shellTemplateMatch[1];
  const powershellTemplate = powershellTemplateMatch[1];
  check(shellTemplate === powershellTemplate, 'Shell and PowerShell HTML scaffolds must stay identical.');

  const paletteMarkers = shellTemplate.match(/ACTIVE_PALETTE_TOKENS/g) ?? [];
  check(paletteMarkers.length === 1, 'The scaffold must contain exactly one active-palette marker.');

  const defaultIntroMatch = shellTemplate.match(
    /<header class="report-intro">([\s\S]*?)<\/header>/
  );
  check(
    defaultIntroMatch,
    'The scaffold must default to contained through an unmodified report-intro class.'
  );
  if (defaultIntroMatch) {
    const defaultIntroMarkup = defaultIntroMatch[1];
    check(
      !/<(?:img|svg|picture|source|video|canvas|object|embed)\b|\bsrc\s*=|\bassets\//i.test(
        defaultIntroMarkup
      ),
      'The default Opening Intro must not contain media markup, a source URL, or an asset reference.'
    );
    check(
      (defaultIntroMarkup.match(/<h1\b/g) ?? []).length === 1 &&
        /class="report-intro__summary"/.test(defaultIntroMarkup),
      'The default contained Intro must keep one h1 and its conclusion-led summary.'
    );
  }
  check(
    (shellTemplate.match(/<h1\b/gi) ?? []).length === 1,
    'The complete default scaffold must contain exactly one page h1.'
  );

  const defaultIntroCss = extractRuleBodiesContaining(shellTemplate, '.report-intro').join('\n');
  check(
    !/\bbackground-image\s*:|\b(?:url|image-set|-webkit-image-set|cross-fade|element|image|linear-gradient|radial-gradient|conic-gradient)\s*\(/i.test(
      defaultIntroCss
    ),
    'The default scaffold Intro CSS must not embed background images, URLs, image sets, or other CSS image media.'
  );

  check(
    /<header class="report-intro">\s*<div class="report-intro__surface">\s*<div class="report-intro__content">/.test(
      shellTemplate
    ) &&
      /<div class="page__content">\s*<main>/.test(shellTemplate),
    'The scaffold must separate the full-width Intro shell from centered Intro and reading content layers.'
  );
  check(
    /article\.page\s*\{[^}]*width\s*:\s*100%\s*;/.test(shellTemplate) &&
      /\.page__content\s*,\s*\.report-intro__surface\s*\{[^}]*max-width\s*:\s*var\(--max\)\s*;[^}]*margin\s*:\s*0 auto\s*;/.test(
        shellTemplate
      ),
    'The Intro shell must stay full width while its surface and report body share the centered reading width.'
  );

  const introDecorationSelectors = [
    '.report-intro:not(.report-intro--integrated):not(.report-intro--stage):not(.report-intro--with-media):not(.report-intro--plain) .report-intro__surface::before',
    '.report-intro:not(.report-intro--integrated):not(.report-intro--stage):not(.report-intro--with-media):not(.report-intro--plain) .report-intro__surface::after',
  ];
  const introDecorationRules = introDecorationSelectors.flatMap((selector) =>
    extractRuleBodies(shellTemplate, selector)
  );
  const introDecorationCss = introDecorationRules.join('\n');

  check(
    introDecorationSelectors.every((selector) => shellTemplate.includes(selector)),
    'Contained accents must opt out of both alternate layout modes and both legacy media-treatment modifiers.'
  );
  check(
    /content\s*:\s*["']{2}\s*;/.test(introDecorationCss) &&
      /position\s*:\s*absolute\s*;/.test(introDecorationCss) &&
      /pointer-events\s*:\s*none\s*;/.test(introDecorationCss),
    'The default Intro accents must be non-interactive CSS pseudo-elements.'
  );
  check(
    introDecorationRules.filter((rule) => /background(?:-color)?\s*:/.test(rule)).length >= 2 &&
      introDecorationRules
        .filter((rule) => /background(?:-color)?\s*:/.test(rule))
        .every((rule) => /background(?:-color)?\s*:\s*var\(--page-/.test(rule)),
    'Each default Intro accent must derive its fill from page palette tokens.'
  );
  check(
    !/(?:linear|radial|conic)-gradient\s*\(|box-shadow\s*:|text-shadow\s*:|animation(?:-[\w-]+)?\s*:/i.test(
      introDecorationCss
    ),
    'Default Intro accents must not use gradients, shadows, or animation.'
  );
  check(
    !/(?:#(?:[0-9a-f]{3,8})\b|\b(?:rgb|rgba|hsl|hsla|hwb|lab|lch|oklab|oklch|color)\s*\()/i.test(
      introDecorationCss
    ),
    'Default Intro accents must not introduce hardcoded color values.'
  );
}

const heroModeContract = normalize(
  [skill, defaultTheme, elementUsage, layoutContract, qaChecklist, visualBadcaseGates, imageGuide].join(
    '\n'
  )
);
const skillModeContract = normalize(skill);
const layoutModeContract = normalize(layoutContract);
const imageModeContract = normalize(imageGuide);

check(
  ['contained', 'integrated', 'stage'].every(
    (mode) =>
      new RegExp(`\\b${mode}\\b`, 'i').test(skillModeContract) &&
      new RegExp(`\\b${mode}\\b`, 'i').test(layoutModeContract)
  ),
  'SKILL.md and the layout contract must define contained, integrated, and stage as the canonical Intro modes.'
);
check(
  /(?:formal|research|PRD|data|technical)[\s\S]{0,240}\bcontained\b/i.test(skillModeContract) &&
    /\bintegrated\b[\s\S]{0,360}(?:single[- ]subject|single subject|one subject)[\s\S]{0,360}(?:safe area|text-safe|text safe|safe region)/i.test(
      skillModeContract
    ) &&
    /\bstage\b[\s\S]{0,360}(?:feature|brand|film|portfolio|Landing Cover|landing cover)/i.test(
      skillModeContract
    ),
  'Automatic mode selection must keep contained as the report default and gate integrated/stage on their content and material cues.'
);
check(
  /(?:explicit user (?:mode|choice|request|selection)|supplied visual direction)[\s\S]{0,120}(?:override|takes priority|wins)/i.test(
    skillModeContract
  ),
  'An explicit user Intro-mode choice must take priority over automatic selection.'
);
check(
  /(?:no|without a) layout modifier[\s\S]{0,120}\bcontained\b/i.test(layoutModeContract) &&
    /(?:at most one of[\s\S]{0,160}report-intro--integrated[\s\S]{0,160}report-intro--stage|report-intro--integrated[\s\S]{0,160}report-intro--stage[\s\S]{0,160}mutually exclusive)/i.test(
      heroModeContract
    ) &&
    /\.report-intro--with-media/.test(layoutContract) &&
    /\.report-intro--plain/.test(layoutContract) &&
    /(?:with-media[\s\S]{0,160}plain[\s\S]{0,160}(?:orthogonal|independent|separate axis)|(?:orthogonal|independent|separate axis)[\s\S]{0,160}with-media[\s\S]{0,160}plain)/i.test(
      heroModeContract
    ),
  'Layout modes must be mutually exclusive and remain orthogonal to the legacy media-treatment modifiers.'
);
check(
  /(?:contained[\s\S]{0,100}integrated|integrated[\s\S]{0,100}contained)[\s\S]{0,260}(?:Intro|opening)[\s\S]{0,160}(?:summary|conclusion)/i.test(
    heroModeContract
  ),
  'Contained and integrated Intros must keep the conclusion-led summary inside the Intro.'
);
check(
  /for `stage`, include[\s\S]{0,300}first `main > section#report-overview` immediately after it/i.test(
    skillModeContract
  ) &&
    /`stage` may omit it only when the first direct section in `main` is the immediate Overview/i.test(
      layoutModeContract
    ) &&
    /<main>\s*<section id="report-overview">\s*<h2\b[^>]*>[^<]*<\/h2>\s*<p class="report-overview__summary">[\s\S]*?<\/p>\s*<\/section>\s*<!--\s*detailed evidence follows\s*-->/i.test(
      layoutContract
    ) &&
    /immediately followed by `main > section#report-overview` whose heading is immediately followed by `\.report-overview__summary` before evidence/i.test(
      normalize(qaChecklist)
    ),
  'Stage must put its conclusion summary in the Intro or at the start of the immediately following main > section#report-overview.'
);
check(
  /\bintegrated\b[\s\S]{0,420}(?:requires|only when|must use)[\s\S]{0,180}(?:accepted|qualified|suitable)[\s\S]{0,100}media/i.test(
    heroModeContract
  ) &&
    /functional (?:contrast )?scrim/i.test(heroModeContract) &&
    /(?:scrim[\s\S]{0,260}(?:page token|page-token|--page-)|(?:page token|page-token|--page-)[\s\S]{0,260}scrim)/i.test(
      heroModeContract
    ) &&
    /\.report-intro--with-media:is\([\s\S]{0,180}\.report-intro--integrated[\s\S]{0,180}\.report-intro--stage[\s\S]{0,220}\.report-intro__surface::after/.test(
      layoutContract
    ),
  'Integrated mode must require accepted media plus a page-token text-safe region or functional scrim.'
);
check(
  /\bintegrated\b[\s\S]{0,360}(?:missing|invalid|unsuitable|cannot)[\s\S]{0,240}\bcontained\b/i.test(
    heroModeContract
  ) &&
    /\bstage\b[\s\S]{0,320}(?:typographic|without media|no-image|image-free)/i.test(
      heroModeContract
    ),
  'Integrated must fall back to contained when media fails, while stage must remain valid as a typographic cover.'
);

check(
  [skill, layoutContract, shellScaffold, powershellScaffold].every(
    (source) => /\.report-intro--with-media/.test(source) && /\.report-intro--plain/.test(source)
  ) && /\.report-intro--with-media/.test(imageGuide),
  'The with-media and plain classes must remain documented and scaffold-compatible legacy modifiers.'
);

const heroSizingSources = [
  skill,
  defaultTheme,
  elementUsage,
  layoutContract,
  qaChecklist,
  visualBadcaseGates,
  imageGuide,
  shellScaffold,
  powershellScaffold,
].join('\n');
check(
  !/(?:44|65)%/.test(heroSizingSources),
  'Hero contracts must not retain the former global 44% media or 65% content split.'
);
check(
  /\.report-intro--stage(?:\s+\.report-intro__surface)?\s*\{[^}]*block-size\s*:\s*auto\s*;[^}]*min-block-size\s*:\s*clamp\(\s*36rem\s*,\s*88svh\s*,\s*58rem\s*\)\s*;/i.test(
    layoutContract
  ),
  'Stage geometry must use block-size:auto and min-block-size:clamp(36rem, 88svh, 58rem).'
);
const introCssSources = [
  ...[...layoutContract.matchAll(/```css\n([\s\S]*?)\n```/g)].map((match) => match[1]),
  shellTemplateMatch?.[1] ?? '',
  powershellTemplateMatch?.[1] ?? '',
].join('\n');
check(
  !/(?:height|block-size)\s*:\s*100(?:d|s|l)?vh\s*;/i.test(introCssSources),
  'Intro source must not use a fixed 100vh-family height.'
);

const layoutMediaBlocks = extractMediaBlocks(layoutContract);
check(
  layoutMediaBlocks.some(
    ({ condition, body }) =>
      /max-width/i.test(condition) &&
      /\.report-intro--integrated/.test(body) &&
      /\.report-intro--stage/.test(body) &&
      /inline-size\s*:/.test(body)
  ) &&
    /At narrow widths[\s\S]{0,260}(?:title-first|source order)[\s\S]{0,300}(?:change or remove media|wrap)/i.test(
      layoutContract
    ),
  'Non-default modes must provide a source-level narrow/mobile fallback that preserves text order and wrapping.'
);
check(
  hasStageAutoHeightFallback(layoutMediaBlocks, /max-height/i) &&
    layoutMediaBlocks.some(
      ({ condition }) => /max-height/i.test(condition) && /orientation\s*:\s*landscape/i.test(condition)
    ),
  'Stage source rules must fall back to content height in short landscape viewports.'
);
check(
  hasStageAutoHeightFallback(layoutMediaBlocks, /(?:^|,)\s*print\b/i),
  'Stage source rules must fall back to content height for print.'
);
check(
  hasStageAutoHeightFallback(layoutMediaBlocks, /forced-colors\s*:\s*active/i),
  'Stage source rules must fall back to content height in forced-colors mode.'
);
check(
  layoutMediaBlocks.some(
    ({ condition, body }) =>
      /prefers-reduced-motion\s*:\s*reduce/i.test(condition) &&
      (/\.report-intro--stage/.test(body) || /html\s*\{/.test(body)) &&
      /(?:scroll-behavior\s*:\s*auto|animation(?:-[\w-]+)?\s*:\s*none|transition(?:-[\w-]+)?\s*:\s*none|min-block-size\s*:\s*auto)\s*;/i.test(
        body
      )
  ),
  'Stage source rules must include a reduced-motion fallback.'
);

check(/mark\.key/.test(defaultTheme), 'The design reference must define the mark.key behavior.');
check(
  /<th scope="row">/.test(defaultTheme),
  'The design reference must make first-column emphasis semantic rather than positional.'
);
check(
  /accent (?:top, left, or full )?border/i.test(defaultTheme),
  'The design reference must prohibit decorative accent borders on content containers.'
);
check(
  /report-default-v1/.test(qaChecklist),
  'Final QA must verify the versioned default design contract.'
);
check(
  /Do not apply a second width cap[\s\S]{0,260}ordinary prose[\s\S]{0,180}available width/i.test(
    skill
  ) &&
    /Narrower measures[\s\S]{0,220}Intro summaries[\s\S]{0,180}split\/media columns[\s\S]{0,120}margin notes/i.test(
      skill
    ),
  'The core contract must keep ordinary prose on the available reading width while preserving explicit narrow-column exceptions.'
);
check(
  /validate-report-source\.mjs/.test(qaChecklist) &&
    /source-only gate[\s\S]{0,180}unscoped global `p` selector/i.test(normalize(qaChecklist)),
  'Final QA must run the lightweight paragraph-width source gate without rendering.'
);
check(
  /findParagraphWidthViolations/.test(reportSourceValidator) &&
    /max-width\|max-inline-size/.test(reportSourceValidator) &&
    !/(playwright|puppeteer|webdriver|http\.createServer)/i.test(reportSourceValidator),
  'The report source validator must check both width properties without browser or server tooling.'
);
check(
  /one explicitly named film or media work, product, or brand/.test(
    skill
  ) && /one bounded first-party lookup/.test(skill),
  'The core Intro contract must trigger one bounded official-image lookup for eligible named subjects.'
);
check(
  /lookup is required[\s\S]{0,120}use of the (?:image|media) remains conditional/i.test(
    normalize(skill)
  ),
  'The core Intro contract must distinguish the required lookup from the conditional image.'
);
check(
  /official key\s+art, still, product or lifestyle image, or brand imagery/.test(imageGuide) &&
    /A standalone logo does not satisfy this check/.test(imageGuide),
  'The image guide must define useful official Hero media and reject logo-only completion.'
);
check(
  /silent text-\s+only Intro fails/.test(qaChecklist),
  'Final QA must prevent eligible official Hero media from being skipped silently.'
);
check(
  /bounded official-Hero lookup[\s\S]{0,120}named-[\s\S]{0,40}subject trigger/.test(
    defaultTheme
  ) &&
    /one explicitly named film or media work, product, or brand/.test(
      normalize(elementUsage)
    ) &&
    /one explicitly named film or media work, product, or brand/.test(
      normalize(visualBadcaseGates)
    ),
  'Downstream design contracts must preserve the official Hero trigger.'
);
check(
  /Read `diagrams\/image-guide\.md` when the official-Hero trigger applies/.test(skill),
  'Conditional image routing must include the official Hero trigger, not only product or brand media.'
);
check(
  /film\/media, product, or brand Intro context/.test(elementUsage) &&
    /one explicitly named film or media work, product, or brand/.test(
      normalize(visualBadcaseGates)
    ),
  'Visual element exceptions must not omit film or media Hero imagery.'
);
check(
  /Core owns mode selection[\s\S]{0,220}local source and[\s\S]{0,80}fallback integrity/.test(
    layoutContract
  ) && /Missing or unsafe media becomes `contained`/.test(layoutContract),
  'Layout guidance must leave lookup decisions with Core while preserving source and fallback integrity.'
);
check(
  /user requests no image/.test(skill) &&
    /one bounded first-party lookup/.test(imageModeContract) &&
    /repeated search\/generation loop/.test(imageModeContract),
  'Official Hero fallback must respect no-image requests and prohibit repeated lookup loops.'
);
check(
  /Do not call AI image generation unless the user explicitly requests it/.test(skill) &&
    /Do not call ImageGen automatically/.test(imageGuide) &&
    /Do not narrate the lookup in the report body/.test(imageGuide),
  'Official Hero lookup must not trigger automatic generation or report-body narration.'
);
check(
  /Multi-item comparisons default to a neutral no-image Intro/.test(imageModeContract),
  'Multi-item Intro media must preserve the equal-representation fallback.'
);
check(
  /Intro media: USED — <owner\/source>/.test(skill) &&
    /Intro media: FALLBACK — <short reason>/.test(skill) &&
    /Record exactly one compact delivery result outside the report body/.test(qaChecklist),
  'Eligible Intro media decisions must produce one compact auditable delivery result.'
);
check(
  /attribution does not\s+grant reuse rights/.test(imageGuide) &&
    /external publication or distribution with unclear\s+rights/.test(imageGuide),
  'Official image provenance must not be treated as publication permission.'
);

check(
  /Do not open, navigate, inspect, or control the user's browser for report QA\./.test(skill),
  'The core contract must prohibit controlling the user browser for report QA.'
);
check(
  /A request to create, update, restyle, or deliver a report does not authorize browser validation\./.test(
    skill
  ),
  'Browser validation must require separate explicit authorization.'
);
check(
  /## 1\. Default Execution Boundary/.test(qaChecklist) &&
    /Do not invoke browser-control tools or browser plugins/.test(qaChecklist),
  'The QA checklist must default to static checks and prohibit browser-control tooling.'
);
check(
  /isolated test browser/.test(qaChecklist) &&
    /Never reuse or control the user's existing browser/.test(qaChecklist),
  'Optional rendered QA must stay isolated from the user browser.'
);
check(
  /source-checkable V0 rules through static\s+inspection/.test(visualBadcaseGates),
  'Visual badcase gates must define a static default path.'
);
check(
  /Static QA is the default/.test(interactivePrd) &&
    /does\s+not authorize browser control/.test(interactivePrd),
  'Interactive PRD QA must inherit the no-browser default.'
);
check(
  /Static acceptance checks validate configuration and source consistency/.test(chartContract) &&
    /Rendered legend, tooltip, label, and mark behavior remains `NOT RUN`/.test(chartContract),
  'The chart contract must separate static acceptance from rendered behavior.'
);
check(
  /Static QA verifies declared sizes, labels, grouping, and complexity limits/.test(diagramContract) &&
    /Rendered node readability, crossings, clipping, and zoom behavior remain `NOT RUN`/.test(
      diagramContract
    ),
  'The diagram contract must not imply rendered acceptance in the default flow.'
);
check(
  /Static image QA verifies local file integrity, metadata, paths, source records, and responsive rules/.test(
    imageGuide
  ) && /Rendered crop, contrast, narrow-width readability, and offline loading remain `NOT RUN`/.test(
    imageGuide
  ),
  'The image guide must keep rendered image checks outside default QA.'
);
check(
  /validates this Skill package, not a generated report/.test(qaChecklist),
  'The QA checklist must distinguish package-contract validation from report QA.'
);
check(
  /non-zero `height` or `min-height`/.test(chartContract) &&
    /ECharts library script appears before `assets\/charts\.js`/.test(chartContract) &&
    /initialization runs after its DOM container exists/.test(chartContract),
  'Static chart acceptance must guard against blank containers and invalid initialization order.'
);
check(
  /if \(!textDoc\) return;/.test(interactivePrd) &&
    /if \(prototypeRoot\) \{/.test(interactivePrd),
  'Interactive PRD examples must guard optional DOM targets when runtime QA is not run.'
);

const removedUnconditionalBrowserRequirements = [
  ['SKILL.md', skill, 'Run final visual QA in a real rendered browser before delivery.'],
  ['references/qa-checklist.md', qaChecklist, 'If browser tooling is unavailable, report QA as blocked'],
  [
    'references/visual-badcase-gates.md',
    visualBadcaseGates,
    'Before finishing a report, inspect the rendered output over local HTTP',
  ],
  [
    'references/interactive-prd.md',
    interactivePrd,
    'Static source inspection may supplement these checks but does not replace rendered validation.',
  ],
  [
    'references/chart-contract.md',
    chartContract,
    'Legends and tooltips match rendered mark colors.',
  ],
  [
    'diagrams/image-guide.md',
    imageGuide,
    'Verify that the local file decodes and that its crop remains useful at desktop and mobile widths before including it.',
  ],
  [
    'diagrams/image-guide.md',
    imageGuide,
    'Verify at least `4.5:1` contrast for normal text and `3:1` for large text in every crop',
  ],
  [
    'diagrams/image-guide.md',
    imageGuide,
    'verify that narrow cropping does not hide the subject or collide with the text',
  ],
  [
    'diagrams/image-guide.md',
    imageGuide,
    'verify desktop/mobile crop, readability, alt behavior, and offline loading',
  ],
];
for (const [relativePath, source, obsoleteRequirement] of removedUnconditionalBrowserRequirements) {
  const normalizedSource = source.replace(/\s+/g, ' ');
  const normalizedRequirement = obsoleteRequirement.replace(/\s+/g, ' ');
  check(
    !normalizedSource.includes(normalizedRequirement),
    `${relativePath} still contains an unconditional browser-QA requirement.`
  );
}

if (failures.length > 0) {
  console.error('html-report skill contract: FAIL');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('html-report skill contract: PASS');
