from __future__ import annotations

import streamlit as st

from muronto_app.page_helpers import render_project_context

st.set_page_config(page_title="Muronto Surgery", layout="centered")


def main() -> None:
    if not render_project_context("Surgery"):
        return

    st.subheader("Surgery")
    st.info("Surgery records will be added here.")


if __name__ == "__main__":
    main()
