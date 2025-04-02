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
        
        // Initialize audio elements for feedback sounds
        this.successSound = new Audio('/static/sounds/success.mp3');
        this.errorSound = new Audio('/static/sounds/error.mp3');
        
        // Preload the sounds
        this.successSound.load();
        this.errorSound.load();

        // Add explanation sound
        this.insightSound = new Audio('/static/sounds/insight.mp3');
        this.insightSound.load();

        // Initialize milestone progress bar elements
        this.progressBarContainer = document.getElementById('progressBarContainer');
        this.progressMilestones = document.getElementById('progressMilestones');
        this.milestoneSegments = [];
        this.currentSegment = 0;
        this.cardsPerSegment = 25; // Smaller, more manageable chunks
        this.celebrationSound = new Audio('/static/sounds/achievement.mp3');
        this.celebrationSound.load();

        // Initialize modal for explanations
        this.explanationModal = null;
        
        // Try to initialize the explanation modal if the element exists
        const explanationModalElement = document.getElementById('explanationModal');
        if (explanationModalElement && typeof bootstrap !== 'undefined') {
            this.explanationModal = new bootstrap.Modal(explanationModalElement);
        } else {
            console.warn('Explanation modal element not found or bootstrap not loaded');
        }
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
        
        // Create a container for the answers
        const answersContainer = document.createElement('div');
        
        // Get the current theme
        const isDarkTheme = document.documentElement.getAttribute('data-bs-theme') === 'dark';
        
        // Generate answer options with improved UI
        shuffledAnswers.forEach((answer, index) => {
            const optionDiv = document.createElement('div');
            optionDiv.className = 'mb-3';
            
            const answerOption = document.createElement('div');
            answerOption.className = 'answer-option form-check p-0 rounded border user-select-none';
            answerOption.setAttribute('data-answer-value', answer);
            
            // Create radio button with custom styling
            const radio = document.createElement('input');
            radio.className = 'form-check-input visually-hidden';
            radio.type = 'radio';
            radio.id = `answer-${index}`;
            radio.name = 'flashcard-answer';
            radio.value = answer;
            
            // Create label container with improved styling
            const label = document.createElement('label');
            label.className = 'form-check-label d-block w-100 p-3';
            label.htmlFor = `answer-${index}`;
            label.style.cursor = 'pointer';
            label.style.borderRadius = 'inherit';
            
            // Create flex container for radio button and answer text
            const flexContainer = document.createElement('div');
            flexContainer.className = 'd-flex align-items-center';
            
            // Create custom radio button visual
            const customRadio = document.createElement('div');
            customRadio.className = 'custom-radio-btn me-3 border border-secondary rounded-circle';
            customRadio.style.width = '20px';
            customRadio.style.height = '20px';
            customRadio.style.position = 'relative';
            
            // Inner circle for selected state
            const innerCircle = document.createElement('div');
            innerCircle.className = 'inner-circle bg-primary rounded-circle d-none';
            innerCircle.style.width = '12px';
            innerCircle.style.height = '12px';
            innerCircle.style.position = 'absolute';
            innerCircle.style.top = '50%';
            innerCircle.style.left = '50%';
            innerCircle.style.transform = 'translate(-50%, -50%)';
            customRadio.appendChild(innerCircle);
            
            // Create div for answer text
            const answerText = document.createElement('div');
            answerText.className = 'answer-text';
            answerText.textContent = answer; // Use textContent to show raw HTML
            
            // Assemble the elements
            flexContainer.appendChild(customRadio);
            flexContainer.appendChild(answerText);
            label.appendChild(flexContainer);
            answerOption.appendChild(radio);
            answerOption.appendChild(label);
            optionDiv.appendChild(answerOption);
            
            // Add hover effect with theme awareness
            label.addEventListener('mouseenter', () => {
                if (!radio.checked) {
                    answerOption.classList.add('border-primary');
                    // Use theme-aware class instead of hardcoded bg-light
                    label.classList.add(isDarkTheme ? 'bg-dark-subtle' : 'bg-light');
                }
            });
            
            label.addEventListener('mouseleave', () => {
                if (!radio.checked) {
                    answerOption.classList.remove('border-primary');
                    // Remove appropriate class based on theme
                    label.classList.remove(isDarkTheme ? 'bg-dark-subtle' : 'bg-light');
                }
            });
            
            // Add click handler
            answerOption.addEventListener('click', () => {
                // Update all options to remove selection styling
                answersContainer.querySelectorAll('.answer-option').forEach(option => {
                    option.classList.remove('selected', 'border-primary');
                    // Remove both possible theme classes for safety
                    option.querySelector('label')?.classList.remove('bg-light', 'bg-dark-subtle');
                    const innerDot = option.querySelector('.inner-circle');
                    if (innerDot) innerDot.classList.add('d-none');
                });
                
                // Add selection styling to this option
                answerOption.classList.add('selected', 'border-primary');
                // Apply the appropriate theme class
                label.classList.add(isDarkTheme ? 'bg-dark-subtle' : 'bg-light');
                innerCircle.classList.remove('d-none');
                
                if (!radio.checked) {
                    radio.checked = true;
                    
                    // Get the FlashcardManager instance from window
                    if (window.flashcardManager) {
                        window.flashcardManager.handleAnswer(radio.value);
                    }
                }
            });
            
            answersContainer.appendChild(optionDiv);
        });
        
        // Clear the form and add the new answers
        this.answerForm.innerHTML = '';
        this.answerForm.appendChild(answersContainer);
        
        // Store correct answer for checking
        this.answerForm.dataset.correctAnswer = card.correct_answer;
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
        const loadingContainer = document.getElementById('loadingContainer');
        if (!loadingContainer) return;
        
        if (isLoading) {
            loadingContainer.style.display = 'block';
        } else {
            loadingContainer.style.display = 'none';
        }
    }

    showLoadingError(message) {
        // Create an error alert that appears where the loading indicator would be
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger my-3';
        errorDiv.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                <div>
                    <p class="mb-0">Error loading flashcards</p>
                    <small>${message}</small>
                </div>
            </div>
            <div class="mt-2">
                <button class="btn btn-sm btn-outline-danger" onclick="window.location.reload()">
                    Retry
                </button>
            </div>
        `;
        
        // Find the loading container and replace its contents
        const loadingContainer = document.getElementById('loadingContainer');
        if (loadingContainer) {
            // First clear the container
            loadingContainer.innerHTML = '';
            // Then add the error message
            loadingContainer.appendChild(errorDiv);
            // Make sure it's visible
            loadingContainer.style.display = 'block';
        } else {
            // If no loading container, try to add it to the flashcard container
            const container = document.getElementById('flashcardsContainer');
            if (container) {
                container.appendChild(errorDiv);
            }
        }
        
        // Also hide the flashcard container if it exists
        const flashcardContainer = document.getElementById('currentFlashcard');
        if (flashcardContainer) {
            flashcardContainer.style.display = 'none';
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
        // Update milestone progress - this now handles progress bar updates
        this.updateMilestones(score, total);
    }

    showBriefFeedback(isCorrect) {
        if (!this.answerForm) return;
        
        // Play appropriate sound based on correctness
        this.playFeedbackSound(isCorrect);
        
        // Apply visual feedback to the selected answer
        this.applyVisualAnswerFeedback(isCorrect);
        
        // Create a feedback container with enhanced visual design
        const feedbackContainer = document.createElement('div');
        feedbackContainer.classList.add('feedback-container', 'mt-4', 'animate__animated', 'animate__fadeIn');
        
        // Feedback message with enhanced styling
        const feedback = document.createElement('div');
        feedback.classList.add(
            'alert', 
            isCorrect ? 'alert-success' : 'alert-danger',
            'd-flex',
            'align-items-center',
            'mb-0'
        );
        
        // Create icon container with larger icon
        const iconContainer = document.createElement('div');
        iconContainer.className = 'me-3 fs-3';
        iconContainer.innerHTML = isCorrect 
            ? '<i class="bi bi-check-circle-fill text-success"></i>' 
            : '<i class="bi bi-x-circle-fill text-danger"></i>';
        
        // Create message container
        const messageContainer = document.createElement('div');
        messageContainer.innerHTML = `
            <h5 class="mb-0">${isCorrect ? 'Correct!' : 'Incorrect'}</h5>
            <div class="small">${isCorrect ? 'Moving to next card...' : 'Try to remember this card for next time.'}</div>
        `;
        
        feedback.appendChild(iconContainer);
        feedback.appendChild(messageContainer);
        feedbackContainer.appendChild(feedback);
        
        // Add container to the form
        this.answerForm.appendChild(feedbackContainer);
    }

    showAnswerFeedback(isCorrect, nextCardCallback) {
        if (!this.answerForm) return;
        
        // Play appropriate sound based on correctness
        this.playFeedbackSound(isCorrect);
        
        // Apply visual feedback to the selected answer
        this.applyVisualAnswerFeedback(isCorrect);
        
        // Create a feedback container with enhanced visual design
        const feedbackContainer = document.createElement('div');
        feedbackContainer.classList.add('feedback-container', 'mt-4', 'animate__animated', 'animate__fadeIn');
        
        // Feedback message with enhanced styling
        const feedback = document.createElement('div');
        feedback.classList.add(
            'alert', 
            isCorrect ? 'alert-success' : 'alert-danger',
            'd-flex',
            'align-items-center'
        );
        
        // Create icon container with larger icon
        const iconContainer = document.createElement('div');
        iconContainer.className = 'me-3 fs-3';
        iconContainer.innerHTML = isCorrect 
            ? '<i class="bi bi-check-circle-fill text-success"></i>' 
            : '<i class="bi bi-x-circle-fill text-danger"></i>';
        
        // Create message container
        const messageContainer = document.createElement('div');
        messageContainer.innerHTML = `
            <h5 class="mb-0">${isCorrect ? 'Correct!' : 'Incorrect'}</h5>
            <div class="small">${isCorrect ? 'Great job!' : 'Try to remember this card for next time.'}</div>
        `;
        
        feedback.appendChild(iconContainer);
        feedback.appendChild(messageContainer);
        feedbackContainer.appendChild(feedback);
        
        // Create button container for multiple buttons
        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'd-flex gap-2 mt-2 flex-wrap';
        
        // For incorrect answers, add the explain button
        if (!isCorrect) {
            // Add explain button with specific ID
            const explainButton = document.createElement('button');
            explainButton.type = 'button';
            explainButton.id = 'explainFlashcardBtn'; // Add specific ID
            explainButton.className = 'btn btn-outline-secondary flex-grow-1 d-flex justify-content-center align-items-center py-2';
            explainButton.innerHTML = '<i class="bi bi-lightbulb me-2"></i><span>Explain</span>';
            explainButton.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                // Get the flashcard ID from the URL or data attribute
                const flashcardId = this.getCurrentFlashcardId();
                if (flashcardId) {
                    // Use modal instead of inline explanation
                    this.showExplanationModal(flashcardId);
                }
            });
            buttonContainer.appendChild(explainButton);
        }
        
        // Add next button with improved styling and specific ID
        const nextButton = document.createElement('button');
        nextButton.type = 'button';
        nextButton.id = 'nextQuestionBtn'; // Keep this ID as it's already used elsewhere
        nextButton.className = 'btn btn-primary flex-grow-1 d-flex justify-content-center align-items-center py-2';
        nextButton.innerHTML = '<span>Next Question</span><i class="bi bi-arrow-right ms-2"></i>';
        nextButton.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (typeof nextCardCallback === 'function') {
                nextCardCallback();
            }
        });
        buttonContainer.appendChild(nextButton);
        
        feedbackContainer.appendChild(buttonContainer);
        
        // Add keyboard hint with improved styling - UPDATED to be more specific
        const keyboardHint = document.createElement('div');
        keyboardHint.className = 'text-center text-muted small mt-2 py-1 d-flex justify-content-center align-items-center';
        keyboardHint.innerHTML = '<i class="bi bi-keyboard me-1"></i><span>Press any key to go to next question</span>';
        feedbackContainer.appendChild(keyboardHint);
        
        // Add container to the form
        this.answerForm.appendChild(feedbackContainer);
        
        // Focus next button to make keyboard navigation work
        setTimeout(() => nextButton.focus(), 100);
    }
    
    /**
     * Show explanation in a modal instead of inline
     * @param {string} flashcardId - The ID of the current flashcard
     */
    showExplanationModal(flashcardId) {
        // Check if modal exists
        if (!this.explanationModal) {
            const modalElement = document.getElementById('explanationModal');
            if (modalElement && typeof bootstrap !== 'undefined') {
                this.explanationModal = new bootstrap.Modal(modalElement);
            } else {
                console.error('Cannot show explanation: modal element not found or bootstrap not loaded');
                return;
            }
        }
        
        // Show loading state in the modal
        const loadingElement = document.getElementById('explanationLoading');
        const contentElement = document.getElementById('explanationContent');
        
        if (loadingElement && contentElement) {
            loadingElement.classList.remove('d-none');
            contentElement.classList.add('d-none');
            contentElement.innerHTML = '';
        }
        
        // Show the modal
        this.explanationModal.show();
        
        // Fetch the explanation from the server
        fetch(`/flashcard/explain/${flashcardId}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to get explanation');
            }
            return response.json();
        })
        .then(data => {
            // Play insight sound
            try {
                this.insightSound.play();
            } catch (error) {
                console.warn("Sound playback failed:", error);
            }
            
            // Check if explanation data exists
            if (contentElement) {
                contentElement.classList.remove('d-none');
                
                if (data.explanation) {
                    // Format the explanation with proper styling
                    contentElement.innerHTML = `
                        <div class="explanation-content">
                            <div class="correct-answer mb-3">
                                <h6 class="text-muted mb-1">Correct Answer:</h6>
                                <div class="p-2 bg-success bg-opacity-10 border border-success rounded">
                                    ${data.correct_answer || 'Not provided'}
                                </div>
                            </div>
                            <div class="explanation-text">
                                <h6 class="text-muted mb-1">Why This Is Correct:</h6>
                                <div class="p-3 rounded">
                                    ${data.explanation}
                                </div>
                            </div>
                        </div>
                    `;
                } else {
                    // Handle case where no explanation was returned
                    contentElement.innerHTML = `
                        <div class="alert alert-info">
                            <i class="bi bi-info-circle me-2"></i>
                            No detailed explanation is available for this question.
                        </div>
                    `;
                }
            }
            
            // Hide the loading indicator
            if (loadingElement) {
                loadingElement.classList.add('d-none');
            }
            
            // Update the explain button on the main screen
            const explainButton = document.getElementById('explainFlashcardBtn');
            if (explainButton) {
                explainButton.disabled = true;
                explainButton.innerHTML = '<i class="bi bi-lightbulb-fill text-warning me-2"></i><span>Explained</span>';
            }
        })
        .catch(error => {
            console.error('Error getting explanation:', error);
            
            // Show error message in the modal
            if (contentElement) {
                contentElement.classList.remove('d-none');
                contentElement.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle-fill me-2"></i>
                        <strong>Error:</strong> Failed to load explanation. Please try again later.
                    </div>
                `;
            }
            
            // Hide the loading indicator
            if (loadingElement) {
                loadingElement.classList.add('d-none');
            }
        });
    }

    getCurrentFlashcardId() {
        // Try to get it from the current card in the UI
        const currentCard = document.getElementById('currentFlashcard');
        if (currentCard && currentCard.dataset.flashcardId) {
            return currentCard.dataset.flashcardId;
        }
        
        // Try to get from FlashcardManager instance
        if (window.flashcardManager && window.flashcardManager.currentCard) {
            return window.flashcardManager.currentCard.id;
        }
        
        return null;
    }

    showCompletionScreen(deckId, score, totalDue, isDueOnly, remainingDueCards) {
        // Update card counters first to show all completed
        this.updateCardCounter(totalDue - 1, totalDue, score, 0);
        this.updateScore(score, totalDue);
        
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
                                <a href="/deck/study/${deckId}?due_only=true" class="btn btn-primary">
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
                // Due Only mode with no more cards due - show standard completion with dropdown
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
                                Want to study more? You can review other cards or try a different deck.
                            </div>
                            
                            <div class="d-flex justify-content-center gap-3 mt-4 flex-wrap">
                                <div class="dropdown">
                                    <button class="btn btn-primary dropdown-toggle" type="button" id="studyOptionsDropdown" 
                                        data-bs-toggle="dropdown" aria-expanded="false">
                                        <i class="bi bi-book"></i> Study Options
                                    </button>
                                    <ul class="dropdown-menu" aria-labelledby="studyOptionsDropdown">
                                        <li>
                                            <a href="/deck/study/${deckId}" class="dropdown-item">
                                                <i class="bi bi-collection me-2"></i> Study All Cards
                                            </a>
                                        </li>
                                        <li><hr class="dropdown-divider"></li>
                                        <li>
                                            <a href="/deck/random-deck" class="dropdown-item">
                                                <i class="bi bi-shuffle me-2"></i> Study Random Deck
                                            </a>
                                        </li>
                                    </ul>
                                </div>
                                <a href="/deck/${deckId}" class="btn btn-outline-secondary">
                                    <i class="bi bi-house-door"></i> Back to Deck
                                </a>
                            </div>
                        </div>
                    </div>
                `;
            }
        } else {
            // Study All mode - show standard completion with random deck option
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
                            <div class="dropdown">
                                <button class="btn btn-primary dropdown-toggle" type="button" id="studyOptionsDropdown" 
                                    data-bs-toggle="dropdown" aria-expanded="false">
                                    <i class="bi bi-book"></i> Study Options
                                </button>
                                <ul class="dropdown-menu" aria-labelledby="studyOptionsDropdown">
                                    <li>
                                        <a href="${window.location.href}" class="dropdown-item">
                                            <i class="bi bi-arrow-repeat me-2"></i> Study Again
                                        </a>
                                    </li>
                                    <li><hr class="dropdown-divider"></li>
                                    <li>
                                        <a href="/deck/random-deck" class="dropdown-item">
                                            <i class="bi bi-shuffle me-2"></i> Study Random Deck
                                        </a>
                                    </li>
                                </ul>
                            </div>
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

    showNoCardsMessage() {
        if (!this.flashcardContainer) return;
        
        this.flashcardContainer.innerHTML = `
            <div class="alert alert-info">
                <h3 class="h5"><i class="bi bi-info-circle me-2"></i>No Cards to Study</h3>
                <p class="mb-0">
                    There are no cards available for study in this deck.
                    <a href="/deck/${document.getElementById('deckId').value}" class="btn btn-sm btn-primary mt-2">
                        <i class="bi bi-arrow-left me-1"></i> Back to Deck
                    </a>
                </p>
            </div>
        `;
    }

    /**
     * Apply visual feedback to the selected answer
     * @param {boolean} isCorrect - Whether the selected answer is correct
     */
    applyVisualAnswerFeedback(isCorrect) {
        const answerOptions = this.answerForm.querySelectorAll('.answer-option');
        const correctAnswer = this.answerForm.dataset.correctAnswer;
        let selectedOption = null;
        let selectedValue = null;
        
        // First pass - find the selected option
        answerOptions.forEach(option => {
            if (option.classList.contains('selected')) {
                selectedOption = option;
                selectedValue = option.getAttribute('data-answer-value');
            }
        });
        
        if (!selectedOption) return;
        
        // Get the current theme
        const isDarkTheme = document.documentElement.getAttribute('data-bs-theme') === 'dark';
        
        // Second pass - apply styling
        answerOptions.forEach(option => {
            const optionValue = option.getAttribute('data-answer-value');
            const isSelected = option === selectedOption;
            const isCorrectOption = optionValue === correctAnswer;
            
            // Remove hover styling - properly handle both theme styles
            option.classList.remove('border-primary');
            option.querySelector('label').classList.remove('bg-light', 'bg-dark-subtle');
            
            // Replace radio button with appropriate icon for selected/correct answers only
            const customRadio = option.querySelector('.custom-radio-btn');
            if (customRadio) {
                // Get the position and dimensions of the original radio button before modifying it
                customRadio.style.width = '20px';
                customRadio.style.height = '20px'; 
                customRadio.style.position = 'relative';
                customRadio.style.display = 'flex';
                customRadio.style.alignItems = 'center';
                customRadio.style.justifyContent = 'center';
                
                // Only show icons for correct answer or selected wrong answer
                if (isCorrectOption) {
                    // Correct answer icon
                    customRadio.innerHTML = '<i class="bi bi-check-circle-fill text-success"></i>';
                    
                    // Get the icon element and add animation
                    const icon = customRadio.querySelector('i');
                    if (icon) {
                        icon.style.fontSize = '20px';
                        icon.style.position = 'absolute';
                        icon.style.top = '50%';
                        icon.style.left = '50%';
                        icon.style.transform = 'translate(-50%, -50%)';
                        icon.style.animation = 'icon-pop-in 0.3s ease-out forwards';
                    }
                } 
                else if (isSelected && !isCorrect) {
                    // Wrong answer icon
                    customRadio.innerHTML = '<i class="bi bi-x-circle-fill text-danger"></i>';
                    
                    // Get the icon element and add animation
                    const icon = customRadio.querySelector('i');
                    if (icon) {
                        icon.style.fontSize = '20px';
                        icon.style.position = 'absolute';
                        icon.style.top = '50%';
                        icon.style.left = '50%';
                        icon.style.transform = 'translate(-50%, -50%)';
                        icon.style.animation = 'icon-pop-in 0.3s ease-out forwards';
                    }
                }
                else {
                    // For unselected options, just empty the container
                    customRadio.innerHTML = '';
                    customRadio.style.border = 'none';
                }
            }
            
            // Apply different styling based on correctness and selection
            if (isCorrectOption) {
                // Style correct answer with green highlight
                option.classList.add('border-success');
                option.classList.add('bg-success', 'bg-opacity-10');
                
                const label = option.querySelector('label');
                label.classList.add('bg-success', 'bg-opacity-10');
                
                // Add "Correct Answer" badge
                if (!option.querySelector('.correct-answer-badge')) {
                    const badge = document.createElement('div');
                    badge.className = 'position-absolute end-0 top-0 m-2 correct-answer-badge';
                    badge.innerHTML = '<span class="badge bg-success">Correct</span>';
                    option.appendChild(badge);
                }
            } 
            else if (isSelected && !isCorrect) {
                // Style incorrect selected answer with red highlight
                option.classList.add('border-danger');
                option.classList.add('bg-danger', 'bg-opacity-10');
                
                const label = option.querySelector('label');
                label.classList.add('bg-danger', 'bg-opacity-10');
                
                // Add "Your Answer" badge
                if (!option.querySelector('.your-answer-badge')) {
                    const badge = document.createElement('div');
                    badge.className = 'position-absolute end-0 top-0 m-2 your-answer-badge';
                    badge.innerHTML = '<span class="badge bg-danger">Your Answer</span>';
                    option.appendChild(badge);
                }
            }
            
            // For unselected and incorrect options, just gray them out
            if (!isCorrectOption && !isSelected) {
                option.style.opacity = '0.6';
                option.style.filter = 'grayscale(30%)';
            }
            
            // Disable all options
            option.style.pointerEvents = 'none';
        });
    }

    /**
     * Play the appropriate sound effect based on answer correctness
     * @param {boolean} isCorrect - Whether the answer was correct
     */
    playFeedbackSound(isCorrect) {
        try {
            // Stop any currently playing sounds first
            this.successSound.pause();
            this.successSound.currentTime = 0;
            this.errorSound.pause();
            this.errorSound.currentTime = 0;
            
            // Play the appropriate sound
            if (isCorrect) {
                this.successSound.play();
            } else {
                this.errorSound.play();
            }
        } catch (error) {
            // Silently fail if sound playback fails
            console.warn("Sound playback failed:", error);
        }
    }

    /**
     * Initialize segmented milestone progress system
     * @param {number} totalCards - Total number of cards to study
     */
    initializeMilestones(totalCards) {
        if (!this.progressBarContainer || !this.progressMilestones) return;
        
        // Clear existing milestones
        this.progressBarContainer.querySelectorAll('.milestone-marker').forEach(el => el.remove());
        this.progressMilestones.innerHTML = '';
        
        // Use fixed-size segments (e.g., 25 cards per segment)
        this.totalSegments = Math.ceil(totalCards / this.cardsPerSegment);
        this.currentSegment = 0;
        this.totalCards = totalCards;
        
        // Create container for segment info
        const segmentInfoContainer = document.createElement('div');
        segmentInfoContainer.id = 'segmentInfoContainer';
        segmentInfoContainer.className = 'segment-info';
        
        // Add segment progress text
        const segmentProgress = document.createElement('div');
        segmentProgress.id = 'segmentProgress';
        segmentProgress.className = 'segment-progress';
        
        const currentSegmentLabel = document.createElement('div');
        currentSegmentLabel.id = 'currentSegmentLabel';
        currentSegmentLabel.className = 'current-segment-label';
        
        const segmentGoal = document.createElement('div');
        segmentGoal.id = 'segmentGoal';
        segmentGoal.className = 'segment-goal';
        
        // Add elements to page with clearer text indicating segment focus
        segmentInfoContainer.appendChild(segmentProgress);
        this.progressMilestones.appendChild(segmentInfoContainer);
        this.progressMilestones.appendChild(currentSegmentLabel);
        this.progressMilestones.appendChild(segmentGoal);
        
        // Initialize the first segment
        this.updateSegmentDisplay(0, totalCards);
        
        // Create milestone marker for current segment
        this.createSegmentMarker();
        
        console.log(`Initialized ${this.totalSegments} segments of ${this.cardsPerSegment} cards each`);
    }
    
    /**
     * Update the progress bar to show progress within current segment only
     * @param {number} segmentProgress - Progress within current segment
     * @param {number} segmentSize - Total cards in current segment
     */
    updateProgressBar(segmentProgress, segmentSize) {
        if (this.progressBar) {
            // Calculate percentage within segment
            const segmentPercent = segmentSize > 0 ? (segmentProgress / segmentSize) * 100 : 0;
            
            // Update progress bar width to show current segment progress only
            this.progressBar.style.width = `${segmentPercent}%`;
            this.progressBar.setAttribute('aria-valuenow', segmentPercent);
            
            // Add a data attribute to indicate we're showing segment progress
            this.progressBar.dataset.segment = `${this.currentSegment + 1}/${this.totalSegments}`;
        }
    }
    
    /**
     * Update the current segment display
     * @param {number} score - Current score
     * @param {number} totalCards - Total cards in the deck
     */
    updateSegmentDisplay(score, totalCards) {
        this.totalCards = totalCards;
        
        // Calculate which segment we're in
        const completedSegments = Math.floor(score / this.cardsPerSegment);
        
        // Only update display if we've moved to a new segment
        if (completedSegments !== this.currentSegment) {
            // If we completed a segment, show celebration
            if (completedSegments > this.currentSegment) {
                this.celebrateSegmentCompletion(this.currentSegment + 1, this.totalSegments);
            }
            
            // Update current segment
            this.currentSegment = completedSegments;
            
            // Update the marker position
            this.createSegmentMarker();
            
            // Explicitly reset progress bar to 0% for the new segment with animation
            if (this.progressBar) {
                // Add transition class for smooth reset
                this.progressBar.classList.add('resetting-segment');
                this.progressBar.style.width = '0%';
                this.progressBar.setAttribute('aria-valuenow', 0);
                
                // Remove transition class after animation completes
                setTimeout(() => {
                    this.progressBar.classList.remove('resetting-segment');
                }, 300);
            }
        }
        
        // Calculate progress within the current segment
        const segmentStart = this.currentSegment * this.cardsPerSegment;
        const segmentEnd = Math.min((this.currentSegment + 1) * this.cardsPerSegment, totalCards);
        const cardsInSegment = segmentEnd - segmentStart;
        const progressInSegment = score - segmentStart;
        
        // Update segment info display with more informative text
        const segmentProgress = document.getElementById('segmentProgress');
        const currentSegmentLabel = document.getElementById('currentSegmentLabel');
        const segmentGoal = document.getElementById('segmentGoal');
        
        if (segmentProgress) {
            segmentProgress.textContent = `${progressInSegment}/${cardsInSegment}`;
            // Add tooltip for clarity
            segmentProgress.title = `Progress in current segment (${progressInSegment} of ${cardsInSegment} cards)`;
        }
        
        if (currentSegmentLabel) {
            currentSegmentLabel.textContent = `Segment ${this.currentSegment + 1} of ${this.totalSegments}`;
            // Add overall progress as tooltip
            currentSegmentLabel.title = `Overall progress: ${score}/${totalCards} cards (${Math.round((score/totalCards)*100)}%)`;
        }
        
        if (segmentGoal) {
            const remaining = segmentEnd - score;
            if (remaining > 0) {
                segmentGoal.textContent = `${remaining} cards to complete segment`;
            } else if (score === totalCards) {
                segmentGoal.textContent = 'All segments completed!';
                segmentGoal.classList.add('completed-all');
            } else {
                segmentGoal.textContent = 'Ready for next segment!';
            }
        }
        
        // Update the progress bar to show progress within current segment only
        this.updateProgressBar(progressInSegment, cardsInSegment);
    }

    /**
     * Update milestone progress based on current score
     * @param {number} score - Current score/completed cards
     * @param {number} total - Total cards in session
     */
    updateMilestones(score, total) {
        if (!this.progressBarContainer) return;
        
        // Update segment display - this now handles progress bar updates too
        this.updateSegmentDisplay(score, total);
        
        // Ensure segment indicator covers the full progress bar width
        const segmentIndicator = document.getElementById('segmentIndicator');
        if (!segmentIndicator && this.progressBarContainer) {
            const indicator = document.createElement('div');
            indicator.id = 'segmentIndicator';
            indicator.className = 'segment-indicator';
            this.progressBarContainer.appendChild(indicator);
        }
        
        // Update segment indicator to fill entire progress bar
        // since we're now showing only the current segment
        if (segmentIndicator) {
            segmentIndicator.style.left = '0%';
            segmentIndicator.style.width = '100%';
        }
    }
    
    /**
     * Create marker for the current segment
     */
    createSegmentMarker() {
        // Remove existing markers
        this.progressBarContainer.querySelectorAll('.milestone-marker').forEach(el => el.remove());
        
        // Only add a milestone marker at 100%
        const marker = document.createElement('div');
        marker.className = 'milestone-marker';
        marker.style.left = '100%';
        this.progressBarContainer.appendChild(marker);
    }

    /**
     * Show celebration when segment is completed
     * @param {number} segment - Segment number that was completed
     * @param {number} total - Total number of segments
     */
    celebrateSegmentCompletion(segment, total) {
        try {
            // Play achievement sound
            this.celebrationSound.currentTime = 0;
            this.celebrationSound.play().catch(e => console.warn('Could not play celebration sound', e));
        } catch (e) {
            console.warn('Error playing segment completion sound', e);
        }
        
        // Create celebration toast
        const toast = document.createElement('div');
        toast.className = 'milestone-toast';
        
        // Choose celebration message based on progress
        let message;
        if (segment === total) {
            message = 'Final segment completed!';
        } else if (segment / total > 0.75) {
            message = `Great progress! Segment ${segment} completed!`;
        } else if (segment / total > 0.5) {
            message = 'Halfway there! Keep going!';
        } else if (segment / total > 0.25) {
            message = 'Making good progress!';
        } else {
            message = 'First segment completed!';
        }
        
        // Add segment count and overall progress to message
        const segmentCountMsg = `<div class="segment-count mt-1">Segment ${segment}/${total} completed</div>`;
        const overallProgressMsg = `<div class="overall-progress mt-1">${segment * this.cardsPerSegment} of ${this.totalCards} cards total</div>`;
        
        toast.innerHTML = `
            <div class="milestone-icon mb-2"><i class="bi bi-trophy fs-3"></i></div>
            <div class="milestone-message">${message}</div>
            ${segmentCountMsg}
            ${overallProgressMsg}
        `;
        
        document.body.appendChild(toast);
        
        // Add "level-up" animation to the progress bar
        const progressBar = document.getElementById('progressBar');
        if (progressBar) {
            progressBar.classList.add('level-up-pulse');
            setTimeout(() => {
                progressBar.classList.remove('level-up-pulse');
                
                // Reset progress bar to 0% when moving to a new segment
                progressBar.style.width = '0%';
                progressBar.setAttribute('aria-valuenow', 0);
            }, 1000);
        }
        
        // Remove toast after animation completes
        setTimeout(() => {
            toast.remove();
        }, 3500);
    }
}
