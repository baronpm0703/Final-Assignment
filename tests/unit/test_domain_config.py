from pathlib import Path

from src.domain.config import load_domain_config
from src.infrastructure.sql_validator import SqlValidator
from src.router.intent_router import IntentRouter


def test_loads_default_domain_manifest() -> None:
    domain_config = load_domain_config("config/domain.yaml")

    assert domain_config.domain.name == "call_center_analytics"
    assert domain_config.knowledge.root_path == Path("knowledge")
    assert "distribution_call" in domain_config.schema.allowed_schema


def test_fake_domain_can_drive_router_and_validator(tmp_path: Path) -> None:
    config_path = tmp_path / "domain.yaml"
    utterances_path = tmp_path / "intent_utterances.json"
    utterances_path.write_text(
        """
{
  "data_query": ["show order revenue", "order analytics"],
  "out_of_scope": ["weather forecast"],
  "chitchat": ["hello"],
  "unsafe": ["drop table"]
}
""",
        encoding="utf-8",
    )
    config_path.write_text(
        f"""
domain:
  name: retail_analytics
  description: Retail order analytics.
knowledge:
  root_path: knowledge
prompts:
  system_prompt_path: prompts/data_agent_system.md
schema:
  allowed_functions: [count, sum]
  allowed_tables:
    orders:
      columns: [order_id, customer_id, amount]
router:
  intent_utterances_path: {utterances_path}
  bm25_confidence_threshold: 0.55
  llm_fallback_enabled: false
agent:
  business_question_keywords: [definition]
  offline_query_plans: []
response:
  clarification_options: [Revenue, Orders]
""",
        encoding="utf-8",
    )
    domain_config = load_domain_config(config_path)

    router_result = IntentRouter.default(domain_config).route("show order revenue")
    validator = SqlValidator(
        allowed_schema=domain_config.schema.allowed_schema,
        allowed_functions=domain_config.schema.allowed_function_set,
    )
    validated = validator.validate("SELECT order_id, amount FROM orders LIMIT 10")

    assert router_result.intent.value == "data_query"
    assert validated.tables == frozenset({"orders"})
