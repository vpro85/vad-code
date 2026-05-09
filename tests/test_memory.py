import pytest
from unittest.mock import MagicMock
from vad_code.core.memory import ConversationMemory
from vad_code.infrastructure.tokenizer import Tokenizer
from vad_code.config import settings


@pytest.fixture
def mock_tokenizer():
    tokenizer = MagicMock(spec=Tokenizer)
    # Default behavior: 1 token per character for simplicity in tests
    tokenizer.count_tokens.side_effect = lambda x: len(str(x))
    tokenizer.count_messages_tokens.side_effect = lambda msgs: sum(len(m['role']) + len(m['content']) for m in msgs)
    return tokenizer


@pytest.fixture
def memory(mock_tokenizer):
    system_prompt = "You are a helpful assistant"
    return ConversationMemory(tokenizer=mock_tokenizer, system_prompt=system_prompt)


def test_add_and_get_messages(memory):
    memory.add_message("user", "Hello!")
    memory.add_message("assistant", "Hi there!")

    messages = memory.get_messages()
    assert len(messages) == 3
    assert messages[0] == {"role": "system", "content": "You are a helpful assistant"}
    assert messages[1] == {"role": "user", "content": "Hello!"}
    assert messages[2] == {"role": "assistant", "content": "Hi there!"}


def test_reset(memory):
    memory.add_message("user", "Test")
    memory.reset()
    assert len(memory.history) == 0
    assert len(memory.get_messages()) == 1  # Only system prompt remains


def test_trim_by_message_count(memory, monkeypatch):
    # Set a small limit for testing
    monkeypatch.setattr(settings, "max_history_messages", 3)
    monkeypatch.setattr(settings, "max_context_tokens", 10000)  # High token limit to isolate message count test

    # Add 5 messages
    for i in range(5):
        memory.add_message("user", f"Msg {i}")

    memory.trim()

    # Should keep first message + (3-1) most recent = 3 messages total
    assert len(memory.history) == 3
    assert memory.history[0] == {"role": "user", "content": "Msg 0"}
    assert memory.history[1] == {"role": "user", "content": "Msg 3"}
    assert memory.history[2] == {"role": "user", "content": "Msg 4"}


def test_trim_by_tokens_pairs(memory, monkeypatch, mock_tokenizer):
    # Set a very small token limit to trigger trimming
    monkeypatch.setattr(settings, "max_history_messages", 100)
    monkeypatch.setattr(settings, "max_context_tokens", 20)

    # System prompt is "You are a helpful assistant" (28 chars/tokens in our mock)
    # So it's already over the limit of 20.

    memory.add_message("assistant", "Call tool X")
    memory.add_message("user", "OBSERVATION: Tool result")
    memory.add_message("user", "Final question")

    # Mock count_tokens to be consistent for the pair removal logic
    # The code calculates pair_tokens as sum of role and content tokens
    # Let's ensure it triggers the 'if total_tokens > settings.max_context_tokens'

    memory.trim()

    # It should have tried to remove the assistant + observation pair first
    # History was: [assistant, user(OBS), user]
    # After removing pair: [user]
    assert len(memory.history) == 1
    assert memory.history[0] == {"role": "user", "content": "Final question"}


def test_trim_by_tokens_fallback(memory, monkeypatch):
    monkeypatch.setattr(settings, "max_history_messages", 100)
    monkeypatch.setattr(settings, "max_context_tokens", 10)

    # Add messages that are NOT pairs of assistant + observation
    memory.add_message("user", "Msg 1")
    memory.add_message("user", "Msg 2")
    memory.add_message("user", "Msg 3")

    # Trigger trim - should remove oldest messages except the first one
    memory.trim()

    # It will keep removing until total <= 10 or only 1 message left
    # Since system prompt is already > 10, it will likely reduce history to just 1 message (the first one)
    assert len(memory.history) == 1
    assert memory.history[0] == {"role": "user", "content": "Msg 1"}
