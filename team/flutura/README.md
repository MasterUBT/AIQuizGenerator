# Flutura — Terminal Flow, Input, Export, and Integration

## Goal

Build the complete terminal experience and application assembly while keeping user-interface and file-I/O concerns out of the domain and application logic.

## Owned files

- `ai_quiz_generator/cli/terminal_ui.py`
- `ai_quiz_generator/infrastructure/input_reader.py`
- `ai_quiz_generator/infrastructure/quiz_exporter.py`
- `ai_quiz_generator/main.py`
- CLI, input-reader, exporter, and assembly tests

Use Valmira's generator and Stina's quiz-session public methods. Do not duplicate their prompt-generation, validation, session, or scoring logic in the CLI.

## Work checklist

### 1. Develop against fixtures first

- [ ] Confirm the shared contracts and expected errors with Valmira and Stina.
- [ ] Pull and load the shared 10-question fixture.
- [ ] Use a fake provider or fixture-backed generator until Gemini integration is ready.
- [ ] Create a sample `QuizResult` for exporter and display tests.

### 2. Input and terminal flow

- [ ] Add a menu for topic, pasted lecture text, `.txt` file, and exit.
- [ ] Read pasted text until the user enters an explicit `END` line.
- [ ] Read UTF-8 `.txt` files and report missing, unreadable, or empty files clearly.
- [ ] Reject empty topic or lecture input and let the user retry.
- [ ] Display each question with its A–D options.
- [ ] Accept A–D answers, show friendly validation messages, and retry invalid input.
- [ ] Submit answers through `QuizSession.submit_answer()`.
- [ ] Display final score as points and percentage.
- [ ] Avoid embedding AI prompts or scoring rules in terminal code.

### 3. Wrong-answer export

- [ ] Implement `QuizExporter.export_wrong_answers(quiz, result, path)`.
- [ ] Include question text, selected answer, correct answer, and explanation for every mistake.
- [ ] Produce readable Markdown or TXT output.
- [ ] Handle paths and file-write errors with useful messages.
- [ ] Do not export API keys or raw provider responses.

### 4. Application assembly

- [ ] Construct `GeminiProvider`, `QuizGenerator`, `QuizSession`, and `QuizExporter` in `main.py`.
- [ ] Keep `main.py` limited to dependency construction and startup.
- [ ] Replace the fake provider with `GeminiProvider` during integration.
- [ ] Verify topic, pasted-text, file-input, invalid-input, and export flows end to end.

### 5. Tests

- [ ] Test all four menu choices with mocked input/output.
- [ ] Test multiline input and the `END` marker.
- [ ] Test valid, missing, unreadable, and empty `.txt` files.
- [ ] Test invalid answer retries.
- [ ] Test score and percentage display.
- [ ] Test exported content for zero, one, and multiple wrong answers.
- [ ] Test assembly with fakes so automated tests never require a real API call.

## Integration contracts

```python
quiz = generator.generate(source, mode)
session = QuizSession(quiz)
session.submit_answer(question_id, choice)
result = session.finish()
exporter.export_wrong_answers(quiz, result, path)
```

For `.txt` files, read their content and call the generator with `mode="lecture"`. The provider should receive content, not a file path.

## Deliverable

The terminal supports topic, pasted lecture, and text-file inputs; presents all 10 questions; displays the score; and optionally exports incorrect answers. It first works with fixtures and then with the real generator without restructuring the CLI.

Suggested branch: `feature/cli-export`.

