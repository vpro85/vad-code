"""
Модуль управления бэкапами и историей изменений для системы Undo/Redo.
"""
import shutil
from pathlib import Path
from typing import Optional

from vad_code.infrastructure.logger import log


class ChangeRecord:
    """Запись об изменении файла."""

    def __init__(self, file_path: str, backup_path: str, operation: str):
        self.file_path = file_path
        self.backup_path = backup_path
        self.operation = operation

    def __repr__(self) -> str:
        return f"ChangeRecord(file={self.file_path}, op={self.operation})"


class BackupManager:
    """
    Управляет созданием бэкапов перед изменениями файлов.
    Поддерживает стек Undo и Redo.
    """

    def __init__(self, backup_dir: str = ".vad_backups"):
        self.backup_dir = Path(backup_dir)
        self.undo_stack: list[ChangeRecord] = []
        self.redo_stack: list[ChangeRecord] = []
        self._max_undo_steps = 20  # Лимит истории

    def create_backup(self, file_path: str, operation: str = "write") -> Optional[ChangeRecord]:
        """
        Создает бэкап файла перед изменением.
        
        Args:
            file_path: Путь к файлу, который будет изменен.
            operation: Тип операции (write, delete, move и т.д.).
            
        Returns:
            ChangeRecord если бэкап создан, иначе None.
        """
        target = Path(file_path)
        
        # Если файл не существует (например, перед удалением или созданием нового), бэкап не нужен
        if not target.exists():
            return None

        try:
            # Создаем директорию для бэкапов, если нет
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Генерируем имя файла бэкапа
            backup_name = f"{target.name}.bak_{id(self)}_{len(self.undo_stack)}"
            backup_path = self.backup_dir / backup_name
            
            # Копируем файл, исключая служебные директории
            if target.is_dir():
                shutil.copytree(
                    target, 
                    backup_path, 
                    ignore=shutil.ignore_patterns(
                        '.vad_backups', 
                        '.git', 
                        '__pycache__', 
                        'htmlcov', 
                        '.pytest_cache',
                        'node_modules',
                        '.venv',
                        'venv',
                        'env'
                    )
                )
            else:
                shutil.copy2(target, backup_path)
            
            record = ChangeRecord(
                file_path=str(target.resolve()),
                backup_path=str(backup_path.resolve()),
                operation=operation
            )
            
            self.undo_stack.append(record)
            
            # Ограничиваем размер стека
            if len(self.undo_stack) > self._max_undo_steps:
                self.undo_stack.pop(0)
                
            log.debug("📦 Backup created: %s -> %s", target, backup_path)
            return record
            
        except Exception as e:
            log.error("❌ Failed to create backup for %s: %s", target, e)
            return None

    def undo(self) -> Optional[str]:
        """
        Отменяет последнее изменение.
        
        Returns:
            Сообщение о результате операции.
        """
        if not self.undo_stack:
            return "Нет изменений для отмены."

        record = self.undo_stack.pop()
        target = Path(record.file_path)
        backup = Path(record.backup_path)

        try:
            # Сначала создаем бэкап ТЕКУЩЕГО состояния для Redo (до восстановления)
            redo_backup_name = f"{target.name}.redo_{len(self.redo_stack)}"
            redo_backup_path = self.backup_dir / redo_backup_name
            
            if target.exists():
                if target.is_dir():
                    shutil.copytree(
                        target, 
                        redo_backup_path, 
                        ignore=shutil.ignore_patterns(
                            '.vad_backups', 
                            '.git', 
                            '__pycache__', 
                            'htmlcov', 
                            '.pytest_cache',
                            'node_modules',
                            '.venv',
                            'venv',
                            'env'
                        )
                    )
                else:
                    shutil.copy2(target, redo_backup_path)
            
            # Теперь восстанавливаем файл из бэкапа
            if not target.exists():
                # Файл был удален
                if backup.is_dir():
                    shutil.copytree(backup, target)
                else:
                    shutil.copy2(backup, target)
                log.info("♻️ Restored deleted file: %s", target)
            else:
                # Файл существует, перезаписываем его содержимым из бэкапа
                if target.is_dir():
                    shutil.rmtree(target)
                    shutil.copytree(backup, target)
                else:
                    shutil.copy2(backup, target)
                log.info("♻️ Restored file: %s", target)

            # Добавляем запись в стек Redo
            redo_record = ChangeRecord(
                file_path=record.file_path,
                backup_path=str(redo_backup_path.resolve()),
                operation="redo"
            )
            self.redo_stack.append(redo_record)

            return f"✅ Отменено: {record.operation} для {target.name}"

        except Exception as e:
            log.error("❌ Failed to undo: %s", e)
            # Возвращаем запись в стек, если что-то пошло не так
            self.undo_stack.append(record)
            return f"❌ Ошибка при отмене: {e}"

    def redo(self) -> Optional[str]:
        """
        Повторяет отмененное изменение.
        
        Returns:
            Сообщение о результате операции.
        """
        if not self.redo_stack:
            return "Нет изменений для повтора."

        record = self.redo_stack.pop()
        target = Path(record.file_path)
        backup = Path(record.backup_path)

        try:
            # Восстанавливаем состояние из Redo-бэкапа
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            
            if backup.is_dir():
                shutil.copytree(backup, target)
            else:
                shutil.copy2(backup, target)
            
            log.info("🔁 Redo applied: %s", target)
            
            # Возвращаем в Undo стек
            self.undo_stack.append(record)
            
            return f"✅ Повторено: изменение для {target.name}"

        except Exception as e:
            log.error("❌ Failed to redo: %s", e)
            self.redo_stack.append(record)
            return f"❌ Ошибка при повторе: {e}"

    def get_history(self) -> list[dict]:
        """Возвращает историю изменений."""
        return [
            {
                "file": rec.file_path,
                "operation": rec.operation,
                "backup": rec.backup_path
            }
            for rec in self.undo_stack
        ]

    def clear(self) -> None:
        """Очищает историю."""
        self.undo_stack.clear()
        self.redo_stack.clear()
        log.info("🧹 История изменений очищена.")


# Глобальный экземпляр
backup_manager = BackupManager()
