from pathlib import Path

DEFAULT_DATA_AGENT_SYSTEM_PROMPT_PATH = Path("prompts/data_agent_system.md")


def load_data_agent_system_prompt(
    path: Path = DEFAULT_DATA_AGENT_SYSTEM_PROMPT_PATH,
) -> str:
    prompt = path.read_text(encoding="utf-8").strip()
    if not prompt:
        raise ValueError(f"System prompt file is empty: {path}")
    return prompt
