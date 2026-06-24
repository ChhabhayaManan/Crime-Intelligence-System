import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import forms
from utils import require_auth

st.set_page_config(page_title="New Record — CIS", layout="wide")
require_auth()

st.title("New Record")
st.caption("Create a top-level entity. Case child-records (evidence, suspects, …) are added from a case on the Dashboard.")

choice = st.radio("What do you want to create?", ["Case", "Person", "Address"], horizontal=True)

st.divider()
if choice == "Address":
    st.write("Standalone address (reusable as a person's address or a crime location).")
    if st.button("➕ Create address", type="primary"):
        forms.dialog_new_address()
elif choice == "Person":
    st.write("A person can later be linked as reporter, officer, suspect, witness, or victim.")
    if st.button("➕ Create person", type="primary"):
        forms.dialog_new_person()
else:
    st.write("Opening a case needs a reporter (person) and a crime location (address). Both can be created inline.")
    if st.button("➕ Open case", type="primary"):
        forms.dialog_new_case()
