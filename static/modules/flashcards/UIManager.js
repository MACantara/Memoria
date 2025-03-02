export class UIManager {
    constructor() {
        this.totalCards = document.querySelectorAll('.flashcard').length;
        this.progressBar = document.getElementById('progressBar');
        this.scoreElement = document.getElementById('score');
        this.cardNumberElement = document.getElementById('cardNumber');
        this.statusBadge = document.getElementById('statusBadge');
        
        // Get the study mode from URL parameters
        this.isDueOnlyMode = new URLSearchParams(window.location.search).get('due_only') === 'true';
    }

    showCard(index, flashcardsArray, score) {
        flashcardsArray.forEach(card => {
            card.style.display = 'none';
            card.classList.remove('active');
        });

        const currentCard = flashcardsArray[index];
        if (currentCard) {
            // Clear any previous feedback before showing card
            this.clearFeedback(currentCard);
            
            currentCard.style.display = 'block';
            currentCard.classList.add('active');
            this.updateCardCounter(index, flashcardsArray.length, score);
            
            // Simply set the raw question text directly
            const questionElem = currentCard.querySelector('.card-title');
            if (questionElem) {
                questionElem.textContent = questionElem.dataset.question;
            }

            // Update prominent status badge above the card
            const state = currentCard.dataset.state || '0';
            this.updateStatusBadge(parseInt(state));
        }
    }
    
    updateStatusBadge(stateNum) {
        if (!this.statusBadge) return;
        
        const stateName = this.getStateName(stateNum);
        this.statusBadge.textContent = stateName.charAt(0).toUpperCase() + stateName.slice(1);
        
        // Reset badge classes but keep size and padding classes
        this.statusBadge.className = 'badge fs-4 p-3';
        
        // Add appropriate class based on state
        switch(stateNum) {
            case 0:
                this.statusBadge.classList.add('bg-secondary');
                break;
            case 1:
                this.statusBadge.classList.add('bg-warning', 'text-dark');
                break;
            case 2:
                this.statusBadge.classList.add('bg-success');
                break;
            case 3:
                this.statusBadge.classList.add('bg-danger');
                break;
        }
    }

    clearFeedback(flashcard) {
        const existingFeedback = flashcard.querySelector('.feedback-container');
        if (existingFeedback) {
            existingFeedback.remove();
        }
    }

    updateCardCounter(index, total, score) {
        // Calculate cards left to review in this session
        const remaining = Math.max(0, total - score);
        const remainingText = remaining > 0 ? 
            `(${remaining} remaining)` : 
            '(0 remaining)';
        
        if (this.cardNumberElement) {
            this.cardNumberElement.textContent = 
                `Card ${index + 1} of ${total} ${remainingText}`;
        }
    }

    updateScore(score, totalDue) {
        // Update the score text to show session completion rather than mastery
        const scoreElement = document.getElementById('score');
        if (scoreElement) scoreElement.textContent = score;
        
        // Update the progress bar
        const progressBar = document.getElementById('progressBar');
        if (progressBar) {
            // Calculate completion percentage for this session
            const percentage = totalDue > 0 ? (score / totalDue) * 100 : 0;
            progressBar.style.width = `${percentage}%`;
            progressBar.setAttribute('aria-valuenow', percentage);
            
            // Change progress bar color based on completion percentage
            if (percentage < 30) {
                progressBar.className = "progress-bar bg-danger";
            } else if (percentage < 70) {
                progressBar.className = "progress-bar bg-warning";
            } else {
                progressBar.className = "progress-bar bg-success";
            }
        }
    }

    showCompletion(score, totalDue) {
        // Update progress bar to 100% first
        this.updateScore(score, totalDue);
        
        // Update card counter to show 0 remaining
        if (this.cardNumberElement) {
            this.cardNumberElement.textContent = 
                `Complete (0 remaining)`;
        }
        
        // Update the status badge to show completion
        this.statusBadge.textContent = 'Completed';
        this.statusBadge.className = 'badge fs-4 p-3 bg-success';
        
        const container = document.getElementById('flashcardsContainer');
        
        // Different message based on whether we're in due-only mode or all cards mode
        const heading = this.isDueOnlyMode ? 
            "All Due Cards Completed!" : 
            "Session Complete!";
            
        const message = this.isDueOnlyMode ?
            "You've reviewed all flashcards that were due today." :
            "You've completed your flashcard review session.";
            
        const icon = this.isDueOnlyMode ? 
            "bi-calendar-check-fill" : 
            "bi-emoji-smile-fill";
            
        // Create additional study options for due-only mode
        const additionalOptions = this.isDueOnlyMode ? `
            <div class="alert alert-info">
                <i class="bi bi-info-circle me-2"></i>
                Want to study more? You can also review cards that aren't due yet.
            </div>
            <a href="${window.location.pathname}" class="btn btn-outline-primary me-2">
                <i class="bi bi-collection"></i> Study All Cards
            </a>
        ` : '';
        
        container.innerHTML = `
            <div class="card text-center p-5">
                <div class="card-body">
                    <h2 class="card-title mb-4">
                        <i class="bi ${icon} text-success"></i> ${heading}
                    </h2>
                    <p class="card-text fs-5">${message}</p>
                    <div class="progress mb-3" style="height: 20px;">
                        <div class="progress-bar bg-success" role="progressbar" 
                            style="width: 100%" aria-valuenow="100" aria-valuemin="0" 
                            aria-valuemax="100">100%</div>
                    </div>
                    <p class="card-text fs-4 text-success fw-bold">
                        <i class="bi bi-trophy-fill"></i> Session Score: ${score}/${totalDue}
                    </p>
                    <div class="d-flex justify-content-center gap-3 mt-4 flex-wrap">
                        ${additionalOptions}
                        <a href="${window.location.href}" class="btn btn-primary">
                            <i class="bi bi-arrow-repeat"></i> Study Again
                        </a>
                        <a href="/" class="btn btn-outline-primary">
                            <i class="bi bi-house-door"></i> Back to Decks
                        </a>
                    </div>
                </div>
            </div>
        `;

        // Update badge to show completion status
        if (this.statusBadge) {
            this.statusBadge.textContent = 'Completed';
            this.statusBadge.className = 'badge bg-success';
        }
    }

    renderAnswerOptions(flashcard, allAnswers) {
        const answersForm = flashcard.querySelector('.answer-form');
        answersForm.innerHTML = allAnswers.map((answer, index) => `
            <div class="mb-3">
                <div class="answer-option form-check p-3 rounded border user-select-none">
                    <input class="form-check-input" type="radio" 
                           id="${flashcard.dataset.id}-${index}" 
                           name="flashcard-${flashcard.dataset.id}" 
                           value="${answer.replace(/"/g, '&quot;')}">
                    <label class="form-check-label w-100" 
                           for="${flashcard.dataset.id}-${index}"
                           style="cursor: pointer">
                        <div class="d-flex align-items-center">
                            <span class="badge bg-light text-dark me-2">${index + 1}</span>
                            <div class="answer-text">${answer}</div>
                        </div>
                    </label>
                </div>
            </div>
        `).join('');

        // Add click handler to the entire option div for better UX
        answersForm.querySelectorAll('.answer-option').forEach(option => {
            option.addEventListener('click', () => {
                const radio = option.querySelector('input[type="radio"]');
                if (!radio.checked) {
                    radio.checked = true;
                    radio.dispatchEvent(new Event('click', { bubbles: true }));
                }
            });
        });
    }

    showAnswerFeedback(flashcard, isCorrect, nextCardCallback) {
        // Clear any previous feedback first
        this.clearFeedback(flashcard);
        
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
        nextButton.classList.add('btn', 'btn-primary', 'w-100');
        nextButton.innerHTML = '<i class="bi bi-arrow-right"></i> Next Question';
        nextButton.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (typeof nextCardCallback === 'function') {
                nextCardCallback();
            }
        });
        feedbackContainer.appendChild(nextButton);
        
        // Add container to the card
        const form = flashcard.querySelector('.answer-form');
        form.appendChild(feedbackContainer);
        
        // Focus next button to make keyboard navigation work
        setTimeout(() => nextButton.focus(), 100);
    }

    getStateName(stateNum) {
        const stateMap = {
            0: 'new',
            1: 'learning',
            2: 'mastered',
            3: 'forgotten'
        };
        return stateMap[stateNum] || 'new';
    }
}
