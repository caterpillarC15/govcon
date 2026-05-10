# Landing (Next.js)

## Getting started

```bash
npm install
npm run dev
```

Then open `http://localhost:3000`.

## Scripts

- `npm run dev`: local dev server
- `npm run build`: production build
- `npm run start`: run the production server
- `npm run lint`: run ESLint
- `npm run typecheck`: run TypeScript typecheck

## Waitlist

The waitlist form on the landing page POSTs to `${NEXT_PUBLIC_API_BASE}/waitlist`, which inserts into Supabase `waitlist_signups`. Per PRD §5.14 (v1.2.6), waitlist signups are also enrolled in the **weekly opportunity email** by default (`weekly_opportunity_enabled=true`). The form copy must reflect this cadence; unsubscribe is one-click from every email and works without login.
