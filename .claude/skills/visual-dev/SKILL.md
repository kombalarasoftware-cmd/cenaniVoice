---
name: visual-dev
description: Build UI with visual feedback loop — design, preview, iterate
allowedTools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - WebSearch
  - WebFetch
  - mcp__plugin_playwright_playwright__browser_navigate
  - mcp__plugin_playwright_playwright__browser_take_screenshot
  - mcp__plugin_playwright_playwright__browser_snapshot
  - mcp__plugin_playwright_playwright__browser_evaluate
  - mcp__plugin_playwright_playwright__browser_click
  - mcp__plugin_playwright_playwright__browser_resize
  - mcp__plugin_playwright_playwright__browser_console_messages
  - mcp__plugin_playwright_playwright__browser_run_code
  - mcp__plugin_playwright_playwright__browser_wait_for
---

# Visual Development Skill

Build stunning, distinctive frontend interfaces with a visual feedback loop.

## Workflow

### Phase 1: Research (if building a new page/component)
1. Understand what the user wants to build
2. Search for modern UI references if needed (Dribbble, Awwwards, Linear, Vercel)
3. Identify the visual style: glassmorphism, neumorphism, bold gradients, minimal, etc.

### Phase 2: Build
1. Write the component/page code using:
   - shadcn/ui as base primitives
   - Tailwind CSS for styling
   - Framer Motion for animations
   - CSS variables for theming
2. Ensure dark mode is the primary theme
3. Add micro-interactions: hover states, focus rings, transitions

### Phase 3: Visual Preview Loop (CRITICAL)
1. Ensure the dev server is running (`npm run dev` in frontend/)
2. Navigate to the page with Playwright: `browser_navigate` to `http://localhost:3000/[path]`
3. Take a screenshot: `browser_take_screenshot`
4. Analyze the visual result critically:
   - Is the layout balanced? Any awkward spacing?
   - Are colors harmonious? Sufficient contrast?
   - Do elements have proper hierarchy (size, weight, color)?
   - Is it responsive? Check mobile viewport with `browser_resize`
5. Fix issues found in the analysis
6. Take another screenshot — repeat until polished
7. **Minimum 2 iterations** before presenting to user

### Phase 4: Responsive Check
1. Desktop (1440px): `browser_resize` width=1440, height=900
2. Tablet (768px): `browser_resize` width=768, height=1024
3. Mobile (375px): `browser_resize` width=375, height=812
4. Screenshot each viewport, fix layout issues

### Phase 5: Polish
1. Check all interactive states (hover, focus, active, disabled)
2. Verify loading states use skeleton screens (not spinners)
3. Ensure smooth page transitions with Framer Motion
4. Validate WCAG AA contrast ratios

## Design Principles

### DO (Distinctive Premium Look)
- Rich gradients with multiple color stops
- Glassmorphism: `backdrop-blur-xl bg-white/5 border border-white/10`
- Bold typography contrast: thin headers (font-light) vs heavy emphasis (font-bold)
- Generous whitespace — let elements breathe
- Layered depth: overlapping elements, elevation shadows
- Micro-animations on every interactive element (150-300ms)
- Skeleton loading screens with shimmer effect
- Subtle background patterns or grain textures
- Color-coded status indicators with glow effects

### DON'T (Generic AI Look)
- Plain white backgrounds with basic card grids
- Default unstyled shadcn/ui components
- Symmetric, boring grid layouts
- Missing hover/focus states
- Hard page transitions (no animation)
- Spinning loaders instead of skeletons
- Generic placeholder text or stock images
- Same font weight throughout the page

## Animation Patterns (Framer Motion)

```tsx
// Page entrance
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.5, ease: "easeOut" }}
>

// Staggered list
<motion.div variants={container} initial="hidden" animate="show">
  {items.map(item => (
    <motion.div key={item.id} variants={listItem}>
      {item.content}
    </motion.div>
  ))}
</motion.div>

// Hover scale
<motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>

// Skeleton loading
<div className="animate-shimmer bg-gradient-to-r from-transparent via-white/10 to-transparent" />
```

## Color Usage Guide
- Primary (purple/indigo): CTAs, active states, links
- Secondary (cyan/teal): Info, secondary actions, charts
- Accent (amber/gold): Highlights, badges, notifications
- Gradients: Hero sections, card backgrounds, button highlights
- Always use opacity variants for backgrounds: `bg-primary-500/10`
