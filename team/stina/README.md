# Stina — Quiz Engine and Grading

## Goal

Build reusable quiz-session state and deterministic grading. The engine receives a `Quiz`, records one valid choice per question, and returns an accurate `QuizResult` without terminal or Gemini dependencies.

## Owned files

- `ai_quiz_generator/domain/quiz_result.py`
- `ai_quiz_generator/services/quiz_session.py`
- `ai_quiz_generator/services/scoring.py` if separate scoring improves clarity
- `tests/sample_quiz.json` as the shared 10-question development fixture
- Shared domain/session contract tests
- Quiz-session, validation, and scoring tests

Valmira owns `Question` and `Quiz`. Import and use those models without changing their public fields unless the whole team agrees.

## Work checklist

### 1. Shared starting point

- [ ] Confirm `Question`, `Quiz`, and `QuizResult` fields and all public methods with Valmira and Flutura.
- [ ] Review the initial `QuizResult` skeleton with Valmira, then take ownership of its implementation.
- [ ] Create `tests/sample_quiz.json` with exactly 10 complete questions, unique IDs, and A–D options.
- [ ] Verify with Valmira that the fixture satisfies the agreed `Question` and `Quiz` validations.
- [ ] Review and publish the shared starting point with Valmira before feature work begins.

### 2. Result model and session state

- [ ] Implement `QuizResult` with `score`, `total`, `answers`, and `wrong_question_ids`.
- [ ] Implement `QuizSession(quiz)` without mutating the supplied quiz.
- [ ] Track submitted answers by question ID.
- [ ] Validate that question IDs exist in the quiz.
- [ ] Normalize or reject invalid choices consistently; only A–D are valid.
- [ ] Prevent duplicate submissions for the same question.
- [ ] Define clear behavior when `finish()` is called before all questions are answered.
- [ ] Prevent unsafe or inconsistent state after the session is finished.

### 3. Scoring

- [ ] Compare recorded choices directly with each question's `correct_answer`.
- [ ] Calculate `score` and `total` accurately.
- [ ] Return wrong question IDs in quiz order.
- [ ] Keep scoring deterministic; do not call Gemini to grade responses.
- [ ] Keep all quiz logic free of `input()` and `print()`.

### 4. Tests

- [ ] Test all-correct, all-wrong, and mixed answers.
- [ ] Test lowercase choices according to the chosen normalization rule.
- [ ] Test invalid choices and unknown question IDs.
- [ ] Test duplicate answers.
- [ ] Test incomplete and repeated `finish()` calls.
- [ ] Test quizzes whose question IDs are valid but not sequential.
- [ ] Verify the exact `QuizResult` fields using the shared fixture.
- [ ] Add contract tests proving the shared fixture loads into the agreed domain models.
- [ ] Add contract tests for the `Quiz` → `QuizSession` → `QuizResult` boundary.

## Integration contract

```python
session = QuizSession(quiz)
session.submit_answer(question_id, choice)
result = session.finish()
```

Flutura owns prompts, display order, retry messages, and result formatting. The session should raise clear domain/application exceptions that the CLI can catch and present. It must not import the CLI, exporter, Gemini provider, or file reader.

## Deliverable

Given the shared fixture and a set of answer choices, `finish()` returns the correct `QuizResult`, including an accurate score and wrong-question ID list.

Suggested branch: `feature/quiz-engine`.

