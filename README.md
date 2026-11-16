# Система приёма лабораторных работ

Этапы А и Б лабораторной работы 1 и этап А лабораторной работы 2, траектория Python Core.

## Что реализовано

- пакет в `src`-layout с неизменяемым dataclass `Submission`;
- строгий разбор JSON/JSONL и валидация схемы;
- ISO-8601 timestamp с обязательной таймзоной;
- явная валидация AI-декларации (`used=true` требует непустого `description`);
- идемпотентный приём в памяти: дубликат (тот же id и тот же хеш) и конфликт (тот же id, другой хеш);
- CLI `lab-import import <file.jsonl>`, который продолжает работу после битых строк.
- синхронный контракт `Analyzer` и `AnalysisReport`;
- `LengthAnalyzer` и `TemplateAnalyzer`;
- JSONL- и in-memory-источники сдач;
- явный реестр фабрик анализаторов и `AnalysisService`.
- потоковый token-baseline сходства с 3-граммами и Jaccard;
- AST-представление с последовательной нормализацией имён;
- сравнение пар одного задания и top-k без self-match;
- отдельная отметка `same_student` для повторных версий;
- evidence с диапазонами исходного кода для token/AST и шаблонов;
- явный статус недостатка данных.

## Запуск

Windows PowerShell:

```text
python -m venv .venv
(если PowerShell: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)
.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m pip install pytest
lab-import import submissions.jsonl
python -m pytest -v
```
Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pip install pytest
lab-import import submissions.jsonl
python -m pytest -v
```

## Отчёт CLI

```json
{"accepted": 2, "duplicate": 1, "errors": [{"code": "invalid_json", "field": null, "line": 2, "message": "invalid JSON: Expecting property name enclosed in double quotes"}]}
```

## Структура

- `models` — Submission, AiDeclaration;

- `analysis` — Assignment, Evidence, AnalysisReport, Analyzer и AnalysisContext;

- `analyzers` — LengthAnalyzer и TemplateAnalyzer;

- `sources` — SubmissionSource, JsonlSubmissionSource, InMemorySubmissionSource и контекст заданий;

- `registry` — AnalyzerRegistry и default_registry;

- `analysis_service` — AnalysisService, выбирающий анализатор через реестр.

- `similarity` — token/AST-признаки, сравнение пар и top-k-кандидаты.

- `errors` — IntakeIssue (code/field/message), IntakeError и потомки (ParseError, ValidationError, ConflictError);

- `parser` — разбор JSONL-строки и валидация схемы, расчёт content_hash;

- `repository` — протокол SubmissionRepository + in-memory реализация;

- `service` — IntakeService (политика дубликатов/конфликтов), AcceptanceResult;

- `cli` — argparse, import_jsonl, печать JSON-отчёта.

Доменный слой не читает stdin и не ходит в HTTP. Репозиторий задан протоколом, поэтому в ЛР 3 in-memory реализация заменится на SQLite без изменения парсинга и правил приёма.

## Лабораторная работа 2, этап А

Token-baseline исключает комментарии и служебные токены, строит множество
токеновых 3-грамм и вычисляет Jaccard. Если объединение признаков пустое,
результат имеет `score=null` и статус `insufficient_evidence`. AST-метод
нормализует имена в порядке первого появления; это уменьшает влияние
переименования, но не доказывает происхождение решений. Индекс полного корпуса
на этом этапе не создаётся: потоковый источник уменьшает память чтения, однако
поиск top-k хранит переданный набор кандидатов.
Повторная версия того же студента не отбрасывается, но помечается
`same_student=true`; сдачи другого задания исключаются. Для корректного
прямого сравнения две сдачи должны иметь один `assignment_id`.

## Ограничения нормализации AST:
- порядок первого появления важен: `a, b` и `b, a` дадут разные `name_0`/`name_1`,
  даже если смысл тот же;
- встроенные имена (`print`, `len`) тоже нормализуются — перекрытие встроенного
  имени и обычное использование могут совпасть;
- атрибуты (`obj.attr`) и строковые литералы (`"hello"` vs `"world"`) не
  нормализуются — различаются;
- нормализуются `Name`, `arg`, `FunctionDef`/`AsyncFunctionDef`/`ClassDef`;
  имена в других конструкциях (например, ключевые аргументы вызова) — нет;
- позиции (`lineno`/`col_offset`) выбрасываются в `_freeze_ast`, чтобы
  форматирование не влияло на сравнение структуры.

## Расход памяти:
- `CodeFeatures`: `frozenset` 3-грамм — O(число токенов) на сдачу (каждая
  3-грамма — кортеж из 3 строк); `template_lines` — O(число шаблонных строк);
- `AstFeatures`: кортеж `_freeze_ast` — O(число узлов AST) на сдачу;
- `top_k_similar` строит `SimilarityResult` для всех кандидатов (O(n) на
  переданный набор), потом сортирует — полный перебор, память O(n) на набор;
- полный индекс корпуса не создаётся; потоковое чтение уменьшает память
  чтения, но не делает полный индекс константным по памяти.

Корпус 30 сдач / 40 пар и split dev/test по `family_id` создаётся к этапу Б
; на этапе А проверено на синтетических тестах.

## Формат входных данных

```json
{
  "submission_id": "sub-1",
  "assignment_id": "lab-1",
  "student_id": "student-1",
  "submitted_at": "2026-11-12T12:00:00+03:00",
  "text": "Explanation",
  "code": "print('ok')",
  "ai_declaration": {"used": false, "description": ""}
}
```

Если `used` равно `true`, `description` не должно быть пустым. Повторяющийся идентификатор с тем же каноническим содержимым является дубликатом, а с другим содержимым — конфликтом.

## Проверка воспроизводимости

Проверено, что пакет устанавливается как обычный (`pip install`)
в отдельном venv **вне** исходного каталога, и CLI работает оттуда.

### Команды

```powershell
mkdir E:\clean_test
cd E:\clean_test
python -m venv venv
venv\Scripts\Activate.ps1
pip install E:\Python_мага\main_lab
lab-import --help
python -c "import lab_system; print(lab_system.__file__)"
```

### Результат

```bash
PS E:\Python_мага\main_lab> cd E:\clean_test
PS E:\clean_test> python -m venv venv
PS E:\clean_test> venv\Scripts\Activate.ps1
(venv) PS E:\clean_test> pip install E:\Python_мага\main_lab
Processing e:\python_мага\main_lab
  Installing build dependencies ... done
  Getting requirements to build wheel ... done
  Preparing metadata (pyproject.toml) ... done
  Building wheel for lab-submission-system (pyproject.toml) ... done
  Created wheel for lab-submission-system: filename=lab_submission_system-0.1.0-py3-none-any.whl size=6599 sha256=9bed36d1df8ff85eede22ac03f3064873b3a598610f8e5e3f9cb9f6cfc6fc39c
  Stored in directory: ****************************************************************************
