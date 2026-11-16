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
- ЛР 2 этап А: реализовал `similarity.py` — `CodeFeatures`/`AstFeatures`/`SimilarityResult`;
- `extract_code_features`: `tokenize` с фильтром `NAME`/`NUMBER`/`STRING`/`OP`, 3-граммы, `template_lines`;
- `extract_ast_features`: `ast.parse`, `NameNormalizer` (`Name`, `arg`, `FunctionDef`/`AsyncFunctionDef`/`ClassDef`), `_freeze_ast` без позиций;
- `compare_submissions`: проверка `assignment_id`, `template_evidence`, token - `_jaccard`, ast - `_structure_similarity`, `_similarity_evidence`, `same_student`;
- `top_k_similar`: фильтр self/другого задания, сортировка с `None` в конце (исправил `score or -1.0` - `score if score is not None else -1.0`).

## Помощь ИИ

- Черновики сигнатур, docstring'ов, скелета модулей.
- Подсказки по синтаксису: `Protocol`, `@dataclass(frozen=True)`, `argparse` с `type=Path`, `pathlib`, `utf-8-sig`.
- Черновики `parametrize`-тестов и фабрики `payload(**changes)`.
- Формулировки сообщений об ошибках, тексты.
- Объяснения непонятных мест (`Protocol`, `deepcopy`, `utf-8-sig`).
- Черновики `Protocol` (`Analyzer`, `AnalysisContext`, `SubmissionSource`), `AnalyzerRegistry`, `AnalysisService`.
- Подсказки по `yield from`, `@dataclass(frozen=True)` для `Evidence`/`AnalysisReport`, `contextmanager`-паттерн.
- Черновики тестов этапа Б
- Черновики `CodeFeatures`/`AstFeatures`/`SimilarityResult`, `_jaccard`, `_freeze_ast`, `_similarity_evidence`.
- Подсказки по `tokenize.generate_tokens(io.StringIO(...).readline)`, `ast.NodeTransformer`, `visit_FunctionDef`/`visit_ClassDef`, `frozenset(zip(...))`.
- Черновики тестов ЛР 2.
- Объяснения `score or -1.0` (баг для `0.0`), `same_student`, ограничений нормализации

## Проверено вручную

- `python -m pytest -v` — все тесты проходят; ручные сценарии через `lab-import` дают ожидаемый JSON.
- Схема и коды ошибок сверены с требованиями ЛР 1.
- «Битая строка не останавливает импорт» — интеграционный тест + ручной файл.
- «Конфликт не перезаписывает» — `raise` до `save`, тест `count == 1`.
- «Вход не изменяется» — `deepcopy` + `raw == before`.
- Этап Б: `python -m pytest tests/test_analysis.py -v` — 15 passed;
- ЛР 2: `python -m pytest tests/test_similarity.py -v` — 14 passed.