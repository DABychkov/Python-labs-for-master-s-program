# Система приёма лабораторных работ

Этап А лабораторной работы 1, траектория Python Core.

## Что реализовано

- пакет в `src`-layout с неизменяемым dataclass `Submission`;
- строгий разбор JSON/JSONL и валидация схемы;
- ISO-8601 timestamp с обязательной таймзоной;
- явная валидация AI-декларации (`used=true` требует непустого `description`);
- идемпотентный приём в памяти: дубликат (тот же id и тот же хеш) и конфликт (тот же id, другой хеш);
- CLI `lab-import import <file.jsonl>`, который продолжает работу после битых строк.

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

- `errors` — IntakeIssue (code/field/message), IntakeError и потомки (ParseError, ValidationError, ConflictError);

- `parser` — разбор JSONL-строки и валидация схемы, расчёт content_hash;

- `repository` — протокол SubmissionRepository + in-memory реализация;

- `service` — IntakeService (политика дубликатов/конфликтов), AcceptanceResult;

- `cli` — argparse, import_jsonl, печать JSON-отчёта.

Доменный слой не читает stdin и не ходит в HTTP. Репозиторий задан протоколом, поэтому в ЛР 3 in-memory реализация заменится на SQLite без изменения парсинга и правил приёма.

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
  Stored in directory: C:\Users\Dmitry\AppData\Local\Temp\pip-ephem-wheel-cache-frstoytp\wheels\bd\34\66\0496370e138e84b9d1d28894a9d4b187e6558c6c32aa7f9bfa
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

- `Покрыто:` валидный импорт, неизменность входа (deepcopy), timestamp без зоны, пустой student_id, неверный тип student_id, лишнее поле, битый JSON, дубликат, конфликт, продолжение импорта после битой строки, AI-декларация (5 случаев: не объект, лишнее поле, used не bool, description не строка, used=true без описания), ручная проверка: пакет устанавливается в чистое окружение