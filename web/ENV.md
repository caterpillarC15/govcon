# Web env contract

Every variable the Next.js `/web` app reads. Lives in `web/.env.local` (gitignored locally) or in Vercel project Settings → Environment Variables (Production scope) for prod.

## Keys

```
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_BASE=http://localhost:8000
NEXT_PUBLIC_SITE_URL=http://localhost:3000
NEXT_PUBLIC_APP_URL=http://localhost:3001
SUPABASE_SERVICE_ROLE_KEY=
ALLOW_DEV_LOGIN=true
DEV_USER_EMAIL=dev@local.test
DEV_USER_PASSWORD=devonly-not-for-prod
```

## Per-key

| Variable | Visibility | Purpose |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | browser | Supabase project URL — same as API's `SUPABASE_URL` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | browser | Publishable anon key (`sb_publishable_…`). Safe in client bundle |
| `NEXT_PUBLIC_API_BASE` | browser | FastAPI base — `http://localhost:8000` dev / `https://api.<domain>` prod |
| `NEXT_PUBLIC_SITE_URL` | browser | Landing canonical URL — `og:url`, sitemap, brand canonicals |
| `NEXT_PUBLIC_APP_URL` | browser | `/web` URL — magic-link `emailRedirectTo` derives from this |
| `SUPABASE_SERVICE_ROLE_KEY` | server-only | Used by `signInAsDev` server action's admin client. Same value as API's |
| `ALLOW_DEV_LOGIN` | server-only | `true` renders the amber "Sign in as dev" button on `/login`. Never set in prod |
| `DEV_USER_EMAIL` | server-only | Dev-skip user email. Default `dev@local.test`. Never set in prod |
| `DEV_USER_PASSWORD` | server-only | Dev-skip user password. Never set in prod |

## Vercel production overrides

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://vvyxjdoenjujkxwbnzyl.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `sb_publishable_…` (anon, NOT service role) |
| `NEXT_PUBLIC_SITE_URL` | `https://samrail.com` |
| `NEXT_PUBLIC_APP_URL` | `https://app.samrail.com` |
| `NEXT_PUBLIC_API_BASE` | `https://api.samrail.com` (after VX1 ships) |
| `SUPABASE_SERVICE_ROLE_KEY` | NEVER on Vercel — server-only, VX1 only |
| `ALLOW_DEV_LOGIN` / `DEV_USER_*` | NEVER on Vercel |

After saving env vars on Vercel, **redeploy with build cache disabled** — `NEXT_PUBLIC_*` are baked at build time.

## Variable visibility model

- `NEXT_PUBLIC_*` prefix → inlined into the client bundle at build time. Browser-visible.
- Anything else → server-side only (Server Components, Route Handlers, Server Actions). Never reaches the browser bundle.
