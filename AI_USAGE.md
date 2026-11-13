# Использование ИИ

## Моя работа

- Разобрал ТЗ ЛР 1 и памятку `Submission`, выделил поля и правила валидации.
- Спроектировал структуру пакета (`models`, `errors`, `parser`, `repository`, `service`, `cli`) и границы слоёв.
- Реализовал валидацию (`parse_submission`, `_parse_ai_declaration`), канонизацию и `content_hash`.
- Реализовал `IntakeService.accept`: дубликат по хешу, конфликт до `save`.
- Написал CLI `import_jsonl`/`main`, настроил `src`-layout и `pip install -e .`.
- Прогнал тесты и ручные сценарии через CLI, сверил вывод с ожидаемым.
- Этап Б: реализовал `AnalysisReport`/`Evidence`/`Assignment`/`AnalysisContext`/`Analyzer` (Protocol);
- реализовал `LengthAnalyzer`, `TemplateAnalyzer` (точные строки, `similarity`, «разрешённое»), `AnalyzerRegistry` и `AnalysisService` без ветвления;
- реализовал `JsonlSubmissionSource` (контекстный менеджер, `utf-8-sig`, номер строки в ошибке) и `InMemorySubmissionSource`;
- реализовал `InMemoryAnalysisContext` (задания `Assignment`, `unknown_assignment`);
- добавил третий `_ThirdAnalyzer` для теста расширяемости;
- прогнал тесты этапа Б (15), ручные сценарии, проверку установки в чистом venv.

## Помощь ИИ

- Черновики сигнатур, docstring'ов, скелета модулей.
- Подсказки по синтаксису: `Protocol`, `@dataclass(frozen=True)`, `argparse` с `type=Path`, `pathlib`, `utf-8-sig`.
- Черновики `parametrize`-тестов и фабрики `payload(**changes)`.
- Формулировки сообщений об ошибках, тексты.
- Объяснения непонятных мест (`Protocol`, `deepcopy`, `utf-8-sig`).
- Черновики `Protocol` (`Analyzer`, `AnalysisContext`, `SubmissionSource`), `AnalyzerRegistry`, `AnalysisService`.
- Подсказки по `yield from`, `@dataclass(frozen=True)` для `Evidence`/`AnalysisReport`, `contextmanager`-паттерн.
- Черновики тестов этапа Б

## Проверено вручную

- `python -m pytest -v` — все тесты проходят; ручные сценарии через `lab-import` дают ожидаемый JSON.
- Схема и коды ошибок сверены с требованиями ЛР 1.
- «Битая строка не останавливает импорт» — интеграционный тест + ручной файл.
- «Конфликт не перезаписывает» — `raise` до `save`, тест `count == 1`.
- «Вход не изменяется» — `deepcopy` + `raw == before`.
- Этап Б: `python -m pytest tests/test_analysis.py -v` — 15 passed;