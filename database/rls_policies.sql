-- =====================================================================
-- Smart Mobile Toilet Network - rls_policies.sql
-- Run SECOND (after schema.sql) in the Supabase SQL Editor.
-- Permissions are enforced HERE, in the database, not just in the UI.
-- =====================================================================

-- ---------- helper functions (SECURITY DEFINER avoids RLS recursion) ----------
create or replace function public.is_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce((select role = 'admin' from public.profiles where id = auth.uid()), false)
$$;

create or replace function public.current_role_name() returns text
language sql stable security definer set search_path = public as $$
  select role from public.profiles where id = auth.uid()
$$;

create or replace function public.is_van_operator(v uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.vans where id = v and operator_id = auth.uid())
$$;

-- ---------- guard triggers (column-level rules RLS cannot express) ----------
-- auth.uid() is NULL in the SQL editor, which is how you bootstrap the first admin.
create or replace function public.profiles_guard() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.role is distinct from old.role and auth.uid() is not null and not public.is_admin() then
    raise exception 'Only admins can change roles';
  end if;
  if new.id is distinct from old.id then raise exception 'id is immutable'; end if;
  return new;
end $$;
drop trigger if exists trg_profiles_guard on public.profiles;
create trigger trg_profiles_guard before update on public.profiles
  for each row execute function public.profiles_guard();

create or replace function public.vans_guard() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.operator_id is not null
     and not exists (select 1 from public.profiles where id = new.operator_id and role = 'operator') then
    raise exception 'operator_id must reference a profile with the operator role';
  end if;
  if tg_op = 'UPDATE' and auth.uid() is not null and not public.is_admin() then
    if (new.van_name, new.service_type, new.operator_id, new.water_capacity, new.waste_capacity, new.is_demo)
       is distinct from
       (old.van_name, old.service_type, old.operator_id, old.water_capacity, old.waste_capacity, old.is_demo) then
      raise exception 'Operators cannot change name, type, assignment or tank capacity';
    end if;
  end if;
  return new;
end $$;
drop trigger if exists trg_vans_guard on public.vans;
create trigger trg_vans_guard before insert or update on public.vans
  for each row execute function public.vans_guard();

-- ---------- enable RLS + lock out anonymous users ----------
alter table public.profiles enable row level security;
alter table public.vans enable row level security;
alter table public.facilities enable row level security;
alter table public.van_facilities enable row level security;
alter table public.bookings enable row level security;
alter table public.cleaning_logs enable row level security;
alter table public.maintenance_logs enable row level security;
alter table public.feedback enable row level security;
alter table public.complaints enable row level security;

revoke all on all tables in schema public from anon;
grant select, insert, update, delete on all tables in schema public to authenticated;
grant usage, select on all sequences in schema public to authenticated;

-- ---------- profiles ----------
drop policy if exists profiles_select on public.profiles;
create policy profiles_select on public.profiles for select to authenticated using (
  id = auth.uid() or public.is_admin()
  or exists (select 1 from public.bookings b join public.vans v on v.id = b.van_id
             where b.customer_id = profiles.id and v.operator_id = auth.uid())
);
drop policy if exists profiles_update_own on public.profiles;
create policy profiles_update_own on public.profiles for update to authenticated
  using (id = auth.uid()) with check (id = auth.uid());
drop policy if exists profiles_admin_all on public.profiles;
create policy profiles_admin_all on public.profiles for all to authenticated
  using (public.is_admin()) with check (public.is_admin());

-- ---------- vans ----------
drop policy if exists vans_select on public.vans;
create policy vans_select on public.vans for select to authenticated using (true);
drop policy if exists vans_admin_write on public.vans;
create policy vans_admin_write on public.vans for all to authenticated
  using (public.is_admin()) with check (public.is_admin());
drop policy if exists vans_operator_update on public.vans;
create policy vans_operator_update on public.vans for update to authenticated
  using (operator_id = auth.uid()) with check (operator_id = auth.uid());

-- ---------- facilities ----------
drop policy if exists facilities_select on public.facilities;
create policy facilities_select on public.facilities for select to authenticated using (true);
drop policy if exists facilities_admin on public.facilities;
create policy facilities_admin on public.facilities for all to authenticated
  using (public.is_admin()) with check (public.is_admin());
