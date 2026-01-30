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
                                    value=yaml.dump(
                                        playground.current_config.model_dump(),
                                        default_flow_style=False,
                                    ),
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
                                    value=playground.current_actions,
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
                                    value=playground.current_rails,
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
                    label="Probe Status", interactive=False, lines=20
                )
                refresh_probes_btn = gr.Button("🔄 Refresh Status")

                def handle_start_probe_streaming(
                    probe_type_val, use_guardrails_val, generations_val, parallel_attempts_val
                ):
                    # Use the new streaming method
                    for output in playground.stream_garak_probe_live(
                        probe_type_val,
                        use_guardrails_val,
                        generations_val,
                        parallel_attempts_val,
                    ):
                        yield output

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
                    benchmark_type = gr.Dropdown(
                        choices=["throughput", "latency"],
                        value="throughput",
                        label="Benchmark Type",
                    )

                start_benchmark_btn = gr.Button(
                    "📊 Start Performance Benchmark", variant="primary"
                )
                benchmark_status_display = gr.Textbox(
                    label="Benchmark Status", interactive=False, lines=20
                )
                refresh_benchmarks_btn = gr.Button("🔄 Refresh Status")

                def handle_start_benchmark(bench_type):
                    return playground.start_performance_benchmark(bench_type)

                def handle_refresh_benchmarks():
                    return playground.get_benchmark_status()

                start_benchmark_btn.click(
                    handle_start_benchmark, [benchmark_type], [benchmark_status_display]
                )
                refresh_benchmarks_btn.click(
                    handle_refresh_benchmarks, [], [benchmark_status_display]
                )
                
                # Auto-refresh benchmark status every 3 seconds
                benchmark_timer = gr.Timer(value=3)
                benchmark_timer.tick(
                    handle_refresh_benchmarks, [], [benchmark_status_display]
                )

    return app
