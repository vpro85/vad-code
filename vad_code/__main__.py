"""Точка входа"""
from vad_code.core.agent import Agent
from vad_code.config import settings


def run() -> None:
    print("🚀 AI-OS Bridge (Local Mode) запущен.")
    print(f"Подключение к {settings.lm_studio_url}")
    print(f"Рабочая директория: {settings.project_root}\n")

    agent = Agent()

    while True:
        try:
            user_input = input("Вы: ").strip()
        except EOFError:
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break

        agent.handle(user_input)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n\n👋 Выход из системы...")
