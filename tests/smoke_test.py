import os, sys
sys.path.insert(0, os.getcwd())
from streamlit.testing.v1 import AppTest

def run(role, page):
    at = AppTest.from_file("../app.py", default_timeout=60)
    at.session_state["demo_mode"] = True
    names = {"customer": ("demo-cust-1","Demo Customer A"), "operator": ("demo-op-1","Demo Operator 1"), "admin": ("demo-admin","Demo Admin")}
    at.session_state["user"] = {"id": names[role][0], "email": "x@demo.local", "full_name": names[role][1], "role": role, "demo": True}
    at.run()
    assert not at.exception, ("app", at.exception)
    at.switch_page(page).run()
    return at

def check(at, label):
    errs = [e.value for e in at.exception]
    print(label, "EXC:" if errs else "ok", errs[:1], "| errors:", [e.value for e in at.error][:2])
    return not errs

ok = True
for role, page in [("customer","pages/1_Customer_Dashboard.py"),("customer","pages/3_My_Bookings.py"),("operator","pages/4_Operator_Dashboard.py"),("admin","pages/5_Admin_Dashboard.py")]:
    ok &= check(run(role, page), page)
# find toilet
at = run("customer","pages/2_Find_Toilet.py"); ok &= check(at,"find (no loc)")
at.session_state["loc"] = (17.385, 78.4867, "Demo centre"); at.run(); ok &= check(at,"find (loc)")
print("buttons:", [b.label for b in at.button][:3], "forms:", len(at.get("form")) if hasattr(at,'get') else '')
# landing, logged out
at = AppTest.from_file("../app.py", default_timeout=60).run(); ok &= check(at,"landing")
print("ALL OK" if ok else "FAILURES")
