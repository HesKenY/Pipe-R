# REVV Master Repo Layout

This repo is structured as a master workspace with one public deploy target and two internal tools.

## Public Website

- `site/index.html` - public REVV business site
- `site/privacy.html` - public privacy policy
- `site/terms.html` - public terms page
- `site/tools/index.html` - internal launcher page

## Internal Apps

- `site/apps/revv-main/` - REVV Main web app copy for internal launches
- `site/apps/jsgarage/` - JsGarage internal instance manager

## Android

- `android/` - Android Studio project for REVV Main
- `scripts/copy-android-project.ps1` - copies the Android source into `site/apps/revv-main/android/` when you need the backup view
- `ANDROID_COPY_SOURCE.md` - plain-language note for where the Android source lives and how to copy it out

## Netlify

Netlify is configured to publish `site/` so the public website is the live deploy.

## Supabase

The Supabase schema and setup notes live at:

- `supabase/`
- `supabase.sql`
- `supabase-fix.sql`
- `SUPABASE_SETUP_INSTRUCTIONS.md`
