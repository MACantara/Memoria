export class UIManager {
    showCard(index, flashcardsArray, score) {
        flashcardsArray.forEach(card => {
            card.style.display = 'none';
            card.classList.remove('active');
        });

        const currentCard = flashcardsArray[index];
        if (currentCard) {
            currentCard.style.display = 'block';
            currentCard.classList.add('active');
            this.updateCardCounter(index, flashcardsArray.length, score);
        }
    }

    updateCardCounter(index, total, score) {
        const remaining = total - score;
        document.getElementById('cardNumber').textContent = 
            `Card ${index + 1} of ${total} (${remaining} remaining)`;
    }

    updateScore(score) {
        document.getElementById('score').textContent = score;
    }

    showCompletion(score, total) {
        const container = document.getElementById('flashcardsContainer');
        container.innerHTML = `
            <div class="card text-center p-5">
                <div class="card-body">
                    <h2 class="card-title mb-4">
                        <i class="bi bi-emoji-smile-fill text-success"></i> Congratulations!
                    </h2>
                    <p class="card-text fs-5">You've successfully completed all flashcards.</p>
                    <p class="card-text fs-4 text-success fw-bold">
                        <i class="bi bi-trophy-fill"></i> Final Score: ${score}/${total}
                    </p>
                    <div class="d-flex justify-content-center gap-3 mt-4">
                        <a href="${window.location.href}" class="btn btn-primary">
                            <i class="bi bi-arrow-repeat"></i> Study Again
                        </a>
                        <a href="/" class="btn btn-outline-primary">
                            <i class="bi bi-house-door"></i> Back to Topics
                        </a>
                    </div>
                </div>
            </div>
        `;
    }

    renderAnswerOptions(flashcard, allAnswers) {
        const answersForm = flashcard.querySelector('.answer-form');
        answersForm.innerHTML = allAnswers.map((answer, index) => `
            <label class="form-check answer-option p-3 mb-3 rounded border user-select-none w-100" 
                   role="button" 
                   style="cursor: pointer"
                   for="${flashcard.dataset.id}-${index}">
                <div class="d-flex align-items-center">
                    <input class="form-check-input" type="radio" 
                           id="${flashcard.dataset.id}-${index}" 
                           name="flashcard-${flashcard.dataset.id}" 
                           value="${answer.replace(/"/g, '&quot;')}">
                    <div class="ms-2">
                        <span class="badge bg-light text-dark me-2">${index + 1}</span>
                        ${answer}
                    </div>
                </div>
            </label>
        `).join('');
    }

    showAnswerFeedback(flashcard, isCorrect) {
        const feedback = document.createElement('div');
        feedback.classList.add('alert', isCorrect ? 'alert-success' : 'alert-danger', 'mt-3');
        
        feedback.innerHTML = isCorrect ? 
            '<i class="bi bi-check-circle-fill"></i> Correct!' : 
            '<i class="bi bi-x-circle-fill"></i> Incorrect - Moving to next question';
        
        const existingFeedback = flashcard.querySelector('.alert');
        if (existingFeedback) {
            existingFeedback.remove();
        }
        
        flashcard.querySelector('.answer-form').appendChild(feedback);
    }
}
