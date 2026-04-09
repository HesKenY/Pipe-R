# CHERP Modular — Roadmap

## What It Is
Construction Helper for Efficient Resource Planning — modular PWA + Android app for crew management, built with pure JS/Supabase/Capacitor.

## Tech Stack
- Pure HTML/CSS/JS (no frameworks) — mobile-first, gloved-hand UX
- Supabase PostgreSQL backend (optional, localStorage-first)
- Capacitor 6.0.0 for Android
- Service Worker (offline-capable PWA)
- Custom module loader with dependency resolution + role-based access

## Architecture

```
cherp-modular/
├── index.html          (90 LOC)   ← App shell
├── cherp-modular.html  (1,224 LOC)← Single-file build
├── main.js             (275 LOC)  ← Boot sequence + module init
├── sw.js               (102 LOC)  ← Service worker (cache-first)
├── core/                          ← Always-loaded foundation
│   ├── module-loader.js (191)     ← Dynamic loader + topological sort
│   ├── auth/auth.js     (313)     ← PIN auth + SHA-256 + biometric
│   ├── roles/roles.js   (134)     ← 6-tier role hierarchy (57 perms)
│   ├── api/supabase.js  (197)     ← Supabase wrapper
│   ├── ui/shell.js      (265)     ← Top bar, nav, modals, toasts
│   └── ui/styles.css    (400)     ← Dark theme, responsive
├── modules/             (10 feature modules)
├── config/              ← Instance + module config
├── build/build.js       ← Tree-shaking build script
└── android/             ← Capacitor native build (CHERP-Modular-App/)
```

**Total LOC**: ~5,800

---

## What's Built — Module Status

### Core System — COMPLETE
- [x] Module loader with dependency resolution (Kahn's algorithm)
- [x] PIN authentication (SHA-256, lockout, session timeout)
- [x] 6-tier role system (apprentice → superuser, 57 permissions)
- [x] Supabase client wrapper
- [x] UI shell (top bar, bottom nav, modals, toasts)
- [x] Dark theme, 48px+ touch targets
- [x] PWA manifest + service worker (offline-capable)
- [x] Build script with module tree-shaking

### Feature Modules (10/11 working)

| Module | Role | LOC | Status |
|--------|------|-----|--------|
| Time Clock | Apprentice | 201 | DONE — punch in/out, weekly timecard, OT calc, GPS indicator |
| Calculator | Apprentice | 168 | DONE — pipe, concrete, material estimator |
| Task List | Apprentice | 137 | DONE — kanban board, priority, assignee |
| Messaging | Apprentice | 159 | STUB — UI only, no storage/sync |
| Safety | Apprentice | 275 | DONE — JSA builder, incidents, checklist, certifications |
| Inventory | Journeyman | 241 | DONE — materials, bin locations, checkout/return, low-stock alerts |
| MRO | Journeyman | 217 | DONE — equipment tracking, work orders, maintenance schedule |
| Documents | Journeyman | 171 | DONE — upload, categorize, version tracking |
| Daily Log | Foreman | 179 | DONE — weather, crew, notes, date navigation |
| Reports | Admin | 291 | DONE — daily/weekly/timecard/safety/MRO, print-ready |
| Admin Panel | Admin | — | NOT BUILT |

---

## Phase 1: Core + Modules — 90% COMPLETE
- [x] Auth system (PIN + biometric + lockout)
- [x] Role-based access (6 tiers, 57 permissions)
- [x] Module loader + config system
- [x] 10 feature modules (9 fully working)
- [x] PWA (service worker, manifest, offline)
- [x] Build script
- [~] Messaging module (UI only, needs backend)
- [ ] Admin Panel module

## Phase 2: Backend Integration — NOT STARTED
- [ ] Configure Supabase project (create tables from migrations)
- [ ] Enable RLS policies
- [ ] Sync Time Clock punches to Supabase
- [ ] Sync Task List to Supabase
- [ ] Sync Safety reports to Supabase
- [ ] Sync Inventory to Supabase
- [ ] Sync Daily Log to Supabase
- [ ] Real-time subscriptions (live updates across devices)
- [ ] Complete Messaging module (Supabase Realtime channels)

## Phase 3: Android Build — NOT STARTED
- [ ] Build APK with Capacitor (`npx cap sync && gradlew assembleDebug`)
- [ ] Test on physical device
- [ ] Generate app icons + splash screens
- [ ] Add native GPS (Capacitor Geolocation plugin)
- [ ] Add native biometrics (Capacitor BiometricAuth plugin)
- [ ] Add photo capture to Daily Log (Capacitor Camera plugin)
- [ ] Signed release build
- [ ] Play Store listing

## Phase 4: Production Hardening — NOT STARTED
- [ ] Admin Panel (user CRUD, audit log viewer, settings editor)
- [ ] Conflict resolution (offline edits vs server state)
- [ ] Data export (CSV/PDF from Reports module)
- [ ] Push notifications (shift reminders, task assignments)
- [ ] Multi-company support (instance isolation)
- [ ] CI/CD pipeline (auto-deploy web + build APK)

## Phase 5: Advanced Features — FUTURE
- [ ] Crew scheduling / shift calendar
- [ ] Drawing markup (annotate blueprints on-device)
- [ ] QR code scanning for inventory
- [ ] Geofencing (auto clock-in when arriving at job site)
- [ ] Payroll export integration
- [ ] Foreman approval workflows (timecards, safety reports)

---

## Priority — What's Next

### High
1. **Messaging module** — wire up localStorage storage at minimum, Supabase Realtime ideal
2. **Android APK** — first build + device test
3. **Supabase setup** — create project, run migrations, configure instance.json

### Medium
4. **Admin Panel** — user management is needed before multi-user deployment
5. **Photo capture** — Daily Log needs camera integration
6. **Data export** — Reports should output CSV/PDF

### Low
7. Native GPS/biometrics via Capacitor plugins
8. Push notifications
9. Advanced features (scheduling, geofencing, QR)

---

## Stats
- **Total LOC**: ~5,800
- **Modules**: 10 built (9 fully working, 1 stub)
- **Core components**: 6 (loader, auth, roles, API, shell, styles)
- **Roles**: 6 tiers, 57 permissions
- **Data**: localStorage-first, Supabase-ready
- **Platforms**: Web PWA + Android (Capacitor 6.0.0)
