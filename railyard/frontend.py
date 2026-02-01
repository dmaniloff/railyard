import gradio as gr
import yaml

from .backend import GuardrailPlayground


def create_app():
    playground = GuardrailPlayground()

    with gr.Blocks(title="Railyard") as app:
        gr.Markdown("# 🛤️ Railyard")

        with gr.Tabs():
            # Purple Section - Chat and Config
            with gr.Tab("🟣 Configure & Chat") as purple_tab:
                with gr.Row(height=400, equal_height=True):
                    with gr.Column(scale=1):
                        gr.Markdown("### Chat with AI")

                        enable_guardrails = gr.Checkbox(
                            label="Enable Guardrails",
                            value=True,
                            info="Toggle to enable/disable guardrail protection",
                        )
                        chatbot = gr.Chatbot(label="AI Assistant")
                        msg_input = gr.Textbox(
                            label="Message", placeholder="Type your message..."
                        )
                        send_btn = gr.Button("Send", variant="primary")

                    with gr.Column(scale=2):
                        gr.Markdown("### Configuration")
                        with gr.Tabs():
                            with gr.Tab("config.yaml"):
                                config_editor = gr.Code(
                                    value=playground.current_config.config_yaml_file_contents,
                                    language="yaml",
                                    label="config.yaml",
                                    lines=40,
                                    max_lines=40,
                                )
                                update_config_btn = gr.Button(
                                    "Update Config", variant="primary"
                                )
                                config_status = gr.Textbox(
                                    label="Status", interactive=False
                                )

                            with gr.Tab("actions.py"):
                                actions_editor = gr.Code(
                                    value=playground.current_config.actions_py_file_contents,
                                    language="python",
                                    label="actions.py",
                                    lines=40,
                                    max_lines=40,
                                )
                                update_actions_btn = gr.Button(
                                    "Update Actions", variant="primary"
                                )
                                actions_status = gr.Textbox(
                                    label="Status", interactive=False
                                )

                            with gr.Tab("rails.co"):
                                rails_editor = gr.Code(
                                    value=playground.current_config.rails_co_file_contents,
                                    label="rails.co",
                                    lines=40,
                                    max_lines=40,
                                )
                                update_rails_btn = gr.Button(
                                    "Update Rails", variant="primary"
                                )
                                rails_status = gr.Textbox(
                                    label="Status", interactive=False
                                )

                # Event handlers for purple section
                async def handle_chat(message, history, enable_guardrails):
                    if enable_guardrails:
                        return await playground.chat_with_guardrails(message, history)
                    else:
                        return await playground.chat_without_guardrails(
                            message, history
                        )

                def handle_config_update(config_text):
                    return playground.update_config(config_text)

                def handle_actions_update(actions_text):
                    return playground.update_actions(actions_text)

                def handle_rails_update(rails_text):
                    return playground.update_rails(rails_text)

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
                    handle_config_update, [config_editor], [config_status]
                )
                update_actions_btn.click(
                    handle_actions_update, [actions_editor], [actions_status]
                )
                update_rails_btn.click(
                    handle_rails_update, [rails_editor], [rails_status]
                )

            # Red Section - Security Probes
            with gr.Tab("🔴 Security Testing") as red_tab:
                gr.Markdown("### Malicious Probe Testing")
                gr.Markdown(
                    "Test the system's defenses against various attack patterns using Garak."
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
                    use_guardrails = gr.Checkbox(label="Use Guardrails", value=True)

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

                start_probe_btn = gr.Button("🚨 Start Security Probe", variant="stop")
                probe_status_display = gr.Textbox(
                    label="Probe Status", interactive=False, lines=20,
                    info="Ready to start security probe"
                )
                refresh_probes_btn = gr.Button("🔄 Refresh Status")

                def handle_start_probe_streaming(
                    probe_type_val,
                    use_guardrails_val,
                    generations_val,
                    parallel_attempts_val,
                ):
                    # Start the job first
                    job = playground.start_garak_job(
                        probe_type_val,
                        use_guardrails_val,
                        generations_val,
                        parallel_attempts_val,
                    )
                    
                    # Clear status and update info to show job starting
                    guardrails_text = "with guardrails" if use_guardrails_val else "without guardrails"
                    yield gr.update(value="", info=f"🚨 Starting {probe_type_val} probe {guardrails_text}: {job.command_display}")
                    
                    try:
                        # Stream the job output
                        for output in job.stream_output():
                            yield output
                        
                        # When streaming finishes, check job exit code
                        exit_code = job.exit_code
                        if exit_code == 0:
                            yield gr.update(info=f"✅ {probe_type_val} probe completed successfully")
                        else:
                            yield gr.update(info=f"❌ {probe_type_val} probe failed (exit code: {exit_code})")
                        
                    except Exception as e:
                        # If streaming fails, update info to show error
                        yield gr.update(info=f"❌ {probe_type_val} probe failed: {str(e)}")

                def handle_refresh_probes():
                    return playground.get_probe_status()

                start_probe_btn.click(
                    handle_start_probe_streaming,
                    [probe_type, use_guardrails, generations, parallel_attempts],
                    [probe_status_display],
                )
                refresh_probes_btn.click(
                    handle_refresh_probes, [], [probe_status_display]
                )

            # Blue Section - Performance Testing
            with gr.Tab("🔵 Performance Testing") as blue_tab:
                gr.Markdown("### Performance Benchmarking")
                gr.Markdown("Measure system performance using GuideLLM benchmarks.")

                with gr.Row():
                    benchmark_profile = gr.Dropdown(
                        choices=["synchronous", "concurrent", "throughput", "constant", "poisson", "sweep"],
                        value="throughput",
                        label="Benchmark Profile",
                    )
                
                with gr.Row():
                    max_seconds = gr.Slider(
                        minimum=30, maximum=300, value=60, step=10,
                        label="Duration (seconds)",
                        info="How long to run the benchmark"
                    )
                    warmup_seconds = gr.Slider(
                        minimum=0, maximum=60, value=10, step=5,
                        label="Warmup (seconds)", 
                        info="Ramp-up period before measuring"
                    )
                
                with gr.Row():
                    rate = gr.Slider(
                        minimum=0.1, maximum=50, value=1.0, step=0.1,
                        label="Request Rate (req/sec)",
                        info="Requests per second"
                    )
                    concurrent_users = gr.Slider(
                        minimum=1, maximum=20, value=1, step=1,
                        label="Concurrent Users",
                        info="Number of parallel users"
                    )
                
                with gr.Row():
                    max_errors = gr.Slider(
                        minimum=1, maximum=20, value=5, step=1,
                        label="Max Errors",
                        info="Stop benchmark after this many errors"
                    )

                start_benchmark_btn = gr.Button(
                    "📊 Start Performance Benchmark", variant="primary"
                )
                benchmark_status_display = gr.Textbox(
                    label="Benchmark Status", interactive=False, lines=20,
                    info="Ready to start benchmark"
                )

                def handle_start_benchmark_streaming(profile, max_sec, warmup_sec, req_rate, users, errors):
                    """Stream benchmark output in real-time"""
                    # Start the job first
                    job = playground.start_guidellm_job(
                        profile, max_sec, warmup_sec, req_rate, users, errors
                    )
                    
                    # Clear status and update info to show job starting
                    yield gr.update(value="", info=f"🚀 Starting {profile} benchmark: {job.command_display}")
                    
                    try:
                        # Stream the job output
                        for output in job.stream_output():
                            yield output
                        
                        # When streaming finishes, check job exit code
                        exit_code = job.exit_code
                        if exit_code == 0:
                            yield gr.update(info=f"✅ {profile} benchmark completed successfully")
                        else:
                            yield gr.update(info=f"❌ {profile} benchmark failed (exit code: {exit_code})")
                        
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
                    [rate, concurrent_users]
                )
                
                start_benchmark_btn.click(
                    handle_start_benchmark_streaming, 
                    [benchmark_profile, max_seconds, warmup_seconds, rate, concurrent_users, max_errors], 
                    [benchmark_status_display]
                )


    return app
