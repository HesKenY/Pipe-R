# REVV Modular â€” Roadmap

## What It Is
Construction Helper for Efficient Resource Planning â€” modular PWA + Android app for crew management, built with pure JS/Supabase/Capacitor.

## Tech Stack
- Pure HTML/CSS/JS (no frameworks) â€” mobile-first, gloved-hand UX
- Supabase PostgreSQL backend (optional, localStorage-first)
- Capacitor 6.0.0 for Android
- Service Worker (offline-capable PWA)
- Custom module loader with dependency resolution + role-based access

## Architecture

```
revv-modular/
â”œâ”€â”€ index.html          (90 LOC)   â† App shell
â”œâ”€â”€ revv-modular.html  (1,224 LOC)â† Single-file build
â”œâ”€â”€ main.js             (275 LOC)  â† Boot sequence + module init
â”œâ”€â”€ sw.js               (102 LOC)  â† Service worker (cache-first)
â”œâ”€â”€ core/                          â† Always-loaded foundation
â”‚   â”œâ”€â”€ module-loader.js (191)     â† Dynamic loader + topological sort
â”‚   â”œâ”€â”€ auth/auth.js     (313)     â† PIN auth + SHA-256 + biometric
â”‚   â”œâ”€â”€ roles/roles.js   (134)     â† 6-tier role hierarchy (57 perms)
â”‚   â”œâ”€â”€ api/supabase.js  (197)     â† Supabase wrapper
â”‚   â”œâ”€â”€ ui/shell.js      (265)     â† Top bar, nav, modals, toasts
â”‚   â””â”€â”€ ui/styles.css    (400)     â† Dark theme, responsive
â”œâ”€â”€ modules/             (10 feature modules)
â”œâ”€â”€ config/              â† Instance + module config
â”œâ”€â”€ build/build.js       â† Tree-shaking build script
â””â”€â”€ android/             â† Capacitor native build (REVV-Modular-App/)
```

**Total LOC**: ~5,800

---

## What's Built â€” Module Status

### Core System â€” COMPLETE
- [x] Module loader with dependency resolution (Kahn's algorithm)
- [x] PIN authentication (SHA-256, lockout, session timeout)
- [x] 6-tier role system (apprentice â†’ superuser, 57 permissions)
- [x] Supabase client wrapper
- [x] UI shell (top bar, bottom nav, modals, toasts)
- [x] Dark theme, 48px+ touch targets
- [x] PWA manifest + service worker (offline-capable)
- [x] Build script with module tree-shaking

### Feature Modules (10/11 working)

| Module | Role | LOC | Status |
|--------|------|-----|--------|
| Time Clock | Apprentice | 201 | DONE â€” punch in/out, weekly timecard, OT calc, GPS indicator |
| Calculator | Apprentice | 168 | DONE â€” pipe, concrete, material estimator |
| Task List | Apprentice | 137 | DONE â€” kanban board, priority, assignee |
| Messaging | Apprentice | 159 | STUB â€” UI only, no storage/sync |
| Safety | Apprentice | 275 | DONE â€” JSA builder, incidents, checklist, certifications |
| Inventory | Journeyman | 241 | DONE â€” materials, bin locations, checkout/return, low-stock alerts |
| MRO | Journeyman | 217 | DONE â€” equipment tracking, work orders, maintenance schedule |
| Documents | Journeyman | 171 | DONE â€” upload, categorize, version tracking |
| Daily Log | Foreman | 179 | DONE â€” weather, crew, notes, date navigation |
| Reports | Admin | 291 | DONE â€” daily/weekly/timecard/safety/MRO, print-ready |
| Admin Panel | Admin | â€” | NOT BUILT |

---

## Phase 1: Core + Modules â€” 90% COMPLETE
- [x] Auth system (PIN + biometric + lockout)
- [x] Role-based access (6 tiers, 57 permissions)
- [x] Module loader + config system
- [x] 10 feature modules (9 fully working)
- [x] PWA (service worker, manifest, offline)
- [x] Build script
- [~] Messaging module (UI only, needs backend)
- [ ] Admin Panel module

## Phase 2: Backend Integration â€” NOT STARTED
- [ ] Configure Supabase project (create tables from migrations)
- [ ] Enable RLS policies
- [ ] Sync Time Clock punches to Supabase
- [ ] Sync Task List to Supabase
- [ ] Sync Safety reports to Supabase
- [ ] Sync Inventory to Supabase
- [ ] Sync Daily Log to Supabase
- [ ] Real-time subscriptions (live updates across devices)
- [ ] Complete Messaging module (Supabase Realtime channels)

## Phase 3: Android Build â€” NOT STARTED
- [ ] Build APK with Capacitor (`npx cap sync && gradlew assembleDebug`)
- [ ] Test on physical device
- [ ] Generate app icons + splash screens
- [ ] Add native GPS (Capacitor Geolocation plugin)
- [ ] Add native biometrics (Capacitor BiometricAuth plugin)
- [ ] Add photo capture to Daily Log (Capacitor Camera plugin)
- [ ] Signed release build
- [ ] Play Store listing

## Phase 4: Production Hardening â€” NOT STARTED
- [ ] Admin Panel (user CRUD, audit log viewer, settings editor)
- [ ] Conflict resolution (offline edits vs server state)
- [ ] Data export (CSV/PDF from Reports module)
- [ ] Push notifications (shift reminders, task assignments)
- [ ] Multi-company support (instance isolation)
- [ ] CI/CD pipeline (auto-deploy web + build APK)

## Phase 5: Advanced Features â€” FUTURE
- [ ] Crew scheduling / shift calendar
- [ ] Drawing markup (annotate blueprints on-device)
- [ ] QR code scanning for inventory
- [ ] Geofencing (auto clock-in when arriving at job site)
- [ ] Payroll export integration
- [ ] Foreman approval workflows (timecards, safety reports)

---

## Priority â€” What's Next

### High
1. **Messaging module** â€” wire up localStorage storage at minimum, Supabase Realtime ideal
2. **Android APK** â€” first build + device test
3. **Supabase setup** â€” create project, run migrations, configure instance.json

### Medium
4. **Admin Panel** â€” user management is needed before multi-user deployment
5. **Photo capture** â€” Daily Log needs camera integration
6. **Data export** â€” Reports should output CSV/PDF

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
