-- ============================================
-- REVV Main — RLS Fix for Account Creation + Data Access
-- Run this in the Supabase SQL Editor after the base schema
-- ============================================

-- 1. Fix user_profiles: allow anonymous inserts (signup)
DROP POLICY IF EXISTS user_profiles_insert ON user_profiles;
CREATE POLICY user_profiles_insert ON user_profiles
  FOR INSERT WITH CHECK (true);
-- Anyone can create an account. Admins manage via activate/deactivate.

-- 2. Fix user_profiles: allow reading own profile + company profiles
DROP POLICY IF EXISTS user_profiles_select ON user_profiles;
CREATE POLICY user_profiles_select ON user_profiles
  FOR SELECT USING (true);
-- All active profiles visible (needed for login lookup by username)

-- 3. Fix user_profiles: allow self-update
DROP POLICY IF EXISTS user_profiles_update ON user_profiles;
CREATE POLICY user_profiles_update ON user_profiles
  FOR UPDATE USING (true);
-- Temporarily open for anon key usage. Lock down when using Supabase Auth.

-- 4. Fix time_punches: allow insert from anon key
DROP POLICY IF EXISTS time_punches_insert ON time_punches;
CREATE POLICY time_punches_insert ON time_punches
  FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS time_punches_select ON time_punches;
CREATE POLICY time_punches_select ON time_punches
  FOR SELECT USING (true);

DROP POLICY IF EXISTS time_punches_update ON time_punches;
CREATE POLICY time_punches_update ON time_punches
  FOR UPDATE USING (true);

-- 5. Fix tasks: open for anon key
DROP POLICY IF EXISTS tasks_select ON tasks;
DROP POLICY IF EXISTS tasks_insert ON tasks;
DROP POLICY IF EXISTS tasks_update ON tasks;
DROP POLICY IF EXISTS tasks_delete ON tasks;
CREATE POLICY tasks_select ON tasks FOR SELECT USING (true);
CREATE POLICY tasks_insert ON tasks FOR INSERT WITH CHECK (true);
CREATE POLICY tasks_update ON tasks FOR UPDATE USING (true);
CREATE POLICY tasks_delete ON tasks FOR DELETE USING (true);

-- 6. Fix safety_reports: open for anon key
DROP POLICY IF EXISTS safety_select ON safety_reports;
DROP POLICY IF EXISTS safety_insert ON safety_reports;
DROP POLICY IF EXISTS safety_update ON safety_reports;
CREATE POLICY safety_select ON safety_reports FOR SELECT USING (true);
CREATE POLICY safety_insert ON safety_reports FOR INSERT WITH CHECK (true);
CREATE POLICY safety_update ON safety_reports FOR UPDATE USING (true);

-- 7. Fix inventory + inventory_log
DROP POLICY IF EXISTS inventory_select ON inventory;
DROP POLICY IF EXISTS inventory_insert ON inventory;
DROP POLICY IF EXISTS inventory_update ON inventory;
CREATE POLICY inventory_select ON inventory FOR SELECT USING (true);
CREATE POLICY inventory_insert ON inventory FOR INSERT WITH CHECK (true);
CREATE POLICY inventory_update ON inventory FOR UPDATE USING (true);

DROP POLICY IF EXISTS inv_log_select ON inventory_log;
DROP POLICY IF EXISTS inv_log_insert ON inventory_log;
CREATE POLICY inv_log_select ON inventory_log FOR SELECT USING (true);
CREATE POLICY inv_log_insert ON inventory_log FOR INSERT WITH CHECK (true);

-- 8. Fix daily_logs
DROP POLICY IF EXISTS daily_logs_select ON daily_logs;
DROP POLICY IF EXISTS daily_logs_insert ON daily_logs;
DROP POLICY IF EXISTS daily_logs_update ON daily_logs;
CREATE POLICY daily_logs_select ON daily_logs FOR SELECT USING (true);
CREATE POLICY daily_logs_insert ON daily_logs FOR INSERT WITH CHECK (true);
CREATE POLICY daily_logs_update ON daily_logs FOR UPDATE USING (true);

-- 9. Fix messages
DROP POLICY IF EXISTS messages_insert ON messages;
DROP POLICY IF EXISTS messages_select ON messages;
CREATE POLICY messages_select ON messages FOR SELECT USING (true);
CREATE POLICY messages_insert ON messages FOR INSERT WITH CHECK (true);

-- 10. Fix MRO
DROP POLICY IF EXISTS mro_select ON mro_equipment;
DROP POLICY IF EXISTS mro_insert ON mro_equipment;
DROP POLICY IF EXISTS mro_update ON mro_equipment;
CREATE POLICY mro_select ON mro_equipment FOR SELECT USING (true);
CREATE POLICY mro_insert ON mro_equipment FOR INSERT WITH CHECK (true);
CREATE POLICY mro_update ON mro_equipment FOR UPDATE USING (true);

-- 11. Fix work_orders
DROP POLICY IF EXISTS wo_select ON work_orders;
DROP POLICY IF EXISTS wo_insert ON work_orders;
DROP POLICY IF EXISTS wo_update ON work_orders;
CREATE POLICY wo_select ON work_orders FOR SELECT USING (true);
CREATE POLICY wo_insert ON work_orders FOR INSERT WITH CHECK (true);
CREATE POLICY wo_update ON work_orders FOR UPDATE USING (true);

-- 12. Fix audit_log
DROP POLICY IF EXISTS audit_log_insert ON audit_log;
DROP POLICY IF EXISTS audit_log_select ON audit_log;
CREATE POLICY audit_log_insert ON audit_log FOR INSERT WITH CHECK (true);
CREATE POLICY audit_log_select ON audit_log FOR SELECT USING (true);

-- 13. Fix session_log
DROP POLICY IF EXISTS session_log_insert ON session_log;
DROP POLICY IF EXISTS session_log_select ON session_log;
DROP POLICY IF EXISTS session_log_update ON session_log;
CREATE POLICY session_log_insert ON session_log FOR INSERT WITH CHECK (true);
CREATE POLICY session_log_select ON session_log FOR SELECT USING (true);
CREATE POLICY session_log_update ON session_log FOR UPDATE USING (true);

-- Done. All tables now accessible via anon key.
-- Company isolation is enforced at the APPLICATION level via company_id filtering.
-- When Supabase Auth is implemented, lock these down to auth.uid() checks.
