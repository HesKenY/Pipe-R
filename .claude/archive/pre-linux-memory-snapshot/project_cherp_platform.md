---
name: CHERP Platform Architecture
description: CHERP is a multi-program platform — app, website, web version, Android offline app, and Nest backend. Modular rebuild went wrong.
type: project
originSessionId: c25daccd-a89c-4ade-896e-c5ad4a5ab41b
---
CHERP is a platform made up of multiple related programs:

1. **CHERP (the platform/app)** — The core running application. Construction crew management with time clocks, JSAs, calculators, material tracking, crew messaging.

2. **The Website** — Marketing/landing site for cherp.live. Separate from the app itself.

3. **Web Version** — The website with a live instance of CHERP attached and running. Online mode, Supabase-backed.

4. **App Version (Android)** — A local clone of CHERP modified to use localStorage in offline mode unless logged into an online account. Has an Android Studio project built within it. The best working version is installed on Ken's phone as "cherp-worker".

5. **Bird's Nest (Nest)** — Backend superuser program for:
   - Managing and maintaining customer instances of CHERP
   - All business operations for serving CHERP customers
   - Tool for creating cloned and customized CHERP instances for customers
   - Builds customer-specific zips for deployment

**Modular design goal:** CHERP was being rebuilt as modular so customers could pick which features to implement. Nest would build customized instances as deployable zips.

**Critical issue (2026-04):** During the modular rebuild, the best working version of CHERP was lost. The modular build became "something completely different and unusable." The last known good version is what's installed on Ken's Android as cherp-worker.

**Why:** This is the core context for all CHERP work. The immediate priority is recovering the good working version.

**How to apply:** The modular repo (HesKenY/CHERP current state) is NOT the good version. Need to find the pre-modular or early-modular commit that matches cherp-worker.
