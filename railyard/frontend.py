import time

import gradio as gr

from .backend import GuardrailPlayground


def create_app():
    playground = GuardrailPlayground()

    with gr.Blocks(title="Railyard") as app:
        gr.Markdown("# 🛤️ Railyard")
        gr.Markdown("""
        **Welcome to Railyard** - a simple guardrails playground.
        
        Railyard helps you:
        - **Configure & test** [Nemo Guardrails](https://github.com/NVIDIA/NeMo-Guardrails) for your AI models
        - **Run security probes** using [Garak](https://github.com/NVIDIA/Garak) to identify vulnerabilities  
        - **Benchmark performance** via [GuideLLM](https://github.com/vllm-project/GuideLLM) to measure system throughput
        - **Compare results** between protected and unprotected model interactions
        """)

        with gr.Tabs():
            # Purple Section - Chat and Config
            with gr.Tab("🟣 Configure & Chat") as purple_tab:
                gr.Markdown("### Configuration")
                gr.Markdown("Configure Nemo Guardrails by editing the following files:")
                with gr.Tabs() as config_tabs:
                    with gr.Tab("Config"):
                        config_editor = gr.Code(
                            value=playground.current_config.config_yaml_file_contents,
                            language="yaml",
                            label="config.yaml",
                            lines=15,
                            max_lines=15,
                        )

                    with gr.Tab("Rails"):
                        rails_editor = gr.Code(
                            value=playground.current_config.rails_co_file_contents,
                            label="rails.co",
                            lines=15,
                            max_lines=15,
                        )

                    with gr.Tab("Actions"):
                        actions_editor = gr.Code(
                            value=playground.current_config.actions_py_file_contents,
                            language="python",
                            label="actions.py",
                            lines=15,
                            max_lines=15,
                        )

                update_config_btn = gr.Button("Update Configuration", variant="primary")

                gr.Markdown("### Chat")
                gr.Markdown(
                    "Quickly test your configuration by chatting with the model."
                )
                enable_guardrails = gr.Checkbox(
                    label="Enable Guardrails",
                    value=True,
                )
                chatbot = gr.Chatbot(label="AI Assistant")
                msg_input = gr.Textbox(
                    label="Message", placeholder="Type your message..."
                )
                send_btn = gr.Button("Send", variant="primary")

                # Event handlers for purple section
                def handle_chat(message, history, enable_guardrails):
                    history.append(gr.ChatMessage(role="user", content=message))
                    converted_history = convert_history_to_openai_format(history)

                    if enable_guardrails:
                        chat_function = playground.chat_with_guardrails
                    else:
                        chat_function = playground.chat_without_guardrails

                    try:
                        response = chat_function(converted_history)
                        if response is None:
                            raise gr.Error("No response from model")
                    except Exception as e:
                        raise gr.Error(f"Error: {str(e)}")
                    else:
                        history.append(
                            gr.ChatMessage(role="assistant", content=response)
                        )
                        return "", history
                    finally:
                        pass
                        # history.append(gr.ChatMessage(role="user", content=message))
                        # return "", history

                def convert_history_to_openai_format(
                    history: list[gr.ChatMessage | dict],
                ) -> list[dict]:
                    messages = []
                    for msg in history:
                        if isinstance(msg, gr.ChatMessage):  # gr.ChatMessage object
                            messages.append({"role": msg.role, "content": msg.content})
                        elif isinstance(msg, dict):
                            messages.append(msg)
                        else:
                            raise ValueError(f"Invalid message type: {type(msg)}")
                    return messages

                def handle_config_update(config_text, rails_text, actions_text):
                    try:
                        yield gr.Button("Saving...", interactive=False)
                        time.sleep(0.1)

                        playground.update_config(config_text)
                        playground.update_rails(rails_text)
                        playground.update_actions(actions_text)

                    except Exception as e:
                        raise gr.Error(f"Failed to update configuration: {e}")
                        # yield gr.Button("❌ Some Failed!", interactive=False)
                        # time.sleep(1)
                        # yield gr.Button(
                        #     "Update Configuration", interactive=True, variant="primary"
                        # )
                    else:
                        yield gr.Button("✅ Saved!", interactive=False)
                        time.sleep(1)
                    finally:
                        yield gr.Button(
                            "Update Configuration", interactive=True, variant="primary"
                        )

                send_btn.click(
                    handle_chat,
                    [msg_input, chatbot, enable_guardrails],
                    [msg_input, chatbot],
                )
                msg_input.submit(
                    handle_chat,
                    [msg_input, chatbot, enable_guardrails],
                    [msg_input, chatbot],
                )
                update_config_btn.click(
                    handle_config_update,
                    [config_editor, rails_editor, actions_editor],
                    [update_config_btn],
                )

            # Red Section - Security Probes
            with gr.Tab("🔴 Security Testing") as red_tab:
                gr.Markdown("### Malicious Probe Testing")
                gr.Markdown(
                    "Test the system's defenses against various attack patterns using Garak."
                )

                with gr.Row():
                    with gr.Column():
                        use_guardrails = gr.Radio(
                            choices=["Hit model directly", "Enable guardrails"],
                            value="Enable guardrails",
                            label="Model Access Mode",
                        )
                    with gr.Column():
                        runtime_mode_security = gr.Radio(
                            choices=["Run locally", "Run in KFP"],
                            value="Run locally",
                            label="Scanner Runtime Mode",
                        )

                with gr.Row():
                    probe_type = gr.Dropdown(
                        choices=[
                            "promptinject.HijackKillHumans",
                            "promptinject.HijackHateSpeech",
                            "jailbreak.Dan",
                            "encoding.InjectBase64",
                            "leakage.SystemPromptLeak",
                        ],
                        value="promptinject.HijackKillHumans",
                        label="Probe Type",
                    )

                with gr.Row():
                    generations = gr.Slider(
                        minimum=1,
                        maximum=20,
                        value=1,
                        step=1,
                        label="Generations per Prompt",
                        info="Number of model generations for each prompt",
                    )
                    parallel_attempts = gr.Slider(
                        minimum=1,
                        maximum=10,
                        value=1,
                        step=1,
                        label="Parallel Attempts",
                        info="How many probe attempts to launch in parallel",
                    )

                    prompt_cap = gr.Slider(
                        minimum=1,
                        maximum=100,
                        value=10,
                        step=1,
                        label="Prompt Cap",
                        info="Maximum number of prompts to test per probe",
                    )

                start_probe_btn = gr.Button("🚨 Start Security Probe", variant="stop")
                last_probe_job_id = gr.Textbox(
                    value="", interactive=False, visible=False
                )
                probe_status_display = gr.Textbox(
                    label="Probe Status",
                    interactive=False,
                    lines=5,
                    info="Ready to start security probe",
                )

                gr.Markdown("### Probe History")
                probe_history_table = gr.Dataframe(
                    headers=list(playground.probe_history_headers.keys()),
                    datatype=["str"]
                    * len(list(playground.probe_history_headers.keys())),
                    interactive=False,
                    wrap=True,
                    value=[],  # Start with empty table
                )

                def handle_start_probe_streaming(
                    probe_type_val,
                    use_guardrails_val,
                    runtime_mode_val,
                    generations_val,
                    parallel_attempts_val,
                    prompt_cap_val,
                ):
                    job = playground.start_garak_job(
                        probe_type_val,
                        use_guardrails_val == "Use guardrails",
                        generations_val,
                        parallel_attempts_val,
                        prompt_cap_val,
                    )

                    # Update info to show job starting
                    guardrails_text = (
                        "with guardrails"
                        if use_guardrails_val == "Use guardrails"
                        else "without guardrails"
                    )
                    yield (
                        gr.update(
                            value="",
                            info=f"🚨 Starting {probe_type_val} probe {guardrails_text}: {job.command_display}",
                        ),
                        gr.update(value=job.job_id),
                    )

                    try:
                        # Stream the job output
                        for output in job.stream_output():
                            yield output, gr.update()

                        # When streaming finishes, check job exit code
                        exit_code = job.exit_code
                        if exit_code == 0:
                            yield (
                                gr.update(
                                    info=f"✅ {probe_type_val} probe completed successfully"
                                ),
                                gr.update(),
                            )
                        else:
                            yield (
                                gr.update(
                                    info=f"❌ {probe_type_val} probe failed (exit code: {exit_code})"
                                ),
                                gr.update(),
                            )

                    except Exception as e:
                        # If streaming fails, update info to show error
                        yield (
                            gr.update(
                                info=f"❌ {probe_type_val} probe failed: {str(e)}"
                            ),
                            gr.update(),
                        )

                def handle_history_probes_update(last_probe_job_id):
                    history = playground.update_probe_history(last_probe_job_id)
                    # Convert to table format expected by Gradio DataFrame
                    if history:
                        return [
                            [
                                row[value]
                                for value in playground.probe_history_headers.values()
                            ]
                            for row in history
                        ]

                def load_probe_history():
                    """Load existing probe history on app load/tab switch"""
                    history = playground.probe_history
                    if history:
                        return [
                            [
                                row[value]
                                for value in playground.probe_history_headers.values()
                            ]
                            for row in history
                        ]
                    return []

                start_probe_btn.click(
                    handle_start_probe_streaming,
                    [
                        probe_type,
                        use_guardrails,
                        runtime_mode_security,
                        generations,
                        parallel_attempts,
                        prompt_cap,
                    ],
                    [probe_status_display, last_probe_job_id],
                ).then(
                    handle_history_probes_update,
                    [last_probe_job_id],
                    [probe_history_table],
                )

                # Load probe history when the red tab is selected
                red_tab.select(load_probe_history, outputs=[probe_history_table])

            # Blue Section - Performance Testing
            with gr.Tab("🔵 Performance Testing") as blue_tab:
                gr.Markdown("### Performance Benchmarking")
                gr.Markdown("Measure system performance using GuideLLM benchmarks.")

                with gr.Row():
                    benchmark_profile = gr.Dropdown(
                        choices=[
                            "synchronous",
                            "concurrent",
                            "throughput",
                            "constant",
                            "poisson",
                            "sweep",
                        ],
                        value="throughput",
                        label="Benchmark Profile",
                    )

                with gr.Row():
                    max_seconds = gr.Slider(
                        minimum=30,
                        maximum=300,
                        value=60,
                        step=10,
                        label="Duration (seconds)",
                        info="How long to run the benchmark",
                    )
                    warmup_seconds = gr.Slider(
                        minimum=0,
                        maximum=60,
                        value=10,
                        step=5,
                        label="Warmup (seconds)",
                        info="Ramp-up period before measuring",
                    )

                with gr.Row():
                    rate = gr.Slider(
                        minimum=0.1,
                        maximum=50,
                        value=1.0,
                        step=0.1,
                        label="Request Rate (req/sec)",
                        info="Requests per second",
                    )
                    concurrent_users = gr.Slider(
                        minimum=1,
                        maximum=20,
                        value=1,
                        step=1,
                        label="Concurrent Users",
                        info="Number of parallel users",
                    )

                start_benchmark_btn = gr.Button(
                    "📊 Start Performance Benchmark", variant="primary"
                )
                benchmark_status_display = gr.Textbox(
                    label="Benchmark Status",
                    interactive=False,
                    lines=5,
                    info="Ready to start benchmark",
                )

                def handle_start_benchmark_streaming(
                    profile, max_sec, warmup_sec, req_rate, users
                ):
                    """Stream benchmark output in real-time"""
                    # Start the job first
                    job = playground.start_guidellm_job(
                        benchmark_profile=profile,
                        max_seconds=max_sec,
                        warmup_seconds=warmup_sec,
                        rate=req_rate,
                        concurrent_users=users,
                        max_errors=5,
                    )

                    # Clear status and update info to show job starting
                    yield gr.update(
                        value="",
                        info=f"🚀 Starting {profile} benchmark: {job.command_display}",
                    )

                    try:
                        # Stream the job output
                        for output in job.stream_output():
                            yield output

                        # When streaming finishes, check job exit code
                        exit_code = job.exit_code
                        if exit_code == 0:
                            yield gr.update(
                                info=f"✅ {profile} benchmark completed successfully"
                            )
                        else:
                            yield gr.update(
                                info=f"❌ {profile} benchmark failed (exit code: {exit_code})"
                            )

                    except Exception as e:
                        # If streaming fails, update info to show error
                        yield gr.update(info=f"❌ {profile} benchmark failed: {str(e)}")

                def update_config_visibility(profile):
                    """Update which configs are relevant based on benchmark profile"""
                    if profile == "synchronous":
                        return {
                            rate: gr.update(interactive=False, value=1.0),
                            concurrent_users: gr.update(interactive=False, value=1),
                        }
                    elif profile == "concurrent":
                        return {
                            rate: gr.update(interactive=False, value=1.0),
                            concurrent_users: gr.update(interactive=True),
                        }
                    elif profile == "throughput":
                        return {
                            rate: gr.update(interactive=False, value=50.0),
                            concurrent_users: gr.update(interactive=True),
                        }
                    elif profile in ["constant", "poisson"]:
                        return {
                            rate: gr.update(interactive=True),
                            concurrent_users: gr.update(interactive=False, value=1),
                        }
                    else:  # sweep
                        return {
                            rate: gr.update(interactive=False, value=1.0),
                            concurrent_users: gr.update(interactive=True),
                        }

                # Update config visibility when profile changes
                benchmark_profile.change(
                    update_config_visibility,
                    [benchmark_profile],
                    [rate, concurrent_users],
                )

                start_benchmark_btn.click(
                    handle_start_benchmark_streaming,
                    [
                        benchmark_profile,
                        max_seconds,
                        warmup_seconds,
                        rate,
                        concurrent_users,
                    ],
                    [benchmark_status_display],
                )

        # Load probe history when the app first loads
        app.load(load_probe_history, outputs=[probe_history_table])

    return app
