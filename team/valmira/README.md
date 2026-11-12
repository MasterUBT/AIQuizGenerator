# Valmira — Domain Models and AI Question Generator

## Goal

Build and validate the quiz domain models, define the AI-provider boundary, and turn Gemini JSON into a valid 10-question `Quiz` without any terminal input or output.

## Owned files

- `ai_quiz_generator/domain/question.py`
- `ai_quiz_generator/domain/quiz.py`
- `ai_quiz_generator/ai/provider.py`
- `ai_quiz_generator/ai/gemini_provider.py`
- `ai_quiz_generator/services/quiz_generator.py`
- Model, provider, and generator tests

Stina owns `domain/quiz_result.py`, the shared fixture, and cross-layer domain/session contract tests. Coordinate the initial model fields with her, but do not change her implementation silently.

## Work checklist

### 1. Shared starting point

- [ ] Confirm the shared fields and public methods in the root README with Stina and Flutura.
- [ ] Agree on the team Python version and Gemini SDK dependency.
- [ ] Add `Question` and `Quiz` class skeletons.
- [ ] Coordinate the initial `QuizResult` skeleton with Stina.
- [ ] Review Stina's `tests/sample_quiz.json` and confirm that it satisfies `Question` and `Quiz` validation.
- [ ] Review and publish the shared starting point with Stina before feature work begins.

### 2. Domain validation

- [ ] Validate that every question has a positive unique ID, nonempty text, and nonempty explanation.
- [ ] Require exactly the option keys `A`, `B`, `C`, and `D`, with nonempty values.
- [ ] Require `correct_answer` to be one of `A`, `B`, `C`, or `D`.
- [ ] Require a generated quiz to contain exactly 10 questions.
- [ ] Keep domain modules independent of Gemini, terminal I/O, and file I/O.

### 3. AI provider and generator

- [ ] Define an `AIProvider` abstraction that returns structured quiz data.
- [ ] Implement `GeminiProvider` without leaking Gemini-specific code into domain or CLI modules.
- [ ] Ask Gemini for strict JSON matching the agreed fields.
- [ ] Implement `QuizGenerator.generate(source, mode)` for `topic` and `lecture` modes.
- [ ] Reject empty sources and unsupported modes with clear exceptions.
- [ ] Parse provider output into domain objects and run all validations.
- [ ] Handle malformed JSON, invalid fields, wrong question counts, timeouts, and provider failures.
- [ ] Keep API keys in `GEMINI_API_KEY`; never commit a real key.

### 4. Tests

- [ ] Load and parse the shared fixture successfully.
- [ ] Test missing or extra option keys.
- [ ] Test invalid correct-answer values.
- [ ] Test duplicate IDs and fewer or more than 10 questions.
- [ ] Test malformed provider responses and provider failures.
- [ ] Test both supported generation modes with a fake provider.

## Integration contract

```python
QuizGenerator.generate(source: str, mode: str) -> Quiz
```

The generator receives its provider through dependency injection. It must not call `input()` or `print()`. Flutura should be able to replace a fake provider with `GeminiProvider` in `main.py` without changing terminal flow, and Stina should receive an ordinary validated `Quiz`.

## Deliverable

This call returns a validated quiz with exactly 10 questions and performs no terminal interaction:

```python
quiz = generator.generate("Python OOP", "topic")
```

Suggested branch: `feature/ai-generator`.

