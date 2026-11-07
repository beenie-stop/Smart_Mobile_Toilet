import os, sys
sys.path.insert(0, os.getcwd())
from streamlit.testing.v1 import AppTest
SCRIPT = '''
import streamlit as st
from services import auth_service, booking_service, van_service, repo
import config
auth_service.start_demo("customer"); cust = st.session_state["user"]
out = []
vans = van_service.list_vans(); v2 = vans[vans.van_name=="[DEMO] Aqua Two"].iloc[0]; v1 = vans[vans.van_name=="[DEMO] Aqua One"].iloc[0]
ok,msg = booking_service.create_booking(cust, v1["id"], "on_demand", 17.39, 78.49); out.append(("conflict w/ existing request (expect False)", ok, msg))
ok,msg = booking_service.create_booking(cust, v2["id"], "on_demand", 17.39, 78.49); out.append(("book Aqua Two (True)", ok, msg))
ok,msg = booking_service.create_booking(cust, v2["id"], "on_demand", 17.39, 78.49); out.append(("double book same van (False)", ok, msg))
bk = booking_service.list_bookings(cust); b = bk[(bk.van_id==v2["id"]) & (bk.status=="requested")].iloc[0]
op2 = {"id":"demo-op-2","role":"operator"}; op1 = {"id":"demo-op-1","role":"operator"}
ok,msg = booking_service.update_status(op1, b["id"], "accepted"); out.append(("wrong operator (False)", ok, msg))
for s in ["accepted","assigned","on_the_way","arrived","completed"]:
    ok,msg = booking_service.update_status(op2, b["id"], s); out.append((s, ok, msg))
    if s=="accepted": out.append(("van status", repo.select("vans",eq={"id":v2["id"]})[0]["availability_status"], ""))
out.append(("van after completed", repo.select("vans",eq={"id":v2["id"]})[0]["availability_status"], ""))
out.append(("skip step (False)", *booking_service.update_status(op2, b["id"], "requested")))
out.append(("feedback", *booking_service.submit_feedback(cust, b["id"], 5, "great")))
out.append(("feedback twice (False)", *booking_service.submit_feedback(cust, b["id"], 4, "")))
out.append(("bad rating (False)", *booking_service.submit_feedback(cust, b["id"], 9, "")))
out.append(("complaint", *booking_service.submit_complaint(cust, v2["id"], "Cleanliness", "Needs more soap")))
out.append(("bad coords (False)", *booking_service.create_booking(cust, vans[vans.van_name=="[DEMO] Aqua Three"].iloc[0]["id"], "on_demand", 999, 0)))
out.append(("maintenance van (False)", *booking_service.create_booking(cust, vans[vans.van_name=="[DEMO] Aqua Four"].iloc[0]["id"], "on_demand", 17.3, 78.4)))
admin = {"id":"demo-admin","role":"admin"}
out.append(("admin save van", *van_service.save_van({"van_name":"[DEMO] New Unit","service_type":"stationed","latitude":17.4,"longitude":78.5,"address":"x","availability_status":"available","operating_hours":"24x7","water_capacity":500.0,"water_level":100.0,"waste_capacity":300.0,"waste_level":10.0,"operator_id":None}, ["Private toilet","Running water"])))
out.append(("admin bad hours (False)", *van_service.save_van({"van_name":"Bad","service_type":"stationed","latitude":17.4,"longitude":78.5,"address":"","availability_status":"available","operating_hours":"abc","water_capacity":500.0,"water_level":0.0,"waste_capacity":300.0,"waste_level":0.0,"operator_id":None}, [])))
out.append(("cust cancel after on_the_way n/a", "", ""))
st.session_state["out"] = out
'''
at = AppTest.from_string(SCRIPT, default_timeout=60).run()
assert not at.exception, at.exception
for row in at.session_state["out"]: print(row)
