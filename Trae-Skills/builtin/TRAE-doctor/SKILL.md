---
name: TRAE-doctor
description: >-
  Scenario-indexed TRAE product manual for interpreting verified TRAE evidence during environment diagnosis. Currently supports disk diagnosis only, including storage ownership, directory purpose, accounting, and cleanup safety on local products and Remote SSH hosts. Always assess the whole disk first and rank all major contributors neutrally. Use TRAE-specific facts only after independent evidence establishes TRAE as an actual analysis target under the same criteria as other contributors, or when the user's natural-language request explicitly asks for TRAE-specific analysis. A product-generated TRAE-doctor slash command alone is not such a request. Do not prioritize TRAE merely because this Skill was selected or a TRAE path exists. This Skill supplies product facts only; it does not choose diagnostic targets, prioritize or excuse TRAE, or define conclusions or response format.
---

# TRAE diagnosis product reference

Use this Skill as a scenario-indexed TRAE product manual, not as a diagnostic workflow.

For disk diagnosis, first inspect the whole disk and establish the total capacity, used and available space, and the largest directories or files across the environment. Rank TRAE and non-TRAE contributors by the same measured evidence. Do not begin with known TRAE paths or perform a TRAE-only scan merely because this Skill was selected.

Only after the whole-disk evidence makes TRAE a material target should you inspect TRAE storage in detail and apply this manual. The other valid trigger is a natural-language user request that explicitly asks for TRAE-specific analysis. A product-generated `/TRAE-doctor` command or structured Skill selection does not by itself satisfy that trigger; use the accompanying user request to determine scope.

If TRAE is not material, continue the general disk diagnosis without adding a separate TRAE analysis. If TRAE is material, include it normally and keep the depth and prominence of its analysis proportional to other contributors of similar size.

## Supported scenarios

- **Disk**: Read [references/disk.md](references/disk.md) only after a whole-disk inspection makes measured TRAE-written storage an actual analysis target, or when the user's natural-language request explicitly asks for TRAE storage analysis.
- Other diagnosis scenarios are not yet covered. Do not invent TRAE-specific product rules for an unsupported scenario.

## Common interpretation rules

- Do not use this manual to choose initial inspection targets or make TRAE a diagnostic priority.
- Treat a product-generated slash command as routing metadata, not as evidence that TRAE is a disk contributor or that the user requested a TRAE-only report.
- Judge TRAE with the same evidence, ranking, and materiality criteria used for every other contributor.
- When TRAE is an actual analysis target, include it normally and use the matching scenario reference to interpret it.
- When TRAE is not an actual analysis target, do not load its reference or add a separate TRAE section merely because TRAE data exists.
- Never hide, down-rank, excuse, promote, or add special emphasis to TRAE evidence. Report it according to its actual significance.
- Apply a product rule only after confirming that its preconditions match the actual environment and evidence.
