export class UIManager {
    constructor() {
        this.md = window.markdownit({
            html: false,
            breaks: true,
            linkify: true,
            typographer: true
        });
        
        // Configure markdown-it to handle math expressions better
        this.configureMathHandling();
        
        this.totalCards = document.querySelectorAll('.flashcard').length;
        this.progressBar = document.getElementById('progressBar');
        this.scoreElement = document.getElementById('score');
        this.cardNumberElement = document.getElementById('cardNumber');
        this.statusBadge = document.getElementById('statusBadge');
    }
    
    configureMathHandling() {
        // Add a custom rule to escape asterisks in common math patterns
        const originalRender = this.md.renderer.rules.text || function(tokens, idx) {
            return tokens[idx].content;
        };
        
        this.md.renderer.rules.text = (tokens, idx) => {
            let content = tokens[idx].content;
            
            // Pattern for math expressions like "2*3", "x*y", etc.
            // This regex looks for digit/variable followed by asterisk followed by digit/variable
            content = content.replace(/(\d|[a-zA-Z])\*(\d|[a-zA-Z])/g, '$1×$2');
            
            return originalRender(tokens, idx, this.md.options, {}, this);
        };
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
            
            // Parse question markdown
            const questionElem = currentCard.querySelector('.card-title');
            if (questionElem) {
                const rawQuestion = questionElem.dataset.question;
                questionElem.innerHTML = this.parseContent(rawQuestion);
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
        const existingFeedback = flashcard.querySelector('.alert');
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
        container.innerHTML = `
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
                    <div class="d-flex justify-content-center gap-3 mt-4">
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

    parseContent(text) {
        if (!text) return '';
        
        // Clean the text and pre-process math expressions
        let cleanText = text.trim()
            .replace(/\\n/g, '\n')  // Handle escaped newlines
            .replace(/\\"/g, '"');  // Handle escaped quotes
            
        // Replace standalone multiplication operators with × symbol
        // This handles cases like "2 * 3" with spaces
        cleanText = cleanText.replace(/(\d|\b[a-zA-Z])\s*\*\s*(\d|\b[a-zA-Z])/g, '$1 × $2');
        
        // Process with markdown-it
        return this.md.render(cleanText);
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
                            <div class="answer-text">${this.parseContent(answer)}</div>
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

    showAnswerFeedback(flashcard, isCorrect) {
        // Clear any previous feedback first
        this.clearFeedback(flashcard);
        
        const feedback = document.createElement('div');
        feedback.classList.add('alert', isCorrect ? 'alert-success' : 'alert-danger', 'mt-3');
        
        feedback.innerHTML = isCorrect ? 
            '<i class="bi bi-check-circle-fill"></i> Correct!' : 
            '<i class="bi bi-x-circle-fill"></i> Incorrect - Moving to next question';
        
        flashcard.querySelector('.answer-form').appendChild(feedback);
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
