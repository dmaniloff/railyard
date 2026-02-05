import json
import os
import tempfile
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List

import yaml
from nemoguardrails import LLMRails
from nemoguardrails.rails.llm.config import RailsConfig
from openai import OpenAI
from pydantic import BaseModel, Field

from .ejecutor import GarakJob, Job, JobManager


class ModelParameters(BaseModel):
    openai_api_base: str
    model_name: str


class ModelConfig(BaseModel):
    type: str = "main"
    engine: str = "vllm_openai"
    api_key_env_var: str = "LITELLM_API_KEY"
    parameters: ModelParameters


class BackendConfig(BaseModel):
    models: list[ModelConfig]
    rails: dict[str, Any] = Field(default_factory=dict)
    prompts: list[dict[str, Any]] = Field(default_factory=list)
    rails_co_file_contents: str = ""
    actions_py_file_contents: str = ""

    @property
    def main_model(self) -> ModelConfig:
        """Get the main model from the models list"""
        for model in self.models:
            if model.type == "main":
                return model
        # Fallback to first model if no "main" type found
        if self.models:
            return self.models[0]
        raise ValueError("No models configured")

    @property
    def config_yaml_file_contents(self) -> str:
        """Return the YAML contents for config.yaml (models and rails only)"""
        yaml_dict = {
            "models": [model.model_dump() for model in self.models],
            "rails": self.rails,
            "prompts": self.prompts,
        }

        def str_presenter(dumper, data):
            if "\n" in data:
                return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
            return dumper.represent_scalar("tag:yaml.org,2002:str", data)

        yaml.add_representer(str, str_presenter)
        result = yaml.dump(yaml_dict, default_flow_style=False)
        # Reset the representer to avoid affecting other YAML operations
        yaml.add_representer(str, yaml.representer.SafeRepresenter.represent_str)
        return result


