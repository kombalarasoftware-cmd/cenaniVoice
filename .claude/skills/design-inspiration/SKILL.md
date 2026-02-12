---
name: design-inspiration
description: Research modern UI patterns and design references before building
allowedTools:
  - Read
  - Glob
  - Grep
  - WebSearch
  - WebFetch
  - mcp__plugin_playwright_playwright__browser_navigate
  - mcp__plugin_playwright_playwright__browser_take_screenshot
  - mcp__plugin_playwright_playwright__browser_snapshot
  - mcp__plugin_playwright_playwright__browser_resize
---

# Design Inspiration Skill

Research and analyze modern UI patterns before implementing any significant frontend work.

## When to Use
- Before building a new page or major component
- When the user wants a distinctive, non-generic design
- When redesigning an existing page for better visual quality
- When unsure about the right visual approach

## Research Workflow

### Step 1: Understand the Component Type
Identify what you're building:
- Dashboard / Analytics page
- Landing / Marketing page
- Settings / Configuration page
- Data table / List view
- Form / Wizard flow
- Detail / Profile page
- Auth (login/register) page

### Step 2: Search for References
Search for modern examples:
```
"[component type] UI design 2026 dark mode"
"[component type] dashboard dribbble"
"best SaaS [component type] design inspiration"
"[component type] figma template premium"
```

### Step 3: Analyze Reference Designs
For each reference, extract:
- **Layout**: Grid structure, sidebar placement, content hierarchy
- **Colors**: Primary palette, accent usage, gradient direction
- **Typography**: Font sizes, weights, line heights, letter spacing
- **Spacing**: Padding, margins, gap between elements
- **Components**: Card styles, button variants, input styles
- **Animation**: Entrance effects, hover states, transitions
- **Special effects**: Blur, gradients, shadows, borders

### Step 4: Check Existing Project Patterns
Before implementing, review the project's existing design language:
1. Read `frontend/tailwind.config.ts` for theme tokens
2. Check `frontend/src/components/ui/` for existing primitives
3. Look at similar existing pages for consistency
4. Ensure the new design extends (not contradicts) the current system

### Step 5: Create a Design Brief
Summarize findings before coding:
- Chosen visual style and why
- Key design patterns to apply
- Color and typography decisions
- Animation strategy
- Responsive considerations

## Reference Sites to Search
- **Linear.app** — Clean dark SaaS with purple accents
- **Vercel.com** — Minimal, high-contrast, elegant
- **Stripe Dashboard** — Data-dense but readable
- **Raycast.com** — macOS-native feel, command palette
- **Arc Browser** — Bold colors, playful gradients
- **Figma.com** — Creative tool aesthetic
- **Notion.so** — Clean, content-focused
- **Railway.app** — Developer-friendly dark UI

## Output
Present the design brief to the user before coding, including:
1. Visual style description (1-2 sentences)
2. Reference screenshots (if available via Playwright)
3. Key patterns to apply
4. Any questions about user preferences
