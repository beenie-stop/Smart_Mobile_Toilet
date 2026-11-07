-- =====================================================================
-- seed_demo_data.sql  (run THIRD)
-- Part 1 (REQUIRED): facility catalogue.
-- Part 2 (OPTIONAL): labelled demo vans (is_demo = true, "[DEMO]" name prefix).
--   Skip Part 2 for a clean production database. Remove later with:
--   delete from public.vans where is_demo;
-- The in-app "Demo mode" does NOT use this file: it runs on in-memory sample
-- data and never writes to Supabase.
-- =====================================================================
insert into public.facilities (name, description) values
  ('Private toilet','Fully enclosed private cubicle'),
  ('Running water','Piped running water supply'),
  ('Handwashing sink','Sink with soap'),
  ('Menstrual hygiene products','Pads available on request'),
  ('Sanitary waste disposal','Sealed sanitary waste bin'),
  ('Proper lighting','Interior and entrance lighting'),
  ('Ventilation','Mechanical or passive ventilation'),
  ('Accessible facility','Wheelchair-accessible cubicle with ramp')
on conflict (name) do nothing;

-- Part 2: demo vans around Hyderabad (change the coordinates for your city)
insert into public.vans (van_name, service_type, latitude, longitude, address, availability_status,
                         water_capacity, water_level, waste_capacity, waste_level, operating_hours, is_demo)
select * from (values
  ('[DEMO] Aqua One','on_demand',17.3950,78.4950,'Demo location - city centre','available',500,420,300,60,'06:00-22:00',true),
  ('[DEMO] Aqua Two','on_demand',17.3700,78.4700,'Demo location - west side','available',500,350,300,90,'06:00-22:00',true),
  ('[DEMO] Highway Stop Unit','stationed',17.4400,78.5300,'Demo location - highway service lane','available',800,700,500,120,'24x7',true),
  ('[DEMO] Campus Gate Unit','stationed',17.3600,78.5100,'Demo location - college main gate','available',800,650,500,100,'07:00-20:00',true)
) as t(van_name, service_type, latitude, longitude, address, availability_status, water_capacity,
       water_level, waste_capacity, waste_level, operating_hours, is_demo)
where not exists (select 1 from public.vans where is_demo);

insert into public.van_facilities (van_id, facility_id, available)
select v.id, f.id, true from public.vans v cross join public.facilities f
where v.is_demo and not exists (select 1 from public.van_facilities x where x.van_id = v.id);
