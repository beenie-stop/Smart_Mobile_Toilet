-- =====================================================================
-- Smart Mobile Toilet Network - schema.sql
-- Run FIRST in Supabase: Dashboard -> SQL Editor -> New query -> paste -> Run
-- =====================================================================
create extension if not exists btree_gist;

-- ---------- profiles (1:1 with auth.users) ----------
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null default '' check (char_length(full_name) <= 120),
  email text,
  phone text check (phone is null or phone ~ '^\+?[0-9]{10,13}$'),
  role text not null default 'customer' check (role in ('customer','operator','admin')),
  created_at timestamptz not null default now()
);

-- New sign-ups ALWAYS become 'customer'. Roles are never taken from client input.
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, email, full_name, phone)
  values (
    new.id, new.email,
    left(coalesce(new.raw_user_meta_data->>'full_name', ''), 120),
    case when new.raw_user_meta_data->>'phone' ~ '^\+?[0-9]{10,13}$'
         then new.raw_user_meta_data->>'phone' end
  );
  return new;
end $$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------- vans ----------
create table if not exists public.vans (
  id uuid primary key default gen_random_uuid(),
  van_name text not null check (char_length(van_name) between 2 and 100),
  service_type text not null check (service_type in ('on_demand','stationed')),
  latitude double precision not null check (latitude between -90 and 90),
  longitude double precision not null check (longitude between -180 and 180),
  address text check (char_length(address) <= 250),
  availability_status text not null default 'available'
    check (availability_status in ('available','busy','unavailable','maintenance')),
  water_capacity numeric not null default 500 check (water_capacity > 0),
  water_level numeric not null default 0 check (water_level >= 0),
  waste_capacity numeric not null default 300 check (waste_capacity > 0),
  waste_level numeric not null default 0 check (waste_level >= 0),
  last_cleaned_at timestamptz,
  operator_id uuid references public.profiles(id) on delete set null,
  operating_hours text not null default '06:00-22:00' check (char_length(operating_hours) <= 20),
  is_demo boolean not null default false,
  created_at timestamptz not null default now(),
  constraint water_within_capacity check (water_level <= water_capacity),
  constraint waste_within_capacity check (waste_level <= waste_capacity)
);
create index if not exists idx_vans_operator on public.vans(operator_id);
create index if not exists idx_vans_status on public.vans(availability_status);
create index if not exists idx_vans_type on public.vans(service_type);

-- ---------- facilities ----------
create table if not exists public.facilities (
  id int generated always as identity primary key,
  name text not null unique,
  description text
);

create table if not exists public.van_facilities (
  id int generated always as identity primary key,
  van_id uuid not null references public.vans(id) on delete cascade,
  facility_id int not null references public.facilities(id) on delete cascade,
  available boolean not null default true,
  unique (van_id, facility_id)
);
create index if not exists idx_van_facilities_van on public.van_facilities(van_id);

-- ---------- bookings ----------
create table if not exists public.bookings (
  id uuid primary key default gen_random_uuid(),
  customer_id uuid not null references public.profiles(id) on delete cascade,
  van_id uuid references public.vans(id) on delete set null,
  booking_type text not null check (booking_type in ('on_demand','stationed')),
  user_latitude double precision check (user_latitude between -90 and 90),
  user_longitude double precision check (user_longitude between -180 and 180),
  requested_at timestamptz not null default now(),
  scheduled_at timestamptz not null default now(),
  duration_minutes int not null default 30 check (duration_minutes between 10 and 120),
  slot_end timestamptz not null default now(),
  status text not null default 'requested'
    check (status in ('requested','accepted','assigned','on_the_way','arrived','completed','cancelled','rejected')),
  notes text check (char_length(notes) <= 500),
  constraint on_demand_needs_location check
    (booking_type = 'stationed' or (user_latitude is not null and user_longitude is not null))
);
create index if not exists idx_bookings_customer on public.bookings(customer_id);
create index if not exists idx_bookings_van on public.bookings(van_id);
create index if not exists idx_bookings_status on public.bookings(status);
create index if not exists idx_bookings_requested on public.bookings(requested_at desc);

-- No two ACTIVE bookings may overlap in time on the same van (race-condition proof).
alter table public.bookings drop constraint if exists bookings_no_overlap;
alter table public.bookings add constraint bookings_no_overlap
  exclude using gist (van_id with =, tstzrange(scheduled_at, slot_end) with &&)
  where (status in ('requested','accepted','assigned','on_the_way','arrived'));

