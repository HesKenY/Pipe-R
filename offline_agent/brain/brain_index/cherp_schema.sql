-- ============================================
-- CHERP Modular — Full Supabase Schema
-- Project: pflprnvmhklomqscwceg
-- Run in Supabase SQL Editor
-- ============================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. user_profiles
-- ============================================
CREATE TABLE IF NOT EXISTS user_profiles (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  username      TEXT UNIQUE NOT NULL,
  display_name  TEXT NOT NULL,
  pin_hash      TEXT NOT NULL,
  role          TEXT NOT NULL DEFAULT 'apprentice'
                CHECK (role IN ('apprentice','journeyman','foreman','superintendent','admin','superuser')),
  is_active     BOOLEAN NOT NULL DEFAULT true,
  company_id    TEXT,
  crew          TEXT,
  trade         TEXT,
  phone         TEXT,
  email         TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_username ON user_profiles (username);
CREATE INDEX IF NOT EXISTS idx_user_profiles_role ON user_profiles (role);
CREATE INDEX IF NOT EXISTS idx_user_profiles_company ON user_profiles (company_id);

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_profiles_select ON user_profiles
  FOR SELECT USING (is_active = true);
CREATE POLICY user_profiles_insert ON user_profiles
  FOR INSERT WITH CHECK (
    EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('admin','superuser'))
  );
CREATE POLICY user_profiles_update ON user_profiles
  FOR UPDATE USING (
    id = auth.uid()
    OR EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('admin','superuser'))
  );
CREATE POLICY user_profiles_delete ON user_profiles
  FOR DELETE USING (
    EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role = 'superuser')
  );

-- ============================================
-- 2. app_settings
-- ============================================
CREATE TABLE IF NOT EXISTS app_settings (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  key           TEXT UNIQUE NOT NULL,
  value         JSONB NOT NULL DEFAULT '{}'::jsonb,
  description   TEXT,
  updated_by    UUID REFERENCES user_profiles(id),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_app_settings_key ON app_settings (key);

ALTER TABLE app_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY app_settings_select ON app_settings FOR SELECT USING (true);
CREATE POLICY app_settings_insert ON app_settings FOR INSERT WITH CHECK (
  EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role = 'superuser')
);
CREATE POLICY app_settings_update ON app_settings FOR UPDATE USING (
  EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role = 'superuser')
);
CREATE POLICY app_settings_delete ON app_settings FOR DELETE USING (
  EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role = 'superuser')
);

-- ============================================
-- 3. audit_log
-- ============================================
CREATE TABLE IF NOT EXISTS audit_log (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id       UUID REFERENCES user_profiles(id),
  action        TEXT NOT NULL,
  module        TEXT,
  details       JSONB DEFAULT '{}'::jsonb,
  ip_address    INET,
  user_agent    TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log (action);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_module ON audit_log (module);

ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY audit_log_insert ON audit_log FOR INSERT WITH CHECK (true);
CREATE POLICY audit_log_select ON audit_log FOR SELECT USING (
  user_id = auth.uid()
  OR EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('admin','superuser'))
);
CREATE POLICY audit_log_no_update ON audit_log FOR UPDATE USING (false);
CREATE POLICY audit_log_no_delete ON audit_log FOR DELETE USING (false);

-- ============================================
-- 4. session_log
-- ============================================
CREATE TABLE IF NOT EXISTS session_log (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id       UUID NOT NULL REFERENCES user_profiles(id),
  session_start TIMESTAMPTZ NOT NULL DEFAULT now(),
  session_end   TIMESTAMPTZ,
  auth_method   TEXT NOT NULL DEFAULT 'pin'
                CHECK (auth_method IN ('pin','biometric')),
  device_info   JSONB DEFAULT '{}'::jsonb,
  ip_address    INET,
  is_active     BOOLEAN NOT NULL DEFAULT true,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_session_log_user ON session_log (user_id);
CREATE INDEX IF NOT EXISTS idx_session_log_active ON session_log (is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_session_log_start ON session_log (session_start DESC);

ALTER TABLE session_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY session_log_insert ON session_log FOR INSERT WITH CHECK (true);
CREATE POLICY session_log_select ON session_log FOR SELECT USING (
  user_id = auth.uid()
  OR EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('admin','superuser'))
);
CREATE POLICY session_log_update ON session_log FOR UPDATE USING (
  user_id = auth.uid()
  OR EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('admin','superuser'))
);
CREATE POLICY session_log_no_delete ON session_log FOR DELETE USING (false);