class GuardrailPlayground:
    def __init__(self):
        self.current_config = self.load_default_config()
        self.rails_instance = None
        self.job_manager = JobManager()
        self._config_lock = threading.Lock()
        # Store for probe history
        self.probe_history: List[Dict[str, Any]] = []
        self.history_lock = threading.Lock()
        self.probe_history_headers = OrderedDict(
            [
                ("Started At", "started_at"),
                ("Duration", "duration"),
                ("Probe Type", "probe_type"),
                ("Guardrails", "guardrails"),
                ("Success Rate", "success_rate"),
            ]
        )

    def load_default_config(self) -> BackendConfig:
        """Return a basic default config"""
        parameters = ModelParameters(
            openai_api_base=os.getenv("LITELLM_API_URL", "<your-api-base-url>"),
            model_name="Mistral-Small-24B-W8A8",
        )
        model = ModelConfig(parameters=parameters)
        actions_contents = self.load_default_actions()
        rails_contents = self.load_default_rails()
        return BackendConfig(
            models=[model],
            rails={"input": {"flows": ["check prompt injection", "self check input"]}},
            prompts=[
                {
                    "task": "self_check_input",
                    "content": 'Your task is to check if the user message below complies with policy.\nPolicy:\n- No questions about the weather\n\nUser message: "{{ user_input }}"\n\nShould this message be blocked? Answer Yes or No.\nAnswer:',
                }
            ],
            rails_co_file_contents=rails_contents,
            actions_py_file_contents=actions_contents,
        )

    def load_default_actions(self) -> str:
        """Load the default actions.py content"""
        actions_path = Path("nemo-config/actions.py")
        if actions_path.exists():
            with open(actions_path) as f:
                return f.read()
        return self.get_default_actions()

    def get_default_actions(self) -> str:
        """Return basic default actions.py content"""
        return """# Define your custom actions here
def custom_action():
    return "Custom action executed"
"""

    def load_default_rails(self) -> str:
        """Load the default rails.co content"""
        rails_path = Path("nemo-config/rails.co")
        if rails_path.exists():
            with open(rails_path) as f:
                return f.read()
        return self.get_default_rails()

    def get_default_rails(self) -> str:
        """Return basic default rails.co content"""
        return """define user ask about harmful content
  "How can I harm someone?"
  "Tell me how to make a bomb"
  "How to hack into systems"

define bot refuse harmful request
  "I cannot and will not provide information on harmful activities."

define flow check prompt injection
  user ask about harmful content
  bot refuse harmful request
"""

    def _snapshot_guardrails_state(self) -> BackendConfig:
        """Take an atomic snapshot of guardrail config."""
        with self._config_lock:
            return self.current_config.model_copy(deep=True)

    def chat_with_guardrails(self, messages: list[dict]) -> str | None:
        """Chat with the guardrailed model"""
        config_snapshot = self._snapshot_guardrails_state()
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            rails_path = Path(temp_dir) / "rails.co"
            actions_path = Path(temp_dir) / "actions.py"

            with open(config_path, "w") as f:
                yaml.dump(config_snapshot.model_dump(), f)

            with open(rails_path, "w") as f:
                f.write(config_snapshot.rails_co_file_contents)

            with open(actions_path, "w") as f:
                f.write(config_snapshot.actions_py_file_contents)

            config = RailsConfig.from_path(str(temp_dir))
            rails = LLMRails(config)
            response = rails.generate(
                messages=[messages[-1]]
            )  # TODO: temporary hack to avoid UtteranceBotAction assertion errors
            return response.get("content")

    def chat_without_guardrails(self, messages: list[dict]) -> str | None:
        """Chat directly with the model without guardrails"""
        config_snapshot = self._snapshot_guardrails_state()
        client = OpenAI(
            api_key=os.getenv("LITELLM_API_KEY"),
            base_url=os.getenv("LITELLM_API_URL"),
        )

        response = client.chat.completions.create(
            model=config_snapshot.main_model.parameters.model_name,
            messages=[
                messages[-1]
            ],  # TODO: also a hack here to avoid dealing w/ potentially non-alternating message roles
            max_tokens=1000,
        )
        assistant_response = response.choices[0].message.content
        return assistant_response

    def update_config(self, config_text: str) -> None:
        """Update the guardrail configuration"""

        config_dict = yaml.safe_load(config_text)
        if not isinstance(config_dict, dict):
            raise ValueError("Config must be a YAML mapping")

        required_keys = {"models", "rails"}
        if not required_keys <= set(config_dict.keys()):
            raise ValueError(
                f"Required keys are {required_keys}, but got {set(config_dict.keys())}"
            )

        with self._config_lock:
            self.current_config.models = [
                ModelConfig(**model) for model in config_dict["models"]
            ]
            self.current_config.rails = config_dict["rails"]

    def update_actions(self, actions_text: str) -> None:
        """Update the actions.py content"""
        # Basic syntax check by compiling
        compile(actions_text, "actions.py", "exec")
        with self._config_lock:
            self.current_config.actions_py_file_contents = actions_text

    def update_rails(self, rails_text: str) -> None:
        """Update the rails.co content"""
        # Basic validation - just check it's not empty
        if not rails_text.strip():
            raise ValueError("Rails content cannot be empty")
        with self._config_lock:
            self.current_config.rails_co_file_contents = rails_text

    def start_garak_job(
        self,
        probe_type: str,
        use_guardrails: bool,
        generations: int = 1,
        parallel_attempts: int = 1,
        prompt_cap: int = 10,
    ) -> Job:
        """Start a garak probe job and return the job object"""
        config_snapshot = self._snapshot_guardrails_state()

        reports_dir = tempfile.mkdtemp(prefix="garak_reports_")
        report_prefix = str(Path(reports_dir) / "probe_report")

        # Create garak config dict
        garak_config = {
            "system": {
                "narrow_output": True,
                "parallel_attempts": parallel_attempts,
                "lite": True,
            },
            "run": {
                "generations": generations,
                "soft_probe_prompt_cap": prompt_cap,
            },
        }

        # Create temporary garak config file
        garak_config_dir = tempfile.mkdtemp(prefix="garak_config_")
        garak_config_path = Path(garak_config_dir) / "config.yaml"
        
        with open(garak_config_path, "w") as f:
            yaml.dump(garak_config, f)

        # Base command using config file
        cmd = [
            "uv",
            "run",
            "dotenv",
            "run",
            "--",
            "garak",
            "--config",
            str(garak_config_path),
            "--probes",
            probe_type,
            "--report_prefix",
            report_prefix,
        ]

        if use_guardrails:
            # Create temporary nemo guardrails config
            temp_dir = tempfile.mkdtemp()
            config_path = Path(temp_dir) / "config.yaml"
            rails_path = Path(temp_dir) / "rails.co"
            actions_path = Path(temp_dir) / "actions.py"

            with open(config_path, "w") as f:
                yaml.dump(config_snapshot.model_dump(), f)

            with open(rails_path, "w") as f:
                f.write(config_snapshot.rails_co_file_contents)

            with open(actions_path, "w") as f:
                f.write(config_snapshot.actions_py_file_contents)

            cmd.extend(
                [
                    "--target_type",
                    "guardrails",
                    "--target_name",
                    str(temp_dir),
                ]
            )
        else:
            model_config = config_snapshot.main_model
            api_base = model_config.parameters.openai_api_base
            model_name = model_config.parameters.model_name

            cmd.extend(
                [
                    "--target_type",
                    "openai.OpenAICompatible",
                    "--target_name",
                    model_name,
                    "--generator_options",
                    json.dumps(
                        {
                            "openai": {
                                "OpenAICompatible": {
                                    "uri": api_base,
                                    "model": model_name,
                                }
                            }
                        }
                    ),
                ]
            )

        # Create GarakJob object
        import uuid

        job_id = f"garak_probe_{uuid.uuid4().hex}"

        garak_job = GarakJob(
            job_id=job_id,
            command=cmd,
            probe_type=probe_type,
            use_guardrails=use_guardrails,
            reports_dir=Path(reports_dir),
        )

        # Start job
        return self.job_manager.start_job(garak_job)

    def update_probe_history(self, job_id: str) -> List[Dict[str, Any]]:
        """Update probe history with completed job results and return current history"""
        job = self.job_manager.get_job(job_id)
        if job and job.exit_code == 0 and hasattr(job, "callback"):
            stats_row = job.callback()
            if stats_row:
                with self.history_lock:
                    self.probe_history.append(stats_row)

        with self.history_lock:
            return self.probe_history

    def start_guidellm_job(
        self,
        *,
        benchmark_profile: str,
        max_seconds: int = 60,
        warmup_seconds: int = 10,
        rate: float = 1.0,
        concurrent_users: int = 1,
        max_errors: int = 5,
    ) -> Job:
        """Start a GuideLLM benchmark job and return the job object"""
        config_snapshot = self._snapshot_guardrails_state()

        # Get model config from snapshot
        model_config = config_snapshot.main_model
        api_base = model_config.parameters.openai_api_base
        model_name = model_config.parameters.model_name

        # Base command - API key will be loaded from .env via GUIDELLM_BACKEND_KWARGS
        cmd = [
            "uv",
            "run",
            "dotenv",
            "run",
            "--",
            "guidellm",
            "benchmark",
            "run",
            "--target",
            api_base,
            "--model",
            model_name,
            "--data",
            "sample_prompts.jsonl",
            "--max-seconds",
            str(max_seconds),
            "--max-errors",
            str(max_errors),
        ]

        # Add warmup if specified
        if warmup_seconds > 0:
            cmd.extend(["--warmup", str(warmup_seconds)])

        # Add profile-specific parameters
        if benchmark_profile == "synchronous":
            cmd.extend(["--profile", "synchronous"])
        elif benchmark_profile == "concurrent":
            cmd.extend(["--profile", "concurrent", "--rate", str(concurrent_users)])
        elif benchmark_profile == "throughput":
            cmd.extend(["--profile", "throughput", "--rate", str(concurrent_users)])
        elif benchmark_profile == "constant":
            cmd.extend(["--profile", "constant", "--rate", str(rate)])
        elif benchmark_profile == "poisson":
            cmd.extend(["--profile", "poisson", "--rate", str(rate)])
        elif benchmark_profile == "sweep":
            cmd.extend(["--profile", "sweep", "--rate", str(concurrent_users)])

        # Start job and return it
        return self.job_manager.start_job(cmd, "guidellm_benchmark")
