---
paths:
  - "frontend/components/**/*.tsx"
  - "frontend/app/**/*.tsx"
---

# React Component Rules
- Use shadcn/ui primitives before creating custom components
- Use cn() from lib/utils for conditional class merging
- Client components must have "use client" directive at the top
- Server components are the default — avoid "use client" unless needed
- Use React Query v5 for data fetching (useQuery, useMutation)
- Forms must use react-hook-form + Zod resolver
- Handle loading, error, and empty states for all data-driven components
- Use sonner for toast notifications
- Use lucide-react for icons
