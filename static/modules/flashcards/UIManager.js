export class UIManager {
    constructor() {
        this.progressBar = document.getElementById('progressBar');
        this.statusBadge = document.getElementById('statusBadge');
        this.cardCounter = document.getElementById('cardCounter');
        this.flashcardContainer = document.getElementById('currentFlashcard');
        this.questionContainer = document.getElementById('questionContainer');
        this.answerForm = document.getElementById('answerForm');
        this.loadingIndicator = document.getElementById('loadingIndicator');
        
        // Get the study mode from URL parameters
        this.isDueOnlyMode = new URLSearchParams(window.location.search).get('due_only') === 'true';
    }

    renderCard(card) {
        if (!this.flashcardContainer || !card) return;
        
        // Make sure card is visible
        this.flashcardContainer.style.display = 'block';
        
        // Set question
        if (this.questionContainer) {
            this.questionContainer.textContent = card.question;
        }
        
        // Clear any previous answers and feedback
        if (this.answerForm) {
            this.answerForm.innerHTML = '';
        }
        
        // Update state badge based on card state
        this.updateStatusBadge(parseInt(card.state || 0));
        
        // Generate and render answer options
        this.renderAnswerOptions(card);
    }
    
    renderAnswerOptions(card) {
        if (!this.answerForm || !card) return;
        
        // Create shuffled array of all answers
        const allAnswers = [...card.incorrect_answers, card.correct_answer];
        const shuffledAnswers = this.shuffleArray([...allAnswers]);
        
        // Generate HTML for answer options
        const optionsHtml = shuffledAnswers.map((answer, index) => `
            <div class="mb-3">
                <div class="answer-option form-check p-3 rounded border user-select-none">
                    <input class="form-check-input" type="radio" 
                           id="answer-${index}" 
                           name="flashcard-answer" 
                           value="${answer.replace(/"/g, '&quot;')}">
                    <label class="form-check-label w-100" 
                           for="answer-${index}"
                           style="cursor: pointer">
                        <div class="d-flex align-items-center">
                            <span class="badge bg-light text-dark me-2">${index + 1}</span>
                            <div class="answer-text">${answer}</div>
                        </div>
                    </label>
                </div>
            </div>
        `).join('');
        
        // Insert options into the form
        this.answerForm.innerHTML = optionsHtml;
        
        // Store correct answer for checking
        this.answerForm.dataset.correctAnswer = card.correct_answer;
        
        // Add click handler to each answer option
        this.answerForm.querySelectorAll('.answer-option').forEach(option => {
            option.addEventListener('click', () => {
                const radio = option.querySelector('input[type="radio"]');
                if (!radio.checked) {
                    radio.checked = true;
                    
                    // Get the FlashcardManager instance from window
                    if (window.flashcardManager) {
                        window.flashcardManager.handleAnswer(radio.value);
                    }
                }
            });
        });
    }
    
    shuffleArray(array) {
        // Fisher-Yates shuffle algorithm
        for (let i = array.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [array[i], array[j]] = [array[j], array[i]];
        }
        return array;
    }
    
    showLoading(isLoading) {
        if (!this.loadingIndicator) return;
        
        if (isLoading) {
            this.loadingIndicator.classList.remove('d-none');
        } else {
            this.loadingIndicator.classList.add('d-none');
        }
    }

    updateStatusBadge(state) {
        if (!this.statusBadge) return;
        
        // Remove existing classes
        this.statusBadge.classList.remove('bg-secondary', 'bg-warning', 'bg-success', 'bg-danger');
        
        // Update badge style and text based on state
        switch(parseInt(state)) {
            case 0: // New
                this.statusBadge.textContent = 'New';
                this.statusBadge.classList.add('bg-secondary');
                break;
            case 1: // Learning
                this.statusBadge.textContent = 'Learning';
                this.statusBadge.classList.add('bg-warning');
                break;
            case 2: // Mastered
                this.statusBadge.textContent = 'Mastered';
                this.statusBadge.classList.add('bg-success');
                break;
            case 3: // Forgotten
                this.statusBadge.textContent = 'Forgotten';
                this.statusBadge.classList.add('bg-danger');
                break;
        }
    }

    updateCardCounter(index, total, score, remaining) {
        // Update the score and remaining counts with accurate numbers
        const scoreCountElement = document.getElementById('scoreCount');
        const remainingCountElement = document.getElementById('remainingCount');
        
        if (scoreCountElement) {
            scoreCountElement.textContent = score;
        }
        
        if (remainingCountElement) {
            remainingCountElement.textContent = remaining;
        }
        
        // Update the full card counter text if it exists
        if (this.cardCounter) {
            this.cardCounter.innerHTML = `<span id="scoreCount">${score}</span> / ${total} completed (<span id="remainingCount">${remaining}</span> remaining)`;
        }
    }

    updateScore(score, total) {
        // Update only the progress bar, not the text
        if (this.progressBar) {
            const percent = total > 0 ? (score / total) * 100 : 0;
            this.progressBar.style.width = `${percent}%`;
            this.progressBar.setAttribute('aria-valuenow', percent);
        }
    }

    showBriefFeedback(isCorrect) {
        if (!this.answerForm) return;
        
        // Create a simple feedback container without navigation buttons
        const feedbackContainer = document.createElement('div');
        feedbackContainer.classList.add('feedback-container', 'mt-3');
        
        // Feedback message
        const feedback = document.createElement('div');
        feedback.classList.add('alert', isCorrect ? 'alert-success' : 'alert-danger', 'mb-2');
        feedback.innerHTML = isCorrect ? 
            '<i class="bi bi-check-circle-fill"></i> Correct! Moving to next card...' : 
            '<i class="bi bi-x-circle-fill"></i> Incorrect';
            
        feedbackContainer.appendChild(feedback);
        
        // Add container to the form
        this.answerForm.appendChild(feedbackContainer);
    }

    showAnswerFeedback(isCorrect, nextCardCallback) {
        if (!this.answerForm) return;
        
        // Create a feedback container with navigation buttons
        const feedbackContainer = document.createElement('div');
        feedbackContainer.classList.add('feedback-container', 'mt-3');
        
        // Feedback message
        const feedback = document.createElement('div');
        feedback.classList.add('alert', isCorrect ? 'alert-success' : 'alert-danger', 'mb-2');
        feedback.innerHTML = isCorrect ? 
            '<i class="bi bi-check-circle-fill"></i> Correct!' : 
            '<i class="bi bi-x-circle-fill"></i> Incorrect';
            
        feedbackContainer.appendChild(feedback);
        
        // Add next button for manual advancement
        const nextButton = document.createElement('button');
        nextButton.type = 'button';
        nextButton.className = 'btn btn-primary w-100';
        nextButton.innerHTML = 'Next Question <i class="bi bi-arrow-right"></i>';
        nextButton.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (typeof nextCardCallback === 'function') {
                nextCardCallback();
            }
        });
        feedbackContainer.appendChild(nextButton);
        
        // Add subtle keyboard hint text with Bootstrap styling and icon
        const keyboardHint = document.createElement('div');
        keyboardHint.className = 'text-center text-muted small mt-2 py-1';
        keyboardHint.innerHTML = '<i class="bi bi-keyboard me-1"></i> Press any key to continue';
        feedbackContainer.appendChild(keyboardHint);
        
        // Add container to the form
        this.answerForm.appendChild(feedbackContainer);
        
        // Focus next button to make keyboard navigation work
        setTimeout(() => nextButton.focus(), 100);
    }

    showCompletionScreen(deckId, score, totalDue, isDueOnly, remainingDueCards) {
        // Update card counters first to show all completed
        this.updateCardCounter(totalDue - 1, totalDue, totalDue);
        this.updateScore(totalDue, totalDue);
        
        // Create different completion screens depending on the mode and whether there are more due cards
        if (!this.flashcardContainer) return;
        
        if (isDueOnly) {
            if (remainingDueCards > 0) {
                // Due Only mode with more cards due - show option to continue
                this.flashcardContainer.innerHTML = `
                    <div class="text-center p-3">
                        <div>
                            <h2 class="card-title mb-4">
                                <i class="bi bi-check2-circle text-success"></i> Session Complete!
                            </h2>
                            <p class="card-text fs-5">You've reviewed ${score} flashcards in this session.</p>
                            <div class="progress mb-3" style="height: 20px;">
                                <div class="progress-bar bg-success" role="progressbar" 
                                    style="width: 100%" aria-valuenow="100" aria-valuemin="0" 
                                    aria-valuemax="100">100%</div>
                            </div>
                            
                            <div class="alert alert-info mt-4">
                                <i class="bi bi-info-circle me-2"></i>
                                <strong>${remainingDueCards} more cards</strong> have become due for review since you started this session.
                            </div>
                            
                            <div class="d-flex justify-content-center gap-3 mt-4 flex-wrap">
                                <a href="/deck/${deckId}/study?due_only=true" class="btn btn-primary">
                                    <i class="bi bi-arrow-right"></i> Continue Studying Due Cards
                                </a>
                                <a href="/deck/${deckId}" class="btn btn-outline-secondary">
                                    <i class="bi bi-house-door"></i> Back to Deck
                                </a>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                // Due Only mode with no more cards due - show standard completion
                this.flashcardContainer.innerHTML = `
                    <div class="text-center p-3">
                        <div>
                            <h2 class="card-title mb-4">
                                <i class="bi bi-calendar-check-fill text-success"></i> All Due Cards Completed!
                            </h2>
                            <p class="card-text fs-5">You've reviewed all flashcards that were due today.</p>
                            <div class="progress mb-3" style="height: 20px;">
                                <div class="progress-bar bg-success" role="progressbar" 
                                    style="width: 100%" aria-valuenow="100" aria-valuemin="0" 
                                    aria-valuemax="100">100%</div>
                            </div>
                            
                            <div class="alert alert-info mt-4">
                                <i class="bi bi-info-circle me-2"></i>
                                Want to study more? You can also review cards that aren't due yet.
                            </div>
                            
                            <div class="d-flex justify-content-center gap-3 mt-4 flex-wrap">
                                <a href="/deck/${deckId}/study" class="btn btn-primary">
                                    <i class="bi bi-collection"></i> Study All Cards
                                </a>
                                <a href="/deck/${deckId}" class="btn btn-outline-secondary">
                                    <i class="bi bi-house-door"></i> Back to Deck
                                </a>
                            </div>
                        </div>
                    </div>
                `;
            }
        } else {
            // Study All mode - show standard completion
            this.flashcardContainer.innerHTML = `
                <div class="card text-center p-5">
                    <div class="card-body">
                        <h2 class="card-title mb-4">
                            <i class="bi bi-emoji-smile-fill text-success"></i> Session Complete!
                        </h2>
                        <p class="card-text fs-5">You've completed your flashcard review session.</p>
                        <div class="progress mb-3" style="height: 20px;">
                            <div class="progress-bar bg-success" role="progressbar" 
                                style="width: 100%" aria-valuenow="100" aria-valuemin="0" 
                                aria-valuemax="100">100%</div>
                        </div>
                        <p class="card-text fs-4 text-success fw-bold">
                            <i class="bi bi-trophy-fill"></i> Session Score: ${score}/${totalDue}
                        </p>
                        <div class="d-flex justify-content-center gap-3 mt-4 flex-wrap">
                            <a href="${window.location.href}" class="btn btn-primary">
                                <i class="bi bi-arrow-repeat"></i> Study Again
                            </a>
                            <a href="/deck/${deckId}" class="btn btn-outline-secondary">
                                <i class="bi bi-house-door"></i> Back to Deck
                            </a>
                        </div>
                    </div>
                </div>
            `;
        }

        // Update badge to show completion status
        if (this.statusBadge) {
            this.statusBadge.textContent = 'Completed';
            this.statusBadge.className = 'badge bg-success';
        }
    }
}
