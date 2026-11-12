# AI Quiz Generator

This repository is the shared starting point for a terminal-based AI quiz generator. The first version is a Python layered modular monolith: Gemini creates quizzes, reusable application services run and grade them, and a terminal interface handles user interaction.

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
│   └── sample_quiz.json                # Valmira creates shared 10-question fixture
└── team/
    ├── valmira/README.md
    ├── stina/README.md
    └── flutura/README.md
```

The package directories and target modules are scaffolded now. Implementation and tests are intentionally left to the owners named above.

## Fixed architecture

| Layer | Responsibility | Dependency rule |
|---|---|---|
| Domain | `Question`, `Quiz`, `QuizResult` | No terminal, Gemini, or file-I/O imports |
| Application | Quiz generation, session state, scoring | Uses domain objects and the `AIProvider` abstraction; no `print()` or `input()` |
| Infrastructure | Gemini API, text-file input, result export | Implements external-provider and file operations |
| Presentation | Terminal UI and application assembly | Calls services; owns `print()` and `input()`; contains no prompts or scoring rules |

Use the Strategy pattern for `AIProvider`, constructor injection for `QuizGenerator`, and composition for quizzes and sessions. Do not add FastAPI, a web UI, a database, user accounts, analytics, or model training to the first version.

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
2. Valmira adds the `Question` and `Quiz` skeletons, coordinates the initial `QuizResult` shape with Stina, and creates `tests/sample_quiz.json` with exactly 10 complete questions.
3. Valmira pushes the shared starting commit. Everyone pulls it, installs the same dependencies, and verifies that the fixture can be loaded.
4. Work continues in parallel:
   - Valmira builds the provider and generator on `feature/ai-generator`.
   - Stina builds the session and grading engine on `feature/quiz-engine`.
   - Flutura builds the terminal flow and export on `feature/cli-export`.
5. Flutura initially uses a fake provider or fixture. During integration, `main.py` is switched to `GeminiProvider`, and all end-to-end tests are run.

Each person should edit owned files whenever possible. Cross-owner changes should be discussed first, especially changes to model fields or public method signatures.

## Definition of done

A user can enter a topic, paste lecture text ending with `END`, or load a `.txt` file. Gemini returns exactly 10 validated multiple-choice questions with A–D options. The terminal collects answers, displays the final score, and can export incorrect answers with the selected answer, correct answer, and explanation. Each of the three areas is independently tested.

