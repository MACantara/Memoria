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
            <div class="completion-message">
                <h2>🎉 Congratulations!</h2>
                <p>You've successfully completed all flashcards.</p>
                <p>Final Score: ${score}/${total}</p>
                <a href="${window.location.href}" class="button">Study Again</a>
                <a href="/" class="button">Back to Topics</a>
            </div>
        `;
    }

    renderAnswerOptions(flashcard, allAnswers) {
        const answersForm = flashcard.querySelector('.answer-form');
        answersForm.innerHTML = allAnswers.map((answer, index) => `
            <div class="answer-option">
                <input type="radio" id="${flashcard.dataset.id}-${index}" 
                       name="flashcard-${flashcard.dataset.id}" 
                       value="${answer.replace(/"/g, '&quot;')}">
                <label for="${flashcard.dataset.id}-${index}">
                    <span class="key-hint">${index + 1}</span>${answer}
                </label>
            </div>
        `).join('');
    }

    showAnswerFeedback(flashcard, isCorrect) {
        const feedback = document.createElement('div');
        feedback.classList.add('feedback');
        feedback.textContent = isCorrect ? '✓ Correct!' : '✗ Incorrect - Moving to next question';
        feedback.classList.add(isCorrect ? 'correct' : 'incorrect');
        
        const existingFeedback = flashcard.querySelector('.feedback');
        if (existingFeedback) {
            existingFeedback.remove();
        }
        
        flashcard.querySelector('.answer-form').appendChild(feedback);
    }
}
