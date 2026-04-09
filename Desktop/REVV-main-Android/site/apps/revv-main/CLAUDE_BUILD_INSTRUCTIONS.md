# REVV Modular â€” Claude Website Build Instructions

## What This Is
REVV (Construction Hierarchy, Engagement & Resource Platform) is a modular PWA for construction field crews. This zip contains the core architecture â€” auth, roles, module system, API layer, database schema, and build system.

## Instructions for Claude (claude.ai)

Upload this entire zip to Claude and paste the following:

---

**Build the complete visual UI for REVV Modular â€” a construction crew management PWA.**

This zip contains the modular architecture (auth, roles, module loader, Supabase API, build system). Your job is to create the full visual interface.

### Screens to Build:
1. **Login Screen** â€” Username + PIN entry (large buttons for gloved hands), biometric opt-in button, REVV logo, dark theme
2. **Home Dashboard** â€” Welcome card, quick stats (hours today, active tasks, crew online), quick-action buttons for clock in/out, recent activity feed
3. **Time Clock** â€” Big clock in/out button with GPS indicator, current shift timer, timecard history table, overtime calculator
4. **Field Calculator** â€” Pipe calculator (diameter, length, weight), concrete calculator (volume, bags), material estimator
5. **Task Lists** â€” Kanban-style task board, assign to crew members, checklists with checkboxes, completion percentage
6. **Messaging** â€” Chat interface (DM + group), message bubbles, send button, unread badges
7. **Safety** â€” JSA form builder, incident report form, safety checklist with sign-off, certification tracker
8. **Daily Log** â€” Date-based log entry, weather/conditions, crew present, work accomplished, photos placeholder
9. **MRO Tracker** â€” Equipment list with status badges, maintenance schedule, work order form
10. **Crew Management** (foreman+) â€” Crew roster, role assignment, attendance overview
11. **Admin Panel** (superintendent+) â€” User management, system settings, audit log viewer, report generator
12. **Bottom Navigation** â€” 5 icons: Home, Tasks, Clock, Safety, More (hamburger for rest)

### Design Requirements:
- **Dark theme**: --bg-primary:#0a0d14, --bg-secondary:#141820, --bg-card:#1a1f2e, --accent:#f59e0b (amber), --text:#e2e8f0
- **Mobile-first** â€” designed for phone screens (375px), scales up to tablet/desktop
- **Construction-grade UX** â€” big touch targets (min 48px), high contrast, works with dirty/gloved hands
- **Single HTML file** with embedded CSS and JS
- **PWA-ready** â€” viewport meta, standalone display, touch-optimized
- Bottom nav bar fixed, smooth screen transitions
- Cards with 12px radius, subtle glow on focus
- Role-based nav: show/hide screens based on logged-in role
- Include sample data (3 crew members, some tasks, some timecards) so it looks populated
- REVV logo/branding in header, "Powered by REVV" in settings
- 6-tier role hierarchy: apprentice â†’ worker â†’ foreman â†’ general_foreman â†’ superintendent â†’ superuser

### Tech:
- Pure HTML + CSS + JS (no frameworks, no build tools)
- CSS Grid/Flexbox, custom properties
- Smooth transitions, skeleton loading states
- localStorage for session and sample data

Return the complete HTML file.

---

## Reference Source

The `reference-revv-main/` folder contains the current production REVV app (revv.live). 
Use this as your visual reference â€” match its dark theme, color scheme, button styles, 
card layouts, and overall aesthetic. The rebuild should look like the same product, just 
with modern architecture underneath.

Key files to study:
- `reference-revv-main/css/app.css` â€” The complete REVV stylesheet
- `reference-revv-main/index.html` â€” App shell and structure  
- `reference-revv-main/js/nav.js` â€” Navigation pattern
- `reference-revv-main/js/screens/*.js` â€” Each screen's renderer

Replicate the same visual language: dark backgrounds, amber accents, card-based layouts,
bottom navigation bar, mobile-first design. The new version should feel like REVV v2.0,
not a different product.