-- ============================================
-- 5. time_punches
-- ============================================
CREATE TABLE IF NOT EXISTS time_punches (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id       UUID NOT NULL REFERENCES user_profiles(id),
  punch_type    TEXT NOT NULL CHECK (punch_type IN ('in','out')),
  timestamp     TIMESTAMPTZ NOT NULL DEFAULT now(),
  gps_lat       DOUBLE PRECISION,
  gps_lng       DOUBLE PRECISION,
  gps_accuracy  DOUBLE PRECISION,
  selfie_url    TEXT,
  notes         TEXT,
  company_id    TEXT,
  approved_by   UUID REFERENCES user_profiles(id),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_time_punches_user ON time_punches (user_id);
CREATE INDEX IF NOT EXISTS idx_time_punches_ts ON time_punches (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_time_punches_company ON time_punches (company_id);

ALTER TABLE time_punches ENABLE ROW LEVEL SECURITY;

CREATE POLICY time_punches_insert ON time_punches FOR INSERT WITH CHECK (true);
CREATE POLICY time_punches_select ON time_punches FOR SELECT USING (
  user_id = auth.uid()
  OR EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('foreman','superintendent','admin','superuser'))
);
CREATE POLICY time_punches_update ON time_punches FOR UPDATE USING (
  EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('foreman','superintendent','admin','superuser'))
);

-- ============================================
-- 6. tasks
-- ============================================
CREATE TABLE IF NOT EXISTS tasks (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  title         TEXT NOT NULL,
  description   TEXT,
  status        TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo','in_progress','done')),
  priority      TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low','medium','high','urgent')),
  assigned_to   UUID REFERENCES user_profiles(id),
  created_by    UUID REFERENCES user_profiles(id),
  company_id    TEXT,
  due_date      DATE,
  progress      INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks (assigned_to);
CREATE INDEX IF NOT EXISTS idx_tasks_company ON tasks (company_id);

ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY tasks_select ON tasks FOR SELECT USING (true);
CREATE POLICY tasks_insert ON tasks FOR INSERT WITH CHECK (true);
CREATE POLICY tasks_update ON tasks FOR UPDATE USING (
  assigned_to = auth.uid()
  OR created_by = auth.uid()
  OR EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('foreman','superintendent','admin','superuser'))
);
CREATE POLICY tasks_delete ON tasks FOR DELETE USING (
  created_by = auth.uid()
  OR EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('admin','superuser'))
);

-- ============================================
-- 7. safety_reports (JSA, incidents, checklists)
-- ============================================
CREATE TABLE IF NOT EXISTS safety_reports (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  report_type   TEXT NOT NULL CHECK (report_type IN ('jsa','incident','checklist','certification')),
  title         TEXT NOT NULL,
  severity      TEXT CHECK (severity IN ('low','medium','high','critical')),
  status        TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','in_progress','closed')),
  reported_by   UUID REFERENCES user_profiles(id),
  assigned_to   UUID REFERENCES user_profiles(id),
  company_id    TEXT,
  data          JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_safety_type ON safety_reports (report_type);
CREATE INDEX IF NOT EXISTS idx_safety_company ON safety_reports (company_id);
CREATE INDEX IF NOT EXISTS idx_safety_status ON safety_reports (status);

ALTER TABLE safety_reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY safety_select ON safety_reports FOR SELECT USING (true);
CREATE POLICY safety_insert ON safety_reports FOR INSERT WITH CHECK (true);
CREATE POLICY safety_update ON safety_reports FOR UPDATE USING (
  reported_by = auth.uid()
  OR EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('foreman','superintendent','admin','superuser'))
);

