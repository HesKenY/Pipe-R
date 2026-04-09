# REVV Main Supabase Setup Instructions

Use this sheet when you open the new Supabase project for the REVV instance.

## 1) What I Need From Supabase

Fill these in once the project is created:

- Supabase project ref: `dkeqwmjwutgcvdwplzbe`
- Supabase project URL: `https://dkeqwmjwutgcvdwplzbe.supabase.co`
- `anon` / publishable key: `sb_publishable_DiWn5YXK4kefp0vZPlFotw_PP7RVWvn`
- `service_role` key:
- Default company name:
- Default dispatch team name:
- Optional seed crew names:

Keep the `service_role` key out of the client app. Use it only on the server side if you add admin automation later.

## 2) Load The Base Schema

Open the Supabase SQL Editor and run these files in order:

1. `supabase.sql`
2. `supabase-fix.sql`

If the base schema already exists, run the fix file first only if you need to temporarily open access for testing.

## 2a) CLI Setup Commands

Run these from the project root:

```powershell
supabase login
supabase init
supabase link --project-ref dkeqwmjwutgcvdwplzbe
```

If you want to connect to the database directly, use the full connection string with the real password inserted:

```text
postgresql://postgres:[YOUR-PASSWORD]@db.dkeqwmjwutgcvdwplzbe.supabase.co:5432/postgres
```

If you are going to use migrations later, the next useful command is:

```powershell
supabase db push
```

Only run that after the schema files are ready to be applied.

## 3) What The Schema Creates

The current REVV schema is designed to support:

- user profiles and roles
- app settings
- audit logging
- session tracking
- time punches
- task boards
- safety reports
- daily logs
- messages
- fleet / equipment tracking
- work orders and related operations tables

That structure is meant for an auto transportation operation, not a construction company.

## 4) What To Verify After Import

- `user_profiles` exists and can be read for login lookup
- `tasks`, `time_punches`, and `session_log` exist
- `safety_reports` is available for incident / compliance tracking
- fleet and work order tables are present for dispatch and maintenance
- row-level security is enabled on the tables you want protected

## 5) App Connection Notes

When you send the codes over, wire them into the REVV instance config:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- any server-side admin key only in backend code

If you want me to do the wiring next, send the values exactly as Supabase gives them to you.

## 6) Suggested First Seed Data

Use a small seed set for the first pass:

- 1 company
- 1 dispatch team
- 3 to 5 users
- 2 to 3 trucks
- 2 to 3 trailers
- a few tasks, punch records, safety entries, and route notes

That gives the demo enough realism without making the project hard to maintain.