-- Validate + normalise every new booking server-side.
create or replace function public.bookings_before_insert() returns trigger
language plpgsql security definer set search_path = public as $$
declare v public.vans%rowtype;
begin
  select * into v from public.vans where id = new.van_id;
  if not found then raise exception 'Van not found'; end if;
  if v.service_type <> new.booking_type then
    raise exception 'Booking type does not match the van service type';
  end if;
  if v.availability_status in ('unavailable','maintenance')
     or (v.service_type = 'on_demand' and v.availability_status <> 'available') then
    raise exception 'This van is not available';
  end if;
  new.status := 'requested';
  new.requested_at := now();
  if new.booking_type = 'on_demand' then new.scheduled_at := now(); end if;
  if new.scheduled_at < now() - interval '5 minutes' then
    raise exception 'Scheduled time is in the past';
  end if;
  new.slot_end := new.scheduled_at + make_interval(mins => new.duration_minutes);
  return new;
end $$;
drop trigger if exists trg_bookings_before_insert on public.bookings;
create trigger trg_bookings_before_insert before insert on public.bookings
  for each row execute function public.bookings_before_insert();

-- Immutable fields + no changes after a booking is finished.
create or replace function public.bookings_guard_update() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if old.status in ('completed','cancelled','rejected') and new.status <> old.status then
    raise exception 'Finished bookings cannot be changed';
  end if;
  if (new.customer_id, new.van_id, new.booking_type, new.scheduled_at, new.slot_end)
     is distinct from (old.customer_id, old.van_id, old.booking_type, old.scheduled_at, old.slot_end) then
    raise exception 'Booking details cannot be changed';
  end if;
  return new;
end $$;
drop trigger if exists trg_bookings_guard_update on public.bookings;
create trigger trg_bookings_guard_update before update on public.bookings
  for each row execute function public.bookings_guard_update();

-- Keep on-demand van availability in sync with the booking lifecycle.
create or replace function public.bookings_after_update() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.booking_type = 'on_demand' and new.status is distinct from old.status then
    if new.status in ('accepted','assigned','on_the_way','arrived') then
      update public.vans set availability_status = 'busy'
        where id = new.van_id and availability_status = 'available';
    elsif new.status in ('completed','cancelled','rejected') then
      update public.vans set availability_status = 'available'
        where id = new.van_id and availability_status = 'busy';
    end if;
  end if;
  return new;
end $$;
drop trigger if exists trg_bookings_after_update on public.bookings;
create trigger trg_bookings_after_update after update on public.bookings
  for each row execute function public.bookings_after_update();

-- ---------- operations logs ----------
create table if not exists public.cleaning_logs (
  id uuid primary key default gen_random_uuid(),
  van_id uuid not null references public.vans(id) on delete cascade,
  operator_id uuid references public.profiles(id) on delete set null,
  cleaned_at timestamptz not null default now(),
  cleaning_notes text check (char_length(cleaning_notes) <= 500),
  status text not null default 'completed' check (status in ('completed','partial'))
);
create index if not exists idx_cleaning_van on public.cleaning_logs(van_id, cleaned_at desc);

create table if not exists public.maintenance_logs (
  id uuid primary key default gen_random_uuid(),
  van_id uuid not null references public.vans(id) on delete cascade,
  operator_id uuid references public.profiles(id) on delete set null,
  issue text not null check (char_length(issue) between 3 and 500),
  reported_at timestamptz not null default now(),
  resolution_status text not null default 'open' check (resolution_status in ('open','in_progress','resolved'))
);
create index if not exists idx_maintenance_van on public.maintenance_logs(van_id, reported_at desc);

-- ---------- feedback & complaints ----------
create table if not exists public.feedback (
  id uuid primary key default gen_random_uuid(),
  booking_id uuid not null unique references public.bookings(id) on delete cascade,
  customer_id uuid not null references public.profiles(id) on delete cascade,
  rating int not null check (rating between 1 and 5),
  comments text check (char_length(comments) <= 500),
  created_at timestamptz not null default now()
);
create index if not exists idx_feedback_customer on public.feedback(customer_id);

create table if not exists public.complaints (
  id uuid primary key default gen_random_uuid(),
  customer_id uuid not null references public.profiles(id) on delete cascade,
  van_id uuid references public.vans(id) on delete set null,
  complaint_type text not null
    check (complaint_type in ('Cleanliness','Maintenance','Water supply','Safety','Staff behaviour','Other')),
  description text not null check (char_length(description) between 5 and 500),
  status text not null default 'open' check (status in ('open','in_review','resolved')),
  created_at timestamptz not null default now()
);
create index if not exists idx_complaints_customer on public.complaints(customer_id);
create index if not exists idx_complaints_van on public.complaints(van_id);
