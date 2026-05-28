from unittest.mock import MagicMock, patch
import pytest
from vad_code.infrastructure.tokenizer import Tokenizer


@pytest.fixture
def mock_tokenizer():
    """
    Фикстура для мока AutoTokenizer.
    """
    with patch('vad_code.infrastructure.tokenizer.AutoTokenizer.from_pretrained') as mock_from_pretrained:
        # Создаем мок объекта токенизатора
        mock_tok_instance = MagicMock()
        # Настраиваем метод encode, чтобы он возвращал список длиной в длину строки (для простоты)
        # В реальности токены != символы, но для теста логики достаточно
        mock_tok_instance.encode.side_effect = lambda text, add_special_tokens=False: [f"token_{i}" for i in
                                                                                       range(len(text))]

        mock_from_pretrained.return_value = mock_tok_instance
        yield mock_tok_instance


def test_tokenizer_init(mock_tokenizer):
    # Проверяем, что токенизатор инициализируется и вызывает from_pretrained
    tokenizer = Tokenizer()
    assert tokenizer.tokenizer == mock_tokenizer


def test_count_tokens(mock_tokenizer):
    tokenizer = Tokenizer()
    text = "Hello world"
    # Согласно нашему side_effect, количество токенов будет равно длине строки (11)
    count = tokenizer.count_tokens(text)
    assert count == len(text)
    mock_tokenizer.encode.assert_called_with(text, add_special_tokens=False)


def test_count_messages_tokens(mock_tokenizer):
    tokenizer = Tokenizer()
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ]
    # Расчет: 
    # 'user' (4) + 'Hello' (5) = 9
    # 'assistant' (9) + 'Hi there!' (9) = 18
    # Итого: 27
    expected_count = len("user") + len("Hello") + len("assistant") + len("Hi there!")
    count = tokenizer.count_messages_tokens(messages)
    assert count == expected_count
