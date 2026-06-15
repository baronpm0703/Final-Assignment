from src.memory.conversation_memory import ConversationMemory


def test_memory_keeps_recent_messages_verbatim() -> None:
    memory = ConversationMemory(window_size=4)
    memory.append("c1", "user", "Question 1")
    memory.append("c1", "assistant", "Answer 1")

    context = memory.build_context("c1")

    assert len(context.recent_messages) == 2
    assert context.compacted_messages == []


def test_memory_compacts_older_assistant_messages() -> None:
    memory = ConversationMemory(window_size=2, summary_ratio=1.0)
    memory.append("c1", "user", "Question 1")
    memory.append("c1", "assistant", "Sentence one. Sentence two. Sentence three.")
    memory.append("c1", "user", "Question 2")
    memory.append("c1", "assistant", "Answer 2")

    context = memory.build_context("c1")

    assert len(context.recent_messages) == 2
    assert context.compacted_messages[1].content == "Sentence one. Sentence two."


def test_memory_summarizes_when_compacted_context_is_large() -> None:
    memory = ConversationMemory(window_size=2, summary_ratio=0.01)
    memory.append("c1", "user", "Why was March abandon high?")
    memory.append("c1", "assistant", "Long answer. " * 100)
    memory.append("c1", "user", "Compare with January")
    memory.append("c1", "assistant", "Short answer")

    context = memory.build_context("c1")

    assert context.summary
    assert context.compacted_messages == []
