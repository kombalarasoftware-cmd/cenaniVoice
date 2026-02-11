---
paths:
  - "frontend/**/*.{ts,tsx}"
---

# Frontend React/Next.js Rules

- TypeScript strict mode, no `any` type
- Use App Router (not Pages Router)
- Components: functional only, with TypeScript interface for props
- Data fetching: TanStack React Query (useQuery/useMutation)
- Forms: React Hook Form + Zod schemas
- Styling: Tailwind CSS utility classes, use cn() for conditionals
- UI primitives: shadcn/ui (Radix) components
- API calls through `src/lib/api.ts` client
- State: React Query for server state, React Context for global UI state
- Loading/error states required on all async operations
