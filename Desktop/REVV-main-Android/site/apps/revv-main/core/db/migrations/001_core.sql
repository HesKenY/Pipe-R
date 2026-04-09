-- ============================================
-- CHERP Modular PWA — Core Migration 001
-- Tables: user_profiles, app_settings, audit_log, session_log
-- Includes RLS policies
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- user_profiles
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

-- RLS
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- All authenticated users can read active profiles
CREATE POLICY user_profiles_select ON user_profiles
  FOR SELECT USING (is_active = true);

-- Only admins+ can insert
CREATE POLICY user_profiles_insert ON user_profiles
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role IN ('admin', 'superuser')
    )
  );

-- Users can update their own profile; admins can update any
CREATE POLICY user_profiles_update ON user_profiles
  FOR UPDATE USING (
    id = auth.uid()
    OR EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role IN ('admin', 'superuser')
    )
  );

-- Only superusers can delete
CREATE POLICY user_profiles_delete ON user_profiles
  FOR DELETE USING (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role = 'superuser'
    )
  );

-- ============================================
-- app_settings
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

-- RLS
ALTER TABLE app_settings ENABLE ROW LEVEL SECURITY;

-- Everyone can read settings
CREATE POLICY app_settings_select ON app_settings
  FOR SELECT USING (true);

-- Only superusers can modify settings
CREATE POLICY app_settings_insert ON app_settings
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role = 'superuser'
    )
  );

CREATE POLICY app_settings_update ON app_settings
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role = 'superuser'
    )
  );

CREATE POLICY app_settings_delete ON app_settings
  FOR DELETE USING (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role = 'superuser'
    )
  );

-- ============================================
-- audit_log
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

-- RLS
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Anyone can insert audit entries (for login tracking)
CREATE POLICY audit_log_insert ON audit_log
  FOR INSERT WITH CHECK (true);

-- Users can see their own logs; admins can see all
CREATE POLICY audit_log_select ON audit_log
  FOR SELECT USING (
    user_id = auth.uid()
    OR EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role IN ('admin', 'superuser')
    )
  );

-- No one can update or delete audit logs
CREATE POLICY audit_log_no_update ON audit_log
  FOR UPDATE USING (false);

CREATE POLICY audit_log_no_delete ON audit_log
  FOR DELETE USING (false);

-- ============================================
-- session_log
-- ============================================
CREATE TABLE IF NOT EXISTS session_log (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id       UUID NOT NULL REFERENCES user_profiles(id),
  session_start TIMESTAMPTZ NOT NULL DEFAULT now(),
  session_end   TIMESTAMPTZ,
  auth_method   TEXT NOT NULL DEFAULT 'pin'
                CHECK (auth_method IN ('pin', 'biometric')),
  device_info   JSONB DEFAULT '{}'::jsonb,
  ip_address    INET,
  is_active     BOOLEAN NOT NULL DEFAULT true,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_session_log_user ON session_log (user_id);
CREATE INDEX IF NOT EXISTS idx_session_log_active ON session_log (is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_session_log_start ON session_log (session_start DESC);

-- RLS
ALTER TABLE session_log ENABLE ROW LEVEL SECURITY;

-- Users can insert their own sessions
CREATE POLICY session_log_insert ON session_log
  FOR INSERT WITH CHECK (true);

-- Users see their own sessions; admins see all
CREATE POLICY session_log_select ON session_log
  FOR SELECT USING (
    user_id = auth.uid()
    OR EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role IN ('admin', 'superuser')
    )
  );

-- Users can update their own sessions (to close them)
CREATE POLICY session_log_update ON session_log
  FOR UPDATE USING (
    user_id = auth.uid()
    OR EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role IN ('admin', 'superuser')
    )
  );

-- No deleting session logs
CREATE POLICY session_log_no_delete ON session_log
  FOR DELETE USING (false);

-- ============================================
-- Auto-update updated_at trigger
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_user_profiles_updated
  BEFORE UPDATE ON user_profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_app_settings_updated
  BEFORE UPDATE ON app_settings
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================
-- Seed default settings
-- ============================================
INSERT INTO app_settings (key, value, description) VALUES
  ('app_version', '"1.0.0"'::jsonb, 'Current application version'),
  ('maintenance_mode', 'false'::jsonb, 'Enable to block non-admin access'),
  ('default_role', '"apprentice"'::jsonb, 'Default role for new users')
ON CONFLICT (key) DO NOTHING;
