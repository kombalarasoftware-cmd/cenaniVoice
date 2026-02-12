---
globs: ["frontend/src/**/*.tsx", "frontend/src/**/*.css"]
---

# Frontend Design Standards

## Visual Quality Requirements
- Every page must feel like a premium SaaS product (reference: Linear, Vercel, Stripe)
- Dark mode is the PRIMARY theme — design dark-first, adapt to light
- Use Framer Motion for all page transitions and interactive animations
- Loading states: skeleton screens with shimmer, never spinning loaders
- Every interactive element needs hover/focus/active/disabled states

## Forbidden Patterns (Generic AI Look)
- Plain white/gray backgrounds with basic card grids
- Default unstyled shadcn/ui without customization
- Symmetric boring grid layouts with no visual rhythm
- Missing hover/focus states on interactive elements
- Hard page transitions without animation
- `console.log` or inline styles in production
- Same font weight and size throughout a section

## Required Patterns (Distinctive Design)
- Glassmorphism for overlays: `backdrop-blur-xl bg-white/5 border border-white/10`
- Gradient accents on hero sections and key CTAs
- Typography contrast: mix font-light/font-normal/font-bold deliberately
- Generous whitespace: `space-y-8` or `gap-8` between sections minimum
- Layered depth: shadows, overlapping elements, z-index layering
- Color-coded status with subtle glow: `shadow-[0_0_12px_rgba(var,0.3)]`
- Smooth transitions: `transition-all duration-300 ease-out` on interactive elements
- Staggered entrance animations for lists and grids (Framer Motion)

## Component Standards
- Use `cn()` utility for conditional class merging
- Wrap page content in Framer Motion `<motion.div>` for entrance animations
- Charts and data visualizations: use branded color palette, not defaults
- Tables: zebra striping with `even:bg-white/[0.02]`, sticky headers
- Forms: floating labels or top-aligned labels, inline validation
- Modals: backdrop blur, scale-up entrance animation
- Toasts: slide-in from top-right with auto-dismiss

## Responsive Breakpoints
- Mobile-first: base styles are mobile
- `sm:` (640px) — large phones
- `md:` (768px) — tablets
- `lg:` (1024px) — small laptops
- `xl:` (1280px) — desktops
- `2xl:` (1536px) — large screens
- Critical: test all 3 viewports (mobile 375px, tablet 768px, desktop 1440px)