Successfully built lab-submission-system
Installing collected packages: lab-submission-system
Successfully installed lab-submission-system-0.1.0

[notice] A new release of pip available: 22.3.1 -> 26.3
[notice] To update, run: python.exe -m pip install --upgrade pip
(venv) PS E:\clean_test> lab-import --help
usage: lab-import [-h] {import} path

Import laboratory submissions from JSONL

positional arguments:
  {import}
  path

options:
  -h, --help  show this help message and exit
(venv) PS E:\clean_test> python -c "import lab_system; print(lab_system.__file__)"
E:\clean_test\venv\lib\site-packages\lab_system\__init__.py
```

## Тесты

```powershell
python -m pytest -v
```
42 теста (14 этап А ЛР 1 + 15 этап Б ЛР 1 + 13 этап А ЛР 2)

- `Покрыто:` 
### Этап А 1 лаборатная 
валидный импорт, неизменность входа (deepcopy), timestamp без зоны, пустой student_id, неверный тип student_id, лишнее поле, битый JSON, дубликат, конфликт, продолжение импорта после битой строки, AI-декларация (5 случаев: не объект, лишнее поле, used не bool, description не строка, used=true без описания), ручная проверка: пакет устанавливается в чистое окружение

### Этап Б 1 лаборатная 
analyzer_id + analyzer_version для Length и Template; LengthAnalyzer — score=None, similarity=None, rubric_feedback с числами, evidence с диапазоном; TemplateAnalyzer — similarity=1.0 + точная строка + «разрешённое», нет совпадений - 0.0, (), «не найдено»; реестр + AnalysisService без ветвления; оба источника дают тот же Submission; файл закрыт при early stop и при ошибке; номер строки в ошибке JSONL; unknown_assignment + field="assignment_id"; третий анализатор без правки AnalysisService; ошибка анализатора пробрасывается; реестр: неизвестный create - KeyError, дубликат register - ValueError.

### Этап А 2 лаборатная
token: комментарии/служебные исключены; точная копия - 1.0; пустые признаки - None;
SyntaxError/TokenError - insufficient_evidence + error; AST: нормализация имён
(переменные, функции) - 1.0, разные структуры - 0.0; шаблон - template_only +
evidence + «не нарушение»; top-k: self/другое задание исключены, same_student
помечен, сортировка (0.0 выше None), bound; unknown method / negative top_k -
ValueError; разные assignment_id - ValueError.