-- ============================================
-- 8. inventory
-- ============================================
CREATE TABLE IF NOT EXISTS inventory (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name          TEXT NOT NULL,
  quantity      DOUBLE PRECISION NOT NULL DEFAULT 0,
  unit          TEXT NOT NULL DEFAULT 'each' CHECK (unit IN ('each','ft','lbs','gallons','boxes','rolls','bags','sheets','bundles','pairs')),
  bin_location  TEXT,
  reorder_point DOUBLE PRECISION DEFAULT 0,
  company_id    TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_inventory_company ON inventory (company_id);
CREATE INDEX IF NOT EXISTS idx_inventory_name ON inventory (name);

ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;

CREATE POLICY inventory_select ON inventory FOR SELECT USING (true);
CREATE POLICY inventory_insert ON inventory FOR INSERT WITH CHECK (
  EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('journeyman','foreman','superintendent','admin','superuser'))
);
CREATE POLICY inventory_update ON inventory FOR UPDATE USING (
  EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('journeyman','foreman','superintendent','admin','superuser'))
);

-- ============================================
-- 9. inventory_log (checkout/return tracking)
-- ============================================
CREATE TABLE IF NOT EXISTS inventory_log (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  inventory_id  UUID NOT NULL REFERENCES inventory(id),
  user_id       UUID NOT NULL REFERENCES user_profiles(id),
  action        TEXT NOT NULL CHECK (action IN ('checkout','return','adjust','restock')),
  quantity      DOUBLE PRECISION NOT NULL,
  notes         TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_inv_log_item ON inventory_log (inventory_id);
CREATE INDEX IF NOT EXISTS idx_inv_log_user ON inventory_log (user_id);

ALTER TABLE inventory_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY inv_log_select ON inventory_log FOR SELECT USING (true);
CREATE POLICY inv_log_insert ON inventory_log FOR INSERT WITH CHECK (true);

-- ============================================
-- 10. daily_logs
-- ============================================
CREATE TABLE IF NOT EXISTS daily_logs (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  log_date      DATE NOT NULL,
  weather       TEXT,
  crew_present  JSONB DEFAULT '[]'::jsonb,
  work_done     TEXT,
  notes         TEXT,
  created_by    UUID REFERENCES user_profiles(id),
  company_id    TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_daily_logs_date ON daily_logs (log_date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_logs_company ON daily_logs (company_id);

ALTER TABLE daily_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY daily_logs_select ON daily_logs FOR SELECT USING (true);
CREATE POLICY daily_logs_insert ON daily_logs FOR INSERT WITH CHECK (
  EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('foreman','superintendent','admin','superuser'))
);
CREATE POLICY daily_logs_update ON daily_logs FOR UPDATE USING (
  created_by = auth.uid()
  OR EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('admin','superuser'))
);

-- ============================================
-- 11. messages
-- ============================================
CREATE TABLE IF NOT EXISTS messages (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  sender_id     UUID NOT NULL REFERENCES user_profiles(id),
  recipient_id  UUID REFERENCES user_profiles(id),
  channel       TEXT,
  body          TEXT NOT NULL,
  is_read       BOOLEAN NOT NULL DEFAULT false,
  company_id    TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages (sender_id);
CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages (recipient_id);
CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages (channel);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages (created_at DESC);

ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY messages_insert ON messages FOR INSERT WITH CHECK (true);
CREATE POLICY messages_select ON messages FOR SELECT USING (
  sender_id = auth.uid()
  OR recipient_id = auth.uid()
  OR channel IS NOT NULL
);

-- ============================================
-- 12. mro_equipment
-- ============================================
CREATE TABLE IF NOT EXISTS mro_equipment (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name          TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'operational' CHECK (status IN ('operational','maintenance','out_of_service')),
  location      TEXT,
  company_id    TEXT,
  last_service  DATE,
  next_service  DATE,
  notes         TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE mro_equipment ENABLE ROW LEVEL SECURITY;
CREATE POLICY mro_select ON mro_equipment FOR SELECT USING (true);
CREATE POLICY mro_insert ON mro_equipment FOR INSERT WITH CHECK (
  EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('journeyman','foreman','superintendent','admin','superuser'))
);
CREATE POLICY mro_update ON mro_equipment FOR UPDATE USING (
  EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('journeyman','foreman','superintendent','admin','superuser'))
);

-- ============================================
-- 13. work_orders
-- ============================================
CREATE TABLE IF NOT EXISTS work_orders (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  equipment_id  UUID REFERENCES mro_equipment(id),
  title         TEXT NOT NULL,
  description   TEXT,
  status        TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','in_progress','completed','cancelled')),
  priority      TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low','medium','high','urgent')),
  assigned_to   UUID REFERENCES user_profiles(id),
  created_by    UUID REFERENCES user_profiles(id),
  cost          DOUBLE PRECISION DEFAULT 0,
  company_id    TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE work_orders ENABLE ROW LEVEL SECURITY;
CREATE POLICY wo_select ON work_orders FOR SELECT USING (true);
CREATE POLICY wo_insert ON work_orders FOR INSERT WITH CHECK (true);
CREATE POLICY wo_update ON work_orders FOR UPDATE USING (
  assigned_to = auth.uid()
  OR created_by = auth.uid()
  OR EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('foreman','superintendent','admin','superuser'))
);

-- ============================================
-- Triggers: auto-update updated_at
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_user_profiles_updated BEFORE UPDATE ON user_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_app_settings_updated BEFORE UPDATE ON app_settings FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_tasks_updated BEFORE UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_safety_updated BEFORE UPDATE ON safety_reports FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_inventory_updated BEFORE UPDATE ON inventory FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_daily_logs_updated BEFORE UPDATE ON daily_logs FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_mro_updated BEFORE UPDATE ON mro_equipment FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_work_orders_updated BEFORE UPDATE ON work_orders FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================
-- Seed: default settings + demo user
-- ============================================
INSERT INTO app_settings (key, value, description) VALUES
  ('app_version', '"1.0.0"'::jsonb, 'Current application version'),
  ('maintenance_mode', 'false'::jsonb, 'Enable to block non-admin access'),
  ('default_role', '"apprentice"'::jsonb, 'Default role for new users')
ON CONFLICT (key) DO NOTHING;

-- Demo superuser (PIN: 1234 → SHA-256 hash)
INSERT INTO user_profiles (username, display_name, pin_hash, role, company_id, crew, trade) VALUES
  ('demo', 'Demo Superuser', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'superuser', 'DEMO-001', 'Alpha', 'Plumbing')
ON CONFLICT (username) DO NOTHING;
-- ============================================
-- CHERP — Crew Management Tables
-- Run in Supabase SQL Editor for project: pflprnvmhklomqscwceg
-- ============================================

-- Team/crew definitions
CREATE TABLE IF NOT EXISTS team_codes (
  code           TEXT PRIMARY KEY,
  crew_name      TEXT NOT NULL,
  foreman_name   TEXT,
  foreman_id     UUID,
  foreman_phone  TEXT,
  company_name   TEXT DEFAULT 'CHERP',
  job_site       TEXT,
  notes          TEXT,
  sb_url         TEXT,
  sb_key         TEXT,
  active         BOOLEAN DEFAULT true,
  created_at     TIMESTAMPTZ DEFAULT now(),
  updated_at     TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE team_codes ENABLE ROW LEVEL SECURITY;
CREATE POLICY team_codes_select ON team_codes FOR SELECT USING (true);
CREATE POLICY team_codes_insert ON team_codes FOR INSERT WITH CHECK (true);
CREATE POLICY team_codes_update ON team_codes FOR UPDATE USING (true);
CREATE POLICY team_codes_delete ON team_codes FOR DELETE USING (true);

-- Crew membership (who is on which crew)
CREATE TABLE IF NOT EXISTS crew_members (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  team_code     TEXT REFERENCES team_codes(code) ON DELETE CASCADE,
  member_name   TEXT NOT NULL,
  device_id     TEXT,
  role          TEXT DEFAULT 'Worker',
  is_foreman    BOOLEAN DEFAULT false,
  last_seen     TIMESTAMPTZ DEFAULT now(),
  created_at    TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT crew_members_unique_device UNIQUE (team_code, device_id)
);

CREATE INDEX IF NOT EXISTS idx_crew_members_team ON crew_members (team_code);
CREATE INDEX IF NOT EXISTS idx_crew_members_name ON crew_members (member_name);

ALTER TABLE crew_members ENABLE ROW LEVEL SECURITY;
CREATE POLICY crew_members_select ON crew_members FOR SELECT USING (true);
CREATE POLICY crew_members_insert ON crew_members FOR INSERT WITH CHECK (true);
CREATE POLICY crew_members_update ON crew_members FOR UPDATE USING (true);
CREATE POLICY crew_members_delete ON crew_members FOR DELETE USING (true);

-- Crew-level tasks
CREATE TABLE IF NOT EXISTS crew_tasks (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  team_code     TEXT REFERENCES team_codes(code) ON DELETE CASCADE,
  text          TEXT NOT NULL,
  priority      TEXT DEFAULT 'normal',
  assigned_to   TEXT,
  done          BOOLEAN DEFAULT false,
  done_at       TIMESTAMPTZ,
  progress      INTEGER DEFAULT 0 CHECK (progress IS NULL OR (progress >= 0 AND progress <= 100)),
  work_type     TEXT DEFAULT 'work',
  photo_b64     TEXT,
  due_date      DATE,
  notes         TEXT,
  created_by    TEXT,
  created_at    TIMESTAMPTZ DEFAULT now(),
  updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_crew_tasks_team ON crew_tasks (team_code);
CREATE INDEX IF NOT EXISTS idx_crew_tasks_done ON crew_tasks (done);
CREATE INDEX IF NOT EXISTS idx_crew_tasks_work_type ON crew_tasks (team_code, work_type);

ALTER TABLE crew_tasks ENABLE ROW LEVEL SECURITY;
CREATE POLICY crew_tasks_select ON crew_tasks FOR SELECT USING (true);
CREATE POLICY crew_tasks_insert ON crew_tasks FOR INSERT WITH CHECK (true);
CREATE POLICY crew_tasks_update ON crew_tasks FOR UPDATE USING (true);
CREATE POLICY crew_tasks_delete ON crew_tasks FOR DELETE USING (true);

-- Crew timecards (clock in/out with GPS + selfie)
-- Not to be confused with the older `time_punches` table above — this is
-- the one the live app actually writes to via timeclock.js.
CREATE TABLE IF NOT EXISTS crew_timecards (
  id            TEXT PRIMARY KEY,
  user_id       TEXT NOT NULL,
  user_name     TEXT,
  team_code     TEXT REFERENCES team_codes(code) ON DELETE SET NULL,
  role          TEXT,
  clock_in      TIMESTAMPTZ NOT NULL,
  clock_out     TIMESTAMPTZ,
  hours         NUMERIC(6,4),
  date          DATE,
  status        TEXT DEFAULT 'active',
  notes         TEXT,
  photo_in      TEXT,
  photo_out     TEXT,
  location_in   TEXT,
  location_out  TEXT,
  created_at    TIMESTAMPTZ DEFAULT now(),
  updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_crew_timecards_user   ON crew_timecards (user_id);
CREATE INDEX IF NOT EXISTS idx_crew_timecards_team   ON crew_timecards (team_code);
CREATE INDEX IF NOT EXISTS idx_crew_timecards_date   ON crew_timecards (date);
CREATE INDEX IF NOT EXISTS idx_crew_timecards_status ON crew_timecards (status);

ALTER TABLE crew_timecards ENABLE ROW LEVEL SECURITY;
CREATE POLICY crew_timecards_select ON crew_timecards FOR SELECT USING (true);
CREATE POLICY crew_timecards_insert ON crew_timecards FOR INSERT WITH CHECK (true);
CREATE POLICY crew_timecards_update ON crew_timecards FOR UPDATE USING (true);
CREATE POLICY crew_timecards_delete ON crew_timecards FOR DELETE USING (true);

-- ============================================
-- Additional tables (patch 2026-04-10)
-- ============================================

-- JSA (Job Safety Analysis) reports
CREATE TABLE IF NOT EXISTS jsa_reports (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  team_code     TEXT REFERENCES team_codes(code) ON DELETE SET NULL,
  created_by    TEXT,
  job_site      TEXT,
  task_desc     TEXT,
  hazards       TEXT,
  controls      TEXT,
  ppe           TEXT,
  workers       TEXT,
  status        TEXT DEFAULT 'open',
  signed_by     TEXT,
  signed_at     TIMESTAMPTZ,
  created_at    TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE jsa_reports ENABLE ROW LEVEL SECURITY;
CREATE POLICY jsa_reports_select ON jsa_reports FOR SELECT USING (true);
CREATE POLICY jsa_reports_insert ON jsa_reports FOR INSERT WITH CHECK (true);
CREATE POLICY jsa_reports_update ON jsa_reports FOR UPDATE USING (true);
CREATE POLICY jsa_reports_delete ON jsa_reports FOR DELETE USING (true);

-- Change orders
CREATE TABLE IF NOT EXISTS change_orders (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  team_code     TEXT,
  title         TEXT NOT NULL,
  description   TEXT,
  status        TEXT DEFAULT 'pending',
  cost_impact   NUMERIC(10,2),
  submitted_by  TEXT,
  approved_by   TEXT,
  created_at    TIMESTAMPTZ DEFAULT now(),
  updated_at    TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE change_orders ENABLE ROW LEVEL SECURITY;
CREATE POLICY change_orders_select ON change_orders FOR SELECT USING (true);
CREATE POLICY change_orders_insert ON change_orders FOR INSERT WITH CHECK (true);
CREATE POLICY change_orders_update ON change_orders FOR UPDATE USING (true);
CREATE POLICY change_orders_delete ON change_orders FOR DELETE USING (true);

-- Certifications
CREATE TABLE IF NOT EXISTS certifications (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id       TEXT,
  user_name     TEXT,
  cert_name     TEXT NOT NULL,
  cert_type     TEXT,
  issuer        TEXT,
  issued_date   DATE,
  expiry_date   DATE,
  status        TEXT DEFAULT 'active',
  notes         TEXT,
  created_at    TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE certifications ENABLE ROW LEVEL SECURITY;
CREATE POLICY certifications_select ON certifications FOR SELECT USING (true);
CREATE POLICY certifications_insert ON certifications FOR INSERT WITH CHECK (true);
CREATE POLICY certifications_update ON certifications FOR UPDATE USING (true);
CREATE POLICY certifications_delete ON certifications FOR DELETE USING (true);

-- Payroll entries
CREATE TABLE IF NOT EXISTS payroll_entries (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id       TEXT,
  user_name     TEXT,
  team_code     TEXT,
  period_start  DATE,
  period_end    DATE,
  hours_regular NUMERIC(6,2) DEFAULT 0,
  hours_ot      NUMERIC(6,2) DEFAULT 0,
  rate          NUMERIC(8,2),
  total         NUMERIC(10,2),
  status        TEXT DEFAULT 'draft',
  approved_by   TEXT,
  created_at    TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE payroll_entries ENABLE ROW LEVEL SECURITY;
CREATE POLICY payroll_entries_select ON payroll_entries FOR SELECT USING (true);
CREATE POLICY payroll_entries_insert ON payroll_entries FOR INSERT WITH CHECK (true);
CREATE POLICY payroll_entries_update ON payroll_entries FOR UPDATE USING (true);
CREATE POLICY payroll_entries_delete ON payroll_entries FOR DELETE USING (true);

-- Contacts
CREATE TABLE IF NOT EXISTS contacts (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  owner_id      TEXT,
  name          TEXT NOT NULL,
  role          TEXT,
  company       TEXT,
  phone         TEXT,
  email         TEXT,
  notes         TEXT,
  created_at    TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
CREATE POLICY contacts_select ON contacts FOR SELECT USING (true);
CREATE POLICY contacts_insert ON contacts FOR INSERT WITH CHECK (true);
CREATE POLICY contacts_update ON contacts FOR UPDATE USING (true);
CREATE POLICY contacts_delete ON contacts FOR DELETE USING (true);

-- ============================================
-- Seed data for testing
-- ============================================

INSERT INTO team_codes (code, crew_name, foreman_name, company_name, job_site, notes)
VALUES ('ALPHA-01', 'Alpha Crew', 'Ken Deibel', 'CHERP', 'Test Site', 'Test crew for development')
ON CONFLICT (code) DO NOTHING;

-- Seed superintendents only. Superusers oversee all crews and are never
-- members of one — do NOT seed them into crew_members.
INSERT INTO crew_members (team_code, member_name, role, is_foreman)
VALUES
  ('ALPHA-01', 'S. Bedard', 'Superintendent', false),
  ('ALPHA-01', 'C. Deibel', 'Superintendent', false)
ON CONFLICT DO NOTHING;

INSERT INTO crew_tasks (team_code, text, priority, created_by)
VALUES ('ALPHA-01', 'Test task — verify crew management is working', 'normal', 'Ken Deibel')
ON CONFLICT DO NOTHING;
