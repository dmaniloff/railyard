import os

import gradio as gr

from railyard.frontend import create_app

demo = create_app()


if __name__ == "__main__":
    auth_user = os.environ["RAILYARD_USER"]
    auth_pass = os.environ["RAILYARD_PASS"]

    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        theme=gr.themes.Soft(),
        auth=(auth_user, auth_pass),
    )
