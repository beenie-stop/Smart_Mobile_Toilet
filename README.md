# Smart Mobile Toilet Network
*Clean sanitation, wherever you need it.* Streamlit + Supabase MVP for SBI Youth Ideathon 2026.

## Run it in 2 minutes (demo mode, no Supabase needed)
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
On the home page click **Enter as Customer / Van operator / Admin**. Demo mode uses in-memory sample data
(vans labelled `[DEMO]`) and never writes to Supabase. Use the sidebar "Demo role" box to switch roles.

**Judge walkthrough (3 min):** Customer: *Find a Toilet Near Me* -> "Use Hyderabad city centre" -> filter -> request
**[DEMO] Aqua Two** -> switch role to Operator -> Accept -> Assigned -> On the way -> Arrived -> Completed ->
switch to Customer -> My Bookings -> rate it -> switch to Admin -> Overview/Analytics.
Try requesting **Aqua One** to see the overlap-prevention message (it already has a pending request).

## Real mode: Supabase setup
1. Create a project at supabase.com.
2. **SQL Editor -> New query**, paste and run, in this order:
   1. `database/schema.sql`
   2. `database/rls_policies.sql`
   3. `database/seed_demo_data.sql` (Part 1 is required; Part 2 optional demo vans)
3. **Authentication -> Providers -> Email**: for easy demos turn off "Confirm email" (keep it on in production).
4. **Project Settings -> API**: copy the *Project URL* and the **anon / publishable** key.
   **Never** use the `service_role` key. The app refuses to start if it detects one.
5. Local config: copy `.env.example` to `.env` (or `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`) and fill in the two values.
6. `streamlit run app.py`, then create an account via **Create account**.
7. Make yourself admin (SQL Editor): `update public.profiles set role='admin' where email='you@example.com';`
8. Sign in as admin -> **Users** tab -> promote a user to *operator* -> **Vans** tab -> assign them to a van.
   Sign-ups are always customers; roles can only be changed by admins (enforced in the database).

### Test accounts (safe way)
Create three real accounts via the sign-up form (e.g. `admin+test@yourmail.com`, `operator+test@...`, `customer+test@...`),
then promote two of them as in steps 7-8. No passwords are stored in this repo.

## Deploy to Streamlit Community Cloud
1. Push this folder to a GitHub repo (`.env` and `secrets.toml` are git-ignored).
2. share.streamlit.io -> New app -> pick repo, branch, main file `app.py`.
3. **Advanced settings -> Secrets**, paste the contents of `.streamlit/secrets.toml.example` with your values.
4. In Supabase **Authentication -> URL Configuration**, add your `*.streamlit.app` URL as Site URL.

## Security model
- Permissions live in Postgres Row Level Security + triggers (`rls_policies.sql`), not just the UI.
- Customers see only their own bookings/feedback; operators only their assigned vans and related bookings;
  admin role only changeable by an admin. Hiding sidebar links is cosmetic.
- Double-booking is prevented by a Postgres exclusion constraint (race-condition proof) plus app-level checks.
- Only the anon key is used; each browser session has its own authenticated client. All inputs validated in `utils/validation.py`.

## What is simulated / needs real-world integration
- **Demo mode** data (vans, bookings, cleaning logs, tank levels) is sample data. Tank levels in real mode are typed in by operators: **no IoT hardware is connected**.
- **No live GPS or dispatch tracking.** Van location is updated manually; "On the way" is an operator-set status.
- User location is entered manually (or via optional Nominatim geocoding); the app never guesses it.
- No payments, SMS/email notifications, or real-time push (Streamlit refreshes on interaction).
- Production ideas: Supabase Realtime, an IoT gateway writing `water_level`/`waste_level`, a payment gateway, SMS alerts.

## Tests
```bash
cd tests && PYTHONPATH=.. python smoke_test.py && PYTHONPATH=.. python flow_test.py
```
