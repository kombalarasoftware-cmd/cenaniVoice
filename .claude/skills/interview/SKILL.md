---
description: Interview the user to gather detailed requirements before implementing a feature
---

# Feature Interview

Before implementing, interview the user to understand requirements fully.

## Process

1. **Read the codebase** to understand existing patterns and architecture
2. **Ask probing questions** using the AskUserQuestion tool about:
   - Technical implementation approach
   - UI/UX expectations
   - Edge cases and error scenarios
   - Performance requirements
   - Security considerations
   - Integration points with existing code
3. **Identify gaps** the user may not have considered
4. **Write a complete spec** to SPEC.md when the interview is done

## Question Categories

### Technical
- What data models/schemas are involved?
- What API endpoints are needed?
- How does this interact with existing services?
- Are there concurrency or race condition concerns?

### UX
- What happens on success? On failure?
- Loading states? Empty states?
- Mobile responsiveness requirements?
- Accessibility needs?

### Edge Cases
- What if the input is invalid?
- What if the external service is down?
- What about rate limiting?
- What about partial failures?

### Scope
- What is the minimum viable implementation?
- What can be deferred to a follow-up?

## Output
After the interview, create a `SPEC.md` file with:
- Feature summary
- Technical approach
- Data model changes
- API changes
- UI changes
- Edge cases and error handling
- Test plan
