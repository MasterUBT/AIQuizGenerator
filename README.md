# AI Quiz Generator

This repository contains a Python AI quiz generator with terminal and local browser interfaces. Gemini creates quizzes, while reusable application services run and grade them.

## Run the application

Install dependencies once:

```bash
make setup
```

Copy `.env.example` to `.env`, add `GEMINI_API_KEY`, and start live generation:

```bash
make run
```

Live mode uses `gemini-3.6-flash` first and automatically tries
`gemini-3.8-flash` after a timeout, rate limit, temporary server failure, or
invalid model response. Each model has a 20-second request deadline by default.
Configure the behavior with `GEMINI_MODEL`, `GEMINI_FALLBACK_MODEL`, and
`GEMINI_TIMEOUT_SECONDS`, or the equivalent `--model`, `--fallback-model`, and
`--timeout` command-line options.

Run the deterministic offline fixture explicitly with:

```bash
make practice
```

## Run the browser interface

After completing `make setup` and adding `GEMINI_API_KEY` to `.env`, start the
local web server:

```bash
make web
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser. You can
generate a quiz from a topic, pasted lecture, or UTF-8 `.txt` file. Submit all
10 answers to see the score and explanations, then download the incorrect
answers as a Markdown review file. The API key remains on the Python server and
is never sent to the browser.

Press `Control+C` in the terminal to stop the server. Run only the browser tests
with:

```bash
make test-web
```

Run all automated tests with:

```bash
make test
```

## Team work plans

Each person has a separate, detailed checklist and a clearly defined ownership boundary:

- [Valmira — domain models and AI question generator](team/valmira/README.md)
- [Stina — quiz engine and grading](team/stina/README.md)
- [Flutura — terminal flow, input, export, and integration](team/flutura/README.md)

The name-to-role mapping follows the order in the project request. If the team changes the mapping, update both these links and the ownership table before implementation begins.

## Initial project structure

```text
AIQuizGenerator/
├── README.md
├── .env.example
├── requirements.txt
├── ai_quiz_generator/
│   ├── __init__.py
│   ├── main.py                         # Flutura
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── question.py                 # Valmira
│   │   ├── quiz.py                     # Valmira
│   │   └── quiz_result.py              # Stina
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── provider.py                 # Valmira
│   │   └── gemini_provider.py          # Valmira
│   ├── services/
│   │   ├── __init__.py
│   │   ├── quiz_generator.py           # Valmira
│   │   ├── quiz_session.py             # Stina
│   │   └── scoring.py                  # Stina, only if useful
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── input_reader.py             # Flutura
│   │   └── quiz_exporter.py            # Flutura
│   └── cli/
│       ├── __init__.py
│       └── terminal_ui.py              # Flutura
├── tests/
│   └── sample_quiz.json                # Stina owns shared 10-question fixture
└── team/
    ├── valmira/README.md
    ├── stina/README.md
    └── flutura/README.md
```

The package directories were originally scaffolded around these ownership boundaries. The implementation and automated tests are now present; the team work plans remain as the historical task breakdown.

## Fixed architecture

| Layer | Responsibility | Dependency rule |
|---|---|---|
| Domain | `Question`, `Quiz`, `QuizResult` | No terminal, Gemini, or file-I/O imports |
| Application | Quiz generation, session state, scoring | Uses domain objects and the `AIProvider` abstraction; no `print()` or `input()` |
| Infrastructure | Gemini API, text-file input, result export | Implements external-provider and file operations |
| Presentation | Terminal and local browser UI, plus application assembly | Calls services; contains no AI prompts or scoring rules |

Use the Strategy pattern for `AIProvider`, constructor injection for `QuizGenerator`, and composition for quizzes and sessions. The browser UI is a thin Flask presentation layer and does not add a database, user accounts, analytics, or model training.

## Shared contracts

All three team members must confirm these names and fields before parallel implementation:

```python
Question:
    id: int
    text: str
    options: dict[str, str]       # exactly A, B, C, D
    correct_answer: str           # A, B, C, or D
    explanation: str

Quiz:
    topic: str
    questions: list[Question]     # exactly 10

QuizResult:
    score: int
    total: int
    answers: dict[int, str]       # question ID -> selected choice
    wrong_question_ids: list[int]
```

Required public methods:

```python
QuizGenerator.generate(source: str, mode: str) -> Quiz
QuizSession(quiz: Quiz)
QuizSession.submit_answer(question_id: int, choice: str) -> None
QuizSession.finish() -> QuizResult
QuizExporter.export_wrong_answers(
    quiz: Quiz, result: QuizResult, path: str
) -> None
```

`mode` is `"topic"` or `"lecture"`. Public contract changes require a short team review and updates to this README and every affected work plan.

## Parallel-work kickoff

1. All three members confirm the architecture, contracts, and one shared Python version.
2. Valmira adds the `Question` and `Quiz` skeletons. Stina implements the agreed initial `QuizResult` shape and creates `tests/sample_quiz.json` with exactly 10 complete questions.
3. Valmira and Stina review the shared models and fixture together, then publish the shared starting commit. Everyone pulls it, installs the same dependencies, and verifies that the fixture can be loaded.
4. Work continues in parallel:
   - Valmira builds the provider and generator on `feature/ai-generator`.
   - Stina builds the session and grading engine on `feature/quiz-engine`.
   - Flutura builds the terminal flow and export on `feature/cli-export`.
5. Flutura initially uses a fake provider or fixture. During integration, `main.py` is switched to `GeminiProvider`, and all end-to-end tests are run.

Each person should edit owned files whenever possible. Cross-owner changes should be discussed first, especially changes to model fields or public method signatures.

To balance the workload, Stina also owns the shared fixture and the automated contract tests covering the domain models and quiz-session boundary. Valmira tests provider and generator behavior; Flutura tests the CLI, file operations, and end-to-end assembly.

## Definition of done

A user can enter a topic, paste lecture text ending with `END`, or load a `.txt` file. Gemini returns exactly 10 validated multiple-choice questions with A–D options. The terminal collects answers, displays the final score, and can export incorrect answers with the selected answer, correct answer, and explanation. Each of the three areas is independently tested.

