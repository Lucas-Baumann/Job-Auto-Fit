---
name: readme-optimization
description: Optimize README and public-facing content for GitHub discoverability, clear presentation flow, and accurate feature positioning
user-invocable: true
metadata:
  mcpmarket-version: 1.0.0
---
# README Optimization

## Task

Review and optimize the README.md and repository metadata for discoverability, clear value communication, and accurate feature presentation.

## Instructions

1. Read the current README.md and repository description
2. Evaluate against each area below
3. Suggest specific copy improvements with before/after examples

## Review Areas

### First Impression (Above the Fold)

- Value proposition clear in the first 3 lines: what the project is and who it's for
- Demo visual present (screenshot or GIF showing the project in action)
- Key differentiators immediately visible
- Quick Start commands visible without scrolling on desktop

### GitHub Search Optimization

- Repository description includes the most important searchable terms for the project's domain
- Topics include relevant technology tags (e.g., framework names, domain keywords)
- README headings match common search queries users would type to find this project
- Feature and concept names match how the target audience searches for them

### Content Hierarchy

- **Primary audience first**: Core features and usage before technical implementation details
- **Secondary audience second**: Integration, customization, and advanced usage
- **Contributors third**: Architecture overview, contributing guide links
- Progressive detail: summaries with links to `docs/` for deep dives

### AIDA Presentation Flow

- **Attention**: Visual demo (GIF/screenshot) showing the project
- **Interest**: Feature bullet list highlighting what makes the project unique
- **Desire**: Concrete examples or table showing the breadth of what the project provides
- **Action**: Quick Start with copy-pasteable commands

### Accuracy

- All listed features and capabilities actually exist in the codebase
- Scripts/commands table matches project manifest (e.g., `package.json`, `Makefile`, `pyproject.toml`)
- Any listed keyboard shortcuts or CLI flags match the actual implementation
- Technology versions match the project manifest

### Developer Friendliness

- Quick Start works on fresh clone (no hidden prerequisites)
- Links to detailed docs are not broken
- No marketing language that obscures technical content

## Rules

- No superlatives or hype — let features speak for themselves
- All claims must be verifiable from the codebase
- No references to AI, Claude, or automated generation
- Keep README scannable — prefer tables and bullets over prose

## Output Format

- EFFECTIVE: [area] - what works well and why
- OPTIMIZE: [area] - specific improvement with suggested copy
- GAP: [area] - missing content + draft to fill it
