from dataclasses import dataclass
from typing import Any

from src.agents.tools import SqlExecutor
from src.core.errors import AppError, ErrorCode
from src.domain.intent import Intent, IntentResult, Language
from src.domain.response import AgentResponse, Visualization
from src.rag.knowledge_service import KnowledgeService, RetrievedChunk
from src.router.intent_router import IntentRouter
from src.utils.formatting import compact_table, percent, seconds


@dataclass(frozen=True)
class SqlPlan:
    sql: str
    visualization_type: str
    title: str
    answer_kind: str


class DataAgent:
    def __init__(
        self,
        *,
        router: IntentRouter,
        knowledge_service: KnowledgeService,
        database: SqlExecutor,
    ) -> None:
        self.router = router
        self.knowledge_service = knowledge_service
        self.database = database

    def answer(self, message: str, *, memory_context: str | None = None) -> AgentResponse:
        route = self.router.route(message)
        if route.intent == Intent.UNSAFE:
            return AgentResponse(
                type="unsafe",
                answer=self._localized(route.language, "Input khong an toan.", "Unsafe input."),
                language=route.language,
                reasoning_steps=[route.reason],
            )
        if route.intent == Intent.OUT_OF_SCOPE:
            return AgentResponse(
                type="out_of_scope",
                answer=self._localized(
                    route.language,
                    "Cau hoi nay nam ngoai pham vi chatbot phan tich tong dai.",
                    "This question is outside the call center analytics scope.",
                ),
                language=route.language,
                reasoning_steps=[route.reason],
            )
        if route.intent == Intent.CHITCHAT:
            return AgentResponse(
                type="answer",
                answer=self._localized(
                    route.language,
                    "Xin chao, toi co the ho tro phan tich KPI tong dai.",
                    "Hello, I can help analyze call center KPIs.",
                ),
                language=route.language,
                reasoning_steps=[route.reason],
            )

        retrieval_query = f"{memory_context}\n\n{message}" if memory_context else message
        knowledge = self.knowledge_service.retrieve(retrieval_query, limit=4)
        plan = self._plan_sql(message, route, knowledge)
        if plan is None:
            return self._clarify_metric(route.language)

        rows, sql_executed, retry_steps = self._execute_with_retry(plan.sql)
        return self._format_response(
            route.language, plan, rows, knowledge, sql_executed, retry_steps
        )

    def _plan_sql(
        self,
        message: str,
        route: IntentResult,
        knowledge: list[RetrievedChunk],
    ) -> SqlPlan | None:
        lowered = message.lower()
        if "abandon" in lowered:
            return SqlPlan(
                sql="""
                SELECT
                    DATE_TRUNC('month', d.call_start) AS month,
                    COUNT(DISTINCT d.call_id) AS total_calls,
                    COUNT(DISTINCT a.call_id) AS abandoned_calls,
                    ROUND(
                        COUNT(DISTINCT a.call_id)::numeric
                        / NULLIF(COUNT(DISTINCT d.call_id), 0),
                        4
                    ) AS abandon_sys
                FROM distribution_call d
                LEFT JOIN abandoned_call a ON a.call_id = d.call_id
                GROUP BY month
                ORDER BY month
                LIMIT 24
                """,
                visualization_type="bar_chart",
                title="Ti le Abandon theo thang",
                answer_kind="abandon",
            )

        if any(keyword in lowered for keyword in ["yeu cau", "request"]):
            return SqlPlan(
                sql="""
                SELECT
                    r.name AS request_name,
                    COUNT(*) AS request_count,
                    ROUND(COUNT(*)::numeric / NULLIF(SUM(COUNT(*)) OVER (), 0), 4) AS share
                FROM call_log l
                JOIN distribution_call d ON d.call_id = l.call_id
                JOIN request_code r ON r.code = l.request_code
                WHERE d.call_type = 'Inbound'
                GROUP BY r.name
                ORDER BY request_count DESC
                LIMIT 10
                """,
                visualization_type="pie_chart",
                title="Ty trong yeu cau khach hang",
                answer_kind="request_mix",
            )

        if any(keyword in lowered for keyword in ["agent", "nang suat", "productivity"]):
            return SqlPlan(
                sql="""
                SELECT
                    ag.agent_id,
                    ag.agent_name,
                    COUNT(d.call_id) AS handled_calls,
                    SUM(d.talk_dur + d.wrapup_dur) AS useful_seconds
                FROM agent ag
                JOIN distribution_call d ON d.agent_id = ag.agent_id
                GROUP BY ag.agent_id, ag.agent_name
                ORDER BY handled_calls DESC, useful_seconds DESC
                LIMIT 10
                """,
                visualization_type="bar_chart",
                title="Nang suat agent",
                answer_kind="agent_productivity",
            )

        if any(keyword in lowered for keyword in ["talk", "dam thoai", "đàm thoại"]):
            return SqlPlan(
                sql="""
                SELECT
                    ag.agent_name,
                    ROUND(AVG(d.talk_dur), 2) AS avg_talk_seconds
                FROM distribution_call d
                JOIN agent ag ON ag.agent_id = d.agent_id
                GROUP BY ag.agent_name
                ORDER BY avg_talk_seconds DESC
                LIMIT 10
                """,
                visualization_type="bar_chart",
                title="Thoi gian talk trung binh",
                answer_kind="avg_talk",
            )

        return None

    def _format_response(
        self,
        language: Language,
        plan: SqlPlan,
        rows: list[dict[str, Any]],
        knowledge: list[RetrievedChunk],
        sql_executed: str,
        retry_steps: list[str],
    ) -> AgentResponse:
        answer = self._answer_text(language, plan, rows)
        reasoning_steps = [
            f"Retrieved {len(knowledge)} knowledge chunks",
            f"Selected SQL template for {plan.answer_kind}",
            f"Executed SQL successfully, {len(rows)} rows returned",
            *retry_steps,
        ]
        return AgentResponse(
            type="answer",
            answer=answer,
            language=language,
            visualization=Visualization(
                type=plan.visualization_type,  # type: ignore[arg-type]
                title=plan.title,
                data=rows,
            ),
            sql_executed=sql_executed.strip(),
            reasoning_steps=reasoning_steps,
        )

    def _execute_with_retry(self, sql: str) -> tuple[list[dict[str, Any]], str, list[str]]:
        try:
            return self.database.execute_select(sql), sql, []
        except AppError as exc:
            if exc.code != ErrorCode.SQL_LIMIT_REQUIRED:
                raise

        retried_sql = f"{sql.rstrip().rstrip(';')} LIMIT 100"
        rows = self.database.execute_select(retried_sql)
        return rows, retried_sql, ["Retried SQL after adding LIMIT 100"]

    def _answer_text(self, language: Language, plan: SqlPlan, rows: list[dict[str, Any]]) -> str:
        if not rows:
            return self._localized(language, "Khong co du lieu phu hop.", "No matching data found.")

        first = rows[0]
        if plan.answer_kind == "abandon":
            return self._localized(
                language,
                f"Ti le abandon dau ky la {percent(first.get('abandon_sys'))}.",
                f"The first period abandon rate is {percent(first.get('abandon_sys'))}.",
            )
        if plan.answer_kind == "request_mix":
            request_name = first.get("request_name")
            share = percent(first.get("share"))
            return self._localized(
                language,
                f"Yeu cau cao nhat la {request_name} voi ty trong {share}.",
                f"The top request is {request_name} with {share} share.",
            )
        if plan.answer_kind == "agent_productivity":
            agent_name = first.get("agent_name")
            handled_calls = first.get("handled_calls")
            return self._localized(
                language,
                f"Agent nang suat cao nhat la {agent_name} voi {handled_calls} cuoc.",
                f"The most productive agent is {agent_name} with {handled_calls} calls.",
            )
        if plan.answer_kind == "avg_talk":
            return self._localized(
                language,
                f"Thoi gian talk trung binh cao nhat la {seconds(first.get('avg_talk_seconds'))}.",
                f"The highest average talk time is {seconds(first.get('avg_talk_seconds'))}.",
            )
        return compact_table(rows)

    def _clarify_metric(self, language: Language) -> AgentResponse:
        options = [
            "Abandon/SLA",
            "Yeu cau khach hang",
            "Nang suat agent",
            "Thoi gian talk",
        ]
        return AgentResponse(
            type="clarification_needed",
            answer=self._localized(
                language,
                "Ban muon phan tich chi so tong dai nao?",
                "Which call center metric do you want to analyze?",
            ),
            language=language,
            options=options,
            reasoning_steps=["Data query intent detected but metric is ambiguous"],
        )

    def _localized(self, language: Language, vi: str, en: str) -> str:
        return vi if language == Language.VI else en
