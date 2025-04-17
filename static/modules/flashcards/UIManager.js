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

        // Initialize milestone progress bar elements
        this.progressBarContainer = document.getElementById('progressBarContainer');
        this.progressMilestones = document.getElementById('progressMilestones');
        this.milestoneSegments = [];
        this.currentSegment = 0;
        this.cardsPerSegment = 45; // Batch size of 45 cards
        this.celebrationSound = new Audio('/static/sounds/achievement.mp3');
        this.celebrationSound.load();
        
        // Add a map to track which segments have had celebrations shown
        this.celebratedSegments = new Set();

        // Initialize modal for explanations
        this.explanationModal = null;
        
        // Try to initialize the explanation modal if the element exists
        const explanationModalElement = document.getElementById('explanationModal');
        if (explanationModalElement && typeof bootstrap !== 'undefined') {
            try {
                this.explanationModal = new bootstrap.Modal(explanationModalElement, {
                    backdrop: true,
                    keyboard: true,
                    focus: true
                });
                
                // Add explicit event handlers for the close buttons
                const closeXBtn = document.getElementById('explanationCloseX');
                const closeBtn = document.getElementById('explanationCloseBtn');
                
                if (closeXBtn) {
                    closeXBtn.addEventListener('click', (e) => {
                        e.preventDefault();
                        try {
                            this.explanationModal.hide();
                        } catch (err) {
                            console.error('Error hiding modal via X button:', err);
                            // Fallback close method
                            bootstrap.Modal.getInstance(explanationModalElement)?.hide();
                        }
                    });
                }
                
                if (closeBtn) {
                    closeBtn.addEventListener('click', (e) => {
                        e.preventDefault();
                        try {
                            this.explanationModal.hide();
                        } catch (err) {
                            console.error('Error hiding modal via close button:', err);
                            // Fallback close method
                            bootstrap.Modal.getInstance(explanationModalElement)?.hide();
                        }
                    });
                }
                
                // Ensure modal properly closes with keyboard/backdrop
                explanationModalElement.addEventListener('hidden.bs.modal', () => {
                    console.log('Explanation modal hidden');
                });
            } catch (e) {
                console.error('Error initializing explanation modal:', e);
            }
        } else {
            console.warn('Explanation modal element not found or bootstrap not loaded');
        }

        // Initialize toast for feedback
        this.feedbackToast = null;
        this.initializeFeedbackToast();
    }

    renderCard(card) {
        if (!this.flashcardContainer || !card) {
            console.error(`Cannot render card: ${!this.flashcardContainer ? 'flashcardContainer missing' : 'card data missing'}`);
            return;
        }
        
        console.log(`Rendering card ID: ${card.id}, Question: "${card.question?.substring(0, 30)}..."`);
        
        // Make sure card container is visible and exists
        const cardElement = document.getElementById('currentFlashcard');
        if (!cardElement) {
            console.error("currentFlashcard element not found in DOM!");
            
            // Try to restore the structure if we saved it
            if (this._originalStructure) {
                console.log("Attempting to restore flashcard structure");
                const mainContainer = document.getElementById('flashcardsContainer');
                if (mainContainer) {
                    mainContainer.innerHTML = this._originalStructure.html;
                    // Re-get the cardElement after restoration
                    const restoredCard = document.getElementById('currentFlashcard');
                    if (restoredCard) {
                        console.log("Successfully restored flashcard structure");
                        restoredCard.style.display = 'block';
                    }
                }
            }
            
            // Re-check for elements after possible restoration
            const recoveredCardElement = document.getElementById('currentFlashcard');
            if (!recoveredCardElement) {
                console.error("Could not recover currentFlashcard element. Creating from scratch");
                // Last resort: recreate the element structure from scratch
                this.recreateFlashcardStructure();
            }
        } else {
            cardElement.style.display = 'block';
        }
        
        // Set question
        const questionContainer = document.getElementById('questionContainer');
        if (questionContainer) {
            questionContainer.textContent = card.question;
            console.log("Question set in questionContainer");
        } else {
            console.error("questionContainer element not found!");
            // Try to fix by recreating structure
            this.recreateFlashcardStructure();
            // Try again
            const recoveredQuestionContainer = document.getElementById('questionContainer');
            if (recoveredQuestionContainer) {
                recoveredQuestionContainer.textContent = card.question;
                console.log("Question set in recovered questionContainer");
            }
        }
        
        // Clear any previous answers and feedback
        const answerForm = document.getElementById('answerForm');
        if (answerForm) {
            answerForm.innerHTML = '';
            console.log("Cleared answer form");
        } else {
            console.error("answerForm element not found!");
            // If we already tried to recreate the structure, don't do it again
            if (!document.getElementById('questionContainer')) {
                this.recreateFlashcardStructure();
                // Try again
                const recoveredAnswerForm = document.getElementById('answerForm');
                if (recoveredAnswerForm) {
                    recoveredAnswerForm.innerHTML = '';
                    console.log("Cleared recovered answer form");
                }
            }
        }
        
        // Update state badge based on card state
        this.updateStatusBadge(parseInt(card.state || 0));
        
        // Generate and render answer options - make this more robust
        const finalAnswerForm = document.getElementById('answerForm');
        if (finalAnswerForm) {
            this.renderAnswerOptions(card);
            console.log("Card rendering complete");
        } else {
            console.error("Failed to render answer options: answerForm still not available");
        }
    }
    
    renderAnswerOptions(card) {
        if (!this.answerForm || !card) return;
        
        // Reset form - important to clear any existing handlers
        this.answerForm.innerHTML = '';
        
        // Create a container element that prevents form submission
        this.answerForm.onsubmit = (e) => {
            console.log('Prevented direct form submission');
            e.preventDefault();
            e.stopPropagation();
            return false;
        };
        
        // Create shuffled array of all answers
        const allAnswers = [...card.incorrect_answers, card.correct_answer];
        const shuffledAnswers = this.shuffleArray([...allAnswers]);
        
        // Create a container for the answers
        const answersContainer = document.createElement('div');
        answersContainer.className = 'answer-options-container';
        
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
            answerOption.addEventListener('click', (e) => {
                // Explicitly prevent default to avoid form submission
                e.preventDefault();
                e.stopPropagation();
                
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
                
                // Return false to prevent further processing
                return false;
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
            <div class="mt-3 d-flex justify-content-between">
                <button class="btn btn-sm btn-outline-danger" onclick="window.location.reload()">
                    <i class="bi bi-arrow-clockwise me-1"></i> Retry
                </button>
                <button class="btn btn-sm btn-primary" id="continueAnywayBtn">
                    <i class="bi bi-arrow-right me-1"></i> Continue with current cards
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
            if (this.flashcardContainer) {
                this.flashcardContainer.innerHTML = '';
                this.flashcardContainer.appendChild(errorDiv);
            }
        }
        
        // Add event listener to the continue anyway button
        const continueBtn = document.getElementById('continueAnywayBtn');
        if (continueBtn) {
            continueBtn.addEventListener('click', () => {
                // Try to restore the original flashcard content if we have it
                if (this._originalFlashcardContent && this.flashcardContainer) {
                    this.flashcardContainer.innerHTML = this._originalFlashcardContent;
                }
                
                // Try to resume the current card if flashcardManager is available
                if (window.flashcardManager && window.flashcardManager.currentCard) {
                    this.renderCard(window.flashcardManager.currentCard);
                }
            });
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

    /**
     * Updates the card counter display
     */
    updateCardCounter(index, batchTotal, batchScore, batchRemaining, overallCompleted, overallTotal, overallRemaining) {
        // Update the score and remaining counts with accurate numbers
        const scoreCountElement = document.getElementById('scoreCount');
        
        if (scoreCountElement) {
            scoreCountElement.textContent = batchScore;
        }
        
        // Update the full card counter text if it exists
        if (this.cardCounter) {
            // Show batch progress and overall progress
            this.cardCounter.innerHTML = `
                <span class="badge bg-light text-dark me-1">${batchScore}/${batchTotal}</span> in batch 
                (<span id="totalCount">${overallTotal}</span> total)
            `;
        }
    }

    /**
     * Update the score display and progress indicators
     */
    updateScore(batchScore, batchTotal, overallScore, overallTotal) {
        // Calculate what percentage of the overall deck is complete
        const overallPercent = Math.round((overallScore / overallTotal) * 100);
        
        // Calculate what percentage of the current batch is complete
        const batchPercent = Math.round((batchScore / batchTotal) * 100);
        
        // Update milestone progress - this now handles progress bar updates too
        this.updateMilestones(batchScore, batchTotal, overallScore, overallTotal);
        
        // Update the completed count immediately
        const completedCount = document.getElementById('completedCount');
        if (completedCount) {
            completedCount.textContent = overallScore;
        }
        
        // Update the overall progress display
        const overallProgressBar = document.getElementById('overallProgressBar');
        if (overallProgressBar) {
            overallProgressBar.style.width = `${overallPercent}%`;
            overallProgressBar.setAttribute('aria-valuenow', overallPercent);
            overallProgressBar.textContent = `${overallPercent}%`;
        }
    }

    showBriefFeedback(isCorrect) {
        this.showToastFeedback(isCorrect);
    }

    showAnswerFeedback(isCorrect, nextCardCallback) {
        this.showToastFeedback(isCorrect, nextCardCallback);
    }

    /**
     * Show explanation in a modal
     * @param {string} flashcardId - The ID of the current flashcard
     */
    showExplanationModal(flashcardId) {
        // Check if modal exists
        if (!this.explanationModal) {
            const modalElement = document.getElementById('explanationModal');
            if (modalElement && typeof bootstrap !== 'undefined') {
                try {
                    this.explanationModal = new bootstrap.Modal(modalElement, {
                        backdrop: true,
                        keyboard: true,
                        focus: true
                    });
                    
                    // Re-attach event handlers to close buttons
                    const closeXBtn = document.getElementById('explanationCloseX');
                    const closeBtn = document.getElementById('explanationCloseBtn');
                    
                    const hideModal = (e) => {
                        e.preventDefault();
                        try {
                            this.explanationModal.hide();
                        } catch (err) {
                            console.error('Error hiding modal:', err);
                            // Fallback close method
                            bootstrap.Modal.getInstance(modalElement)?.hide();
                        }
                    };
                    
                    if (closeXBtn) closeXBtn.addEventListener('click', hideModal);
                    if (closeBtn) closeBtn.addEventListener('click', hideModal);
                    
                } catch (e) {
                    console.error('Cannot initialize explanation modal:', e);
                    return;
                }
            } else {
                console.error('Cannot show explanation: modal element not found or bootstrap not loaded');
                return;
            }
        }
        
        // Get the correct answer from the current card before fetching the explanation
        let correctAnswer = null;
        if (window.flashcardManager && window.flashcardManager.currentCard) {
            correctAnswer = window.flashcardManager.currentCard.correct_answer;
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
        try {
            this.explanationModal.show();
        } catch (e) {
            console.error('Error showing explanation modal:', e);
            return;
        }
        
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
            
            // Check if explanation data exists and modal is still open
            if (contentElement) {
                contentElement.classList.remove('d-none');
                
                // Use the correct answer from the current card if not provided in the response
                const displayCorrectAnswer = data.correct_answer || correctAnswer || 'Not provided';
                
                if (data.explanation) {
                    // Format the explanation with proper styling
                    contentElement.innerHTML = `
                        <div class="explanation-content">
                            <div class="correct-answer mb-3">
                                <h6 class="text-muted mb-1">Correct Answer:</h6>
                                <div class="p-2 bg-success bg-opacity-10 border border-success rounded">
                                    ${displayCorrectAnswer}
                                </div>
                            </div>
                            <div class="explanation-text">
                                <h6 class="text-muted mb-1">Why This Is Correct:</h6>
                                <div class="rounded">
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
                            <p>No detailed explanation is available for this question.</p>
                            <hr>
                            <p class="mb-0"><strong>Correct Answer:</strong> ${displayCorrectAnswer}</p>
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

    showCompletionScreenLegacy(deckId, score, totalDue, isDueOnly, remainingDueCards) {
        // This method is kept for backward compatibility but not used
        console.warn('showCompletionScreen is deprecated, use showFinalCompletion instead');
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
     * Initialize the feedback toast
     */
    initializeFeedbackToast() {
        const toastElement = document.getElementById('feedbackToast');
        if (toastElement && typeof bootstrap !== 'undefined') {
            this.feedbackToast = new bootstrap.Toast(toastElement, {
                autohide: true,
                delay: 1000
            });
        }
    }

    /**
     * Show a toast notification for feedback
     * @param {boolean} isCorrect - Whether the answer was correct
     * @param {Function} nextCardCallback - Callback for next card button (for incorrect answers)
     */
    showToastFeedback(isCorrect, nextCardCallback = null) {
        // Apply visual feedback to the selected answer (keep this)
        this.applyVisualAnswerFeedback(isCorrect);
        
        // Play appropriate sound based on correctness
        this.playFeedbackSound(isCorrect);
        
        // Get toast elements
        const toast = document.getElementById('feedbackToast');
        const toastHeader = document.getElementById('feedbackToastHeader');
        const toastIcon = document.getElementById('feedbackToastIcon');
        const toastTitle = document.getElementById('feedbackToastTitle');
        const toastBody = document.getElementById('feedbackToastBody');
        
        if (!toast || !toastHeader || !toastIcon || !toastTitle || !toastBody) {
            console.warn('Toast elements not found');
            return;
        }
        
        // Style toast based on correctness - simplified to match milestone toast
        toast.className = `toast ${isCorrect ? 'border-success' : 'border-danger'}`;
        toastHeader.className = 'toast-header';
        
        // Set the icon and title
        toastIcon.innerHTML = isCorrect 
            ? '<i class="bi bi-check-circle-fill"></i>' 
            : '<i class="bi bi-x-circle-fill"></i>';
        toastTitle.textContent = isCorrect ? 'Correct!' : 'Incorrect';
        
        // Add content to toast body
        if (isCorrect) {
            toastBody.innerHTML = `
                <p class="mb-0">Great job! Moving to next card...</p>
            `;
        } else {
            toastBody.innerHTML = `
                <p class="mb-0">Try to remember this card for next time.</p>
            `;
        }
        
        // Show the toast
        if (this.feedbackToast) {
            this.feedbackToast.show();
        } else {
            // Fallback: try to initialize again
            this.initializeFeedbackToast();
            if (this.feedbackToast) {
                this.feedbackToast.show();
            }
        }
        
        // Keep inline buttons for keyboard navigation
        const minimalButtons = document.createElement('div');
        minimalButtons.className = 'd-flex justify-content-center gap-2 mt-3';
        minimalButtons.innerHTML = `
            <button id="explainFlashcardBtn" class="btn btn-outline-secondary" type="button">
                <i class="bi bi-lightbulb me-2"></i> Explain
            </button>
            <button id="nextQuestionBtn" class="btn btn-primary" type="button">
                <i class="bi bi-arrow-right me-2"></i> Next
            </button>
        `;
        this.answerForm.appendChild(minimalButtons);
        
        // Make sure the buttons have type="button" to avoid form submission
        
        // Add event listeners to new buttons with explicit preventDefault
        const explainBtn = document.getElementById('explainFlashcardBtn');
        const nextBtn = document.getElementById('nextQuestionBtn');
        
        if (explainBtn) {
            explainBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const flashcardId = this.getCurrentFlashcardId();
                if (flashcardId) {
                    this.showExplanationModal(flashcardId);
                }
                return false;
            });
        }
        
        if (nextBtn && typeof nextCardCallback === 'function') {
            nextBtn.addEventListener('click', (e) => {
                e.preventDefault();
                nextCardCallback();
                return false;
            });
            // Focus the next button for keyboard navigation
            setTimeout(() => nextBtn.focus(), 100);
        }
    }

    /**
     * Initialize segmented milestone progress system
     * @param {number} totalCards - Total number of cards to study
     * @param {number} batchSize - Number of cards per batch
     */
    initializeMilestones(totalCards, batchSize) {
        if (!this.progressBarContainer || !this.progressMilestones) return;
        
        // Clear existing milestones
        this.progressBarContainer.querySelectorAll('.milestone-marker').forEach(el => el.remove());
        this.progressMilestones.innerHTML = '';
        
        // Store these values 
        this.cardsPerSegment = batchSize || 45;
        this.totalSegments = Math.ceil(totalCards / this.cardsPerSegment);
        this.currentSegment = 0;
        this.totalCards = totalCards;
        
        // Create a cleaner, centered layout with just the batch information
        const progressDisplay = document.createElement('div');
        progressDisplay.className = 'd-flex justify-content-center w-100';
        
        // Create centered batch label
        const currentSegmentLabel = document.createElement('div');
        currentSegmentLabel.id = 'currentSegmentLabel';
        currentSegmentLabel.className = 'current-segment-label text-center';
        
        // Add elements to the layout
        progressDisplay.appendChild(currentSegmentLabel);
        
        // Add elements to page
        this.progressMilestones.appendChild(progressDisplay);
        
        // Initialize the first segment
        this.updateSegmentDisplay(0, this.cardsPerSegment, 0, totalCards);
        
        // Create milestone marker for current segment
        this.createSegmentMarker();
        
        console.log(`Initialized ${this.totalSegments} batches of ${this.cardsPerSegment} cards each (total: ${totalCards})`);
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
     * Update the progress bar to show progress within current segment only
     * @param {number} segmentProgress - Progress within current batch
     * @param {number} segmentSize - Total cards in current batch
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
     * @param {number} batchScore - Score in current batch
     * @param {number} batchSize - Size of current batch
     * @param {number} overallScore - Overall completed cards
     * @param {number} totalCards - Total cards in the deck
     */
    updateSegmentDisplay(batchScore, batchSize, overallScore, totalCards) {
        // Store total cards
        this.totalCards = totalCards;
        
        // Calculate which batch we're on
        const completedSegments = Math.floor(overallScore / this.cardsPerSegment);
        
        // Update current segment if changed
        if (completedSegments !== this.currentSegment) {
            // If we completed a segment, show celebration
            if (completedSegments > this.currentSegment) {
                this.celebrateSegmentCompletion(completedSegments, this.totalSegments);
            }
            
            // Update current segment
            this.currentSegment = completedSegments;
            
            // Update the marker position
            this.createSegmentMarker();
        }
        
        // Update segment info display with combined batch and overall progress
        const currentSegmentLabel = document.getElementById('currentSegmentLabel');
        
        if (currentSegmentLabel) {
            currentSegmentLabel.textContent = `Batch ${completedSegments + 1} of ${this.totalSegments}`;
            currentSegmentLabel.title = `Overall progress: ${overallScore} of ${totalCards} cards (${batchScore}/${batchSize} in current batch)`;
        }
        
        // Update the progress bar for the current batch
        this.updateProgressBar(batchScore, batchSize);
    }

    /**
     * Update milestone progress based on current score
     * @param {number} batchScore - Score in current batch
     * @param {number} batchTotal - Total cards in current batch
     * @param {number} overallScore - Overall completed cards
     * @param {number} overallTotal - Total cards in all batches
     */
    updateMilestones(batchScore, batchTotal, overallScore, overallTotal) {
        if (!this.progressBarContainer) return;
        
        // Update segment display with both batch and overall progress
        this.updateSegmentDisplay(batchScore, batchTotal, overallScore, overallTotal);
    }

    /**
     * Reset progress display for a new batch
     * @param {number} batchNumber - Current batch number
     * @param {number} totalBatches - Total number of batches
     */
    resetProgressForNewBatch(batchNumber, totalBatches) {
        // Reset progress bar to 0%
        if (this.progressBar) {
            this.progressBar.style.width = '0%';
            this.progressBar.setAttribute('aria-valuenow', 0);
        }
        
        // Update segment label
        const currentSegmentLabel = document.getElementById('currentSegmentLabel');
        if (currentSegmentLabel) {
            currentSegmentLabel.textContent = `Batch ${batchNumber} of ${totalBatches}`;
            currentSegmentLabel.title = `Starting batch ${batchNumber} of ${totalBatches}`;
        }
        
        // Reset segment progress
        const segmentProgress = document.getElementById('segmentProgress');
        if (segmentProgress) {
            segmentProgress.textContent = `0/${this.cardsPerSegment}`;
        }
    }

    /**
     * Show loading indicator for next batch
     */
    showBatchLoading() {
        // Hide the current flashcard
        const currentFlashcard = document.getElementById('currentFlashcard');
        if (currentFlashcard) {
            currentFlashcard.style.display = 'none';
        }
        
        // Hide the batch completion screen
        const batchCompletionScreen = document.getElementById('batchCompletionScreen');
        if (batchCompletionScreen) {
            batchCompletionScreen.style.display = 'none';
        }
        
        // Show loading indicator
        const loadingContainer = document.getElementById('loadingContainer');
        if (loadingContainer) {
            loadingContainer.style.display = 'block';
        }
        
        // Disable the next batch button
        const loadNextBatchBtn = document.getElementById('loadNextBatchBtn');
        if (loadNextBatchBtn) {
            loadNextBatchBtn.disabled = true;
            const normalState = loadNextBatchBtn.querySelector('.normal-state');
            const loadingState = loadNextBatchBtn.querySelector('.loading-state');
            if (normalState && loadingState) {
                normalState.classList.add('d-none');
                loadingState.classList.remove('d-none');
            }
        }
    }

    /**
     * Show final completion screen when all cards are done
     */
    showFinalCompletion(deckId, score, totalDue, isDueOnly, remainingDueCards) {
        // Get the final completion screen
        const finalCompletionScreen = document.getElementById('finalCompletionScreen');
        if (!finalCompletionScreen) return;
        
        // Calculate completion percentage
        const completionPercent = Math.round((score / totalDue) * 100);
        
        // Create different completion screens depending on the mode and whether there are more due cards
        if (isDueOnly && remainingDueCards > 0) {
            // Due Only mode with more cards due - show option to start a new session
            finalCompletionScreen.innerHTML = `
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
                        <i class="bi bi-arrow-right"></i> Start New Session
                    </a>
                    <a href="/deck/${deckId}" class="btn btn-outline-secondary">
                        <i class="bi bi-house-door"></i> Back to Deck
                    </a>
                </div>
            `;
        } else if (isDueOnly) {
            // Due Only mode with no more cards due - show standard completion with dropdown
            finalCompletionScreen.innerHTML = `
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
            `;
        } else {
            // Study All mode - show standard completion with session stats
            finalCompletionScreen.innerHTML = `
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
                                <a href="/deck/study/${deckId}" class="dropdown-item">
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
            `;
        }

        // Show final completion screen
        finalCompletionScreen.style.display = 'block';

        // Update badge to show completion status
        if (this.statusBadge) {
            this.statusBadge.textContent = 'Completed';
            this.statusBadge.className = 'badge bg-success';
        }
    }

    /**
     * Show celebration when segment is completed
     * @param {number} segment - Batch number that was completed
     * @param {number} total - Total number of batches
     */
    celebrateSegmentCompletion(segment, total) {
        // Check if we've already celebrated this segment to avoid duplicates
        if (this.celebratedSegments.has(segment)) {
            console.log(`Segment ${segment} celebration already shown, skipping duplicate`);
            return;
        }
        
        // Add this segment to celebrated set to prevent duplicates
        this.celebratedSegments.add(segment);
        
        console.log(`Celebrating completion of segment ${segment}/${total}`);
        
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
        toast.style.zIndex = "9999"; // Ensure it's on top of all other elements
        toast.style.top = "20px";    // Position at top
        toast.style.right = "20px";  // Position at right
        toast.style.transform = "none"; // Remove any centering transform
        
        // Choose celebration message based on progress
        let message;
        if (segment === total) {
            message = 'Final batch completed!';
        } else if (segment / total > 0.75) {
            message = `Great progress! Batch ${segment} completed!`;
        } else if (segment / total > 0.5) {
            message = 'Halfway there! Keep going!';
        } else if (segment / total > 0.25) {
            message = 'Making good progress!';
        } else {
            message = 'First batch completed!';
        }
        
        // Add segment count and next segment message
        const segmentCountMsg = `<div class="segment-count mt-1">Batch ${segment}/${total} completed</div>`;
        
        toast.innerHTML = `
            <div class="milestone-icon mb-2"><i class="bi bi-trophy fs-3"></i></div>
            <div class="milestone-message">${message}</div>
            ${segmentCountMsg}
            <div class="mt-2">Ready for next batch!</div>
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

    /**
     * Show loading message between segments
     * @param {string} message - The loading message to display
     */
    showLoadingMessage(message) {
        // Get the main container (parent of flashcardContainer)
        const mainContainer = document.getElementById('flashcardsContainer');
        if (!mainContainer) return;
        
        console.log(`Showing loading message: "${message}"`);
        
        // Store original structure if not already stored
        if (!this._originalFlashcardContent) {
            console.log("Storing original flashcard structure for restoration");
            this._originalStructure = {
                html: mainContainer.innerHTML
            };
        }
        
        // Hide the current flashcard but don't remove it
        const currentFlashcard = document.getElementById('currentFlashcard');
        if (currentFlashcard) {
            currentFlashcard.style.display = 'none';
            console.log("Hidden currentFlashcard element during loading");
        }
        
        // Create loading element outside the flashcard container
        const loadingElement = document.createElement('div');
        loadingElement.className = 'segment-loading text-center p-4';
        loadingElement.innerHTML = `
            <div class="spinner-border text-primary mb-3" role="status" style="width: 3rem; height: 3rem;">
                <span class="visually-hidden">Loading</span>
            </div>
            <p class="fw-bold fs-5">${message}</p>
            <p class="text-muted">Loading more flashcards for continued study...</p>
            <div class="progress mt-3" style="height: 8px;">
                <div class="progress-bar progress-bar-striped progress-bar-animated" 
                     role="progressbar" style="width: 100%"></div>
            </div>
            <p class="small text-muted mt-3">Please wait, your progress is being saved</p>
        `;
        
        // Add loading element to the main container
        mainContainer.appendChild(loadingElement);
        console.log("Loading message HTML inserted into container");
    }

    /**
     * Hide loading message between segments
     * @param {boolean} isSegmentTransition - Whether we're transitioning between segments
     */
    hideLoadingMessage(isSegmentTransition = false) {
        // Get the main container
        const mainContainer = document.getElementById('flashcardsContainer');
        if (!mainContainer) return;
        
        console.log(`Hiding loading message. isSegmentTransition=${isSegmentTransition}`);
        
        // Remove any loading message elements
        const loadingMessage = mainContainer.querySelector('.segment-loading');
        if (loadingMessage) {
            console.log('Found .segment-loading element, removing it');
            loadingMessage.remove();
        } else {
            console.log('No .segment-loading element found to remove');
        }
        
        // Make sure the current flashcard element exists and is visible
        let currentCard = document.getElementById('currentFlashcard');
        
        if (!currentCard && this._originalStructure) {
            console.log('currentFlashcard element not found, restoring from saved structure');
            
            // Restore the entire original structure
            mainContainer.innerHTML = this._originalStructure.html;
            
            // Get the current flashcard element again after restoration
            currentCard = document.getElementById('currentFlashcard');
        }
        
        if (currentCard) {
            console.log('Making currentFlashcard visible');
            currentCard.style.display = 'block';
        } else {
            console.error('currentFlashcard element not found and could not be restored!');
        }
    }

    /**
     * Recreate the flashcard structure if it's missing
     * This is a fallback recovery method
     */
    recreateFlashcardStructure() {
        console.log("Recreating flashcard structure from scratch");
        
        const flashcardsContainer = document.getElementById('flashcardsContainer');
        if (!flashcardsContainer) {
            console.error("Cannot recreate structure: flashcardsContainer not found");
            return;
        }
        
        // First, check if we have already tried to recreate it
        if (document.getElementById('currentFlashcard')) {
            return; // Already exists
        }
        
        // Template based on the structure in flashcards.html
        const template = `
            <div id="currentFlashcard" class="card flashcard mb-4">
                <div class="card-body">
                    <span id="statusBadge" class="badge position-absolute top-0 start-0 m-3 compact-status-badge">New</span>
                    <div id="questionContainer" class="card-title h4 mt-4"></div>
                    <form id="answerForm" class="answer-form mt-4">
                        <!-- Answer options will be dynamically inserted here -->
                    </form>
                </div>
            </div>
        `;
        
        // Clear the container and add the template
        flashcardsContainer.innerHTML = template;
        
        // Update our reference to the flashcard container
        this.flashcardContainer = document.getElementById('currentFlashcard');
        this.questionContainer = document.getElementById('questionContainer');
        this.answerForm = document.getElementById('answerForm');
        
        console.log("Flashcard structure recreated");
    }
}
