from __future__ import annotations

import streamlit as st

from muronto_app.page_helpers import render_project_context

st.set_page_config(page_title="Muronto Subject", layout="centered")


def main() -> None:
    if not render_project_context("Subject"):
        return

    st.subheader("Subject")
    st.info("Subject records will be added here.")


if __name__ == "__main__":
    main()
