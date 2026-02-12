---
applyTo: "**/*.ts,**/*.tsx"
---

# TypeScript Code Instructions

- Never use any, use explicit types, generics, or unknown
- Use explicit return types on all exported functions
- Use early return pattern to reduce nesting
- Validate all external data with Zod schemas
- Use React Query v5 (useQuery, useMutation) for server state
- Use next/navigation for App Router (not next/router)
- Components must use shadcn/ui primitives where available
- Use cn() utility from lib/utils for conditional class merging
- Prefer named exports over default exports
- Use interface for object shapes, type for unions and intersections
