import streamlit as st
from pathlib import Path
from playwright_script import run_capture  # make sure to rename your main script to playwright_script.py

st.set_page_config(page_title="📰 Article Screenshot Tool", layout="centered")

st.title("📰 Article Screenshot Tool")
st.markdown("Enter one or more article URLs below (one per line).")

url_input = st.text_area("Article URLs", height=200)

if st.button("📸 Capture Screenshots"):
    urls = [u.strip() for u in url_input.splitlines() if u.strip()]
    if urls:
        with open("urls.txt", "w") as f:
            for url in urls:
                f.write(url + "\n")
        st.info("Running capture...")
        run_capture(urls)
        st.success("✅ Screenshots saved in the 'screenshots' folder!")
    else:
        st.warning("⚠️ Please enter at least one URL.")
