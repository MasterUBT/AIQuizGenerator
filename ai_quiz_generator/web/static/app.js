const modeInputs = document.querySelectorAll('input[name="mode"]');
const sourcePanels = document.querySelectorAll("[data-source-panel]");

function updateSourcePanel() {
  const selected = document.querySelector('input[name="mode"]:checked')?.value;
  sourcePanels.forEach((panel) => {
    panel.hidden = panel.dataset.sourcePanel !== selected;
  });
}

modeInputs.forEach((input) => input.addEventListener("change", updateSourcePanel));
updateSourcePanel();

const fileInput = document.querySelector("#lecture-file");
const fileName = document.querySelector("[data-file-name]");
fileInput?.addEventListener("change", () => {
  fileName.textContent = fileInput.files[0]?.name || "UTF-8 .txt, up to 1 MB";
});

const generationForm = document.querySelector("[data-generation-form]");
const loadingOverlay = document.querySelector("[data-loading-overlay]");
generationForm?.addEventListener("submit", () => {
  loadingOverlay.hidden = false;
});

const quizForm = document.querySelector("[data-quiz-form]");
const answeredCount = document.querySelector("[data-answered-count]");
const progressBar = document.querySelector("[data-progress-bar]");

function updateQuizProgress() {
  if (!quizForm) return;
  const groups = new Set(
    [...quizForm.querySelectorAll('input[type="radio"]:checked')].map(
      (input) => input.name,
    ),
  );
  const total = quizForm.querySelectorAll(".question-card").length;
  if (answeredCount) answeredCount.textContent = String(groups.size);
  if (progressBar) progressBar.style.width = `${(groups.size / total) * 100}%`;
}

quizForm?.addEventListener("change", updateQuizProgress);
updateQuizProgress();