drop policy if exists van_facilities_select on public.van_facilities;
create policy van_facilities_select on public.van_facilities for select to authenticated using (true);
drop policy if exists van_facilities_admin on public.van_facilities;
create policy van_facilities_admin on public.van_facilities for all to authenticated
  using (public.is_admin()) with check (public.is_admin());

-- ---------- bookings ----------
drop policy if exists bookings_select on public.bookings;
create policy bookings_select on public.bookings for select to authenticated using (
  customer_id = auth.uid() or public.is_admin() or public.is_van_operator(van_id)
);
drop policy if exists bookings_customer_insert on public.bookings;
create policy bookings_customer_insert on public.bookings for insert to authenticated
  with check (customer_id = auth.uid() and public.current_role_name() = 'customer');
drop policy if exists bookings_customer_cancel on public.bookings;
create policy bookings_customer_cancel on public.bookings for update to authenticated
  using (customer_id = auth.uid() and status in ('requested','accepted'))
  with check (customer_id = auth.uid() and status = 'cancelled');
drop policy if exists bookings_operator_update on public.bookings;
create policy bookings_operator_update on public.bookings for update to authenticated
  using (public.is_van_operator(van_id)) with check (public.is_van_operator(van_id));
drop policy if exists bookings_admin_all on public.bookings;
create policy bookings_admin_all on public.bookings for all to authenticated
  using (public.is_admin()) with check (public.is_admin());

-- ---------- cleaning & maintenance logs ----------
drop policy if exists cleaning_select on public.cleaning_logs;
create policy cleaning_select on public.cleaning_logs for select to authenticated
  using (public.is_admin() or public.is_van_operator(van_id));
drop policy if exists cleaning_insert on public.cleaning_logs;
create policy cleaning_insert on public.cleaning_logs for insert to authenticated
  with check (public.is_admin() or (operator_id = auth.uid() and public.is_van_operator(van_id)));
drop policy if exists cleaning_admin on public.cleaning_logs;
create policy cleaning_admin on public.cleaning_logs for all to authenticated
  using (public.is_admin()) with check (public.is_admin());

drop policy if exists maint_select on public.maintenance_logs;
create policy maint_select on public.maintenance_logs for select to authenticated
  using (public.is_admin() or public.is_van_operator(van_id));
drop policy if exists maint_insert on public.maintenance_logs;
create policy maint_insert on public.maintenance_logs for insert to authenticated
  with check (public.is_admin() or (operator_id = auth.uid() and public.is_van_operator(van_id)));
drop policy if exists maint_update on public.maintenance_logs;
create policy maint_update on public.maintenance_logs for update to authenticated
  using (public.is_admin() or public.is_van_operator(van_id))
  with check (public.is_admin() or public.is_van_operator(van_id));
drop policy if exists maint_delete on public.maintenance_logs;
create policy maint_delete on public.maintenance_logs for delete to authenticated using (public.is_admin());

-- ---------- feedback ----------
drop policy if exists feedback_select on public.feedback;
create policy feedback_select on public.feedback for select to authenticated using (
  customer_id = auth.uid() or public.is_admin()
  or exists (select 1 from public.bookings b where b.id = feedback.booking_id and public.is_van_operator(b.van_id))
);
drop policy if exists feedback_insert on public.feedback;
create policy feedback_insert on public.feedback for insert to authenticated with check (
  customer_id = auth.uid()
  and exists (select 1 from public.bookings b
              where b.id = booking_id and b.customer_id = auth.uid() and b.status = 'completed')
);
drop policy if exists feedback_admin_delete on public.feedback;
create policy feedback_admin_delete on public.feedback for delete to authenticated using (public.is_admin());

-- ---------- complaints ----------
drop policy if exists complaints_select on public.complaints;
create policy complaints_select on public.complaints for select to authenticated
  using (customer_id = auth.uid() or public.is_admin() or public.is_van_operator(van_id));
drop policy if exists complaints_insert on public.complaints;
create policy complaints_insert on public.complaints for insert to authenticated
  with check (customer_id = auth.uid() and status = 'open');
drop policy if exists complaints_admin on public.complaints;
create policy complaints_admin on public.complaints for all to authenticated
  using (public.is_admin()) with check (public.is_admin());

-- =====================================================================
-- FIRST ADMIN: sign up in the app, then run this in the SQL editor:
--   update public.profiles set role = 'admin' where email = 'you@example.com';
-- OPERATORS: promote a user from Admin Dashboard -> Users, then assign a van.
-- =====================================================================
