document.addEventListener('DOMContentLoaded', function() {
    // Form submission handler
    const generateForm = document.getElementById('generateForm');
    if (generateForm) {
        generateForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            
            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                if (data.success) {
                    window.location.href = data.redirect_url; // Redirect to the URL provided in the response
                }
            } catch (error) {
                console.error('Error generating flashcards:', error);
                // Fallback to regular form submission if AJAX fails
                generateForm.submit();
            }
        });
    }

    const flashcardsContainer = document.getElementById('flashcardsContainer');
    if (!flashcardsContainer) return;

    let currentCardIndex = 0;
    let score = 0;
    let flashcardsArray = Array.from(document.querySelectorAll('.flashcard')); // Convert NodeList to Array

    function initializeFlashcard(flashcard) {
        const answersForm = flashcard.querySelector('.answer-form');
        const correctAnswer = flashcard.dataset.correct;
        const incorrectAnswers = JSON.parse(flashcard.dataset.incorrect);
        
        // Combine and shuffle answers
        const allAnswers = [correctAnswer, ...incorrectAnswers];
        shuffleArray(allAnswers);
        
        // Create answer options
        answersForm.innerHTML = allAnswers.map((answer, index) => `
            <div class="answer-option">
                <input type="radio" id="${flashcard.dataset.id}-${index}" 
                       name="flashcard-${flashcard.dataset.id}" value="${answer}">
                <label for="${flashcard.dataset.id}-${index}">
                    <span class="key-hint">${index + 1}</span>${answer}
                </label>
            </div>
        `).join('');

        // Add click handlers for radio buttons
        answersForm.querySelectorAll('input[type="radio"]').forEach(radio => {
            radio.addEventListener('click', function() {
                handleAnswer(this.value, flashcard);
            });
        });
    }

    function shuffleArray(array) {
        for (let i = array.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [array[i], array[j]] = [array[j], array[i]];
        }
        return array;
    }

    function updateProgress(flashcardId, isCorrect) {
        fetch('/update_progress', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                flashcard_id: flashcardId,
                is_correct: isCorrect
            })
        });
    }

    function handleAnswer(selectedAnswer, flashcard) {
        const correctAnswer = flashcard.dataset.correct;
        const isCorrect = selectedAnswer === correctAnswer;
        
        updateProgress(flashcard.dataset.id, isCorrect);

        // Visual feedback
        const feedback = document.createElement('div');
        feedback.classList.add('feedback');
        feedback.textContent = isCorrect ? '✓ Correct!' : '✗ Incorrect - Will review again later';
        feedback.classList.add(isCorrect ? 'correct' : 'incorrect');
        
        const existingFeedback = flashcard.querySelector('.feedback');
        if (existingFeedback) {
            existingFeedback.remove();
        }
        
        flashcard.querySelector('.answer-form').appendChild(feedback);

        setTimeout(() => {
            if (isCorrect) {
                score++;
                document.getElementById('score').textContent = score;
                
                // Check if all cards have been answered correctly
                if (score === flashcardsArray.length) {
                    showCompletion();
                } else {
                    // Keep the card in array but mark it as completed
                    flashcard.dataset.completed = 'true';
                    showNextRemainingCard();
                }
            } else {
                // Move incorrect card to end
                moveCardToEnd(flashcard);
                showNextRemainingCard();
            }
        }, 1500);
    }

    function moveCardToEnd(flashcard) {
        flashcardsContainer.appendChild(flashcard);
        // Reset the radio buttons
        flashcard.querySelectorAll('input[type="radio"]').forEach(radio => {
            radio.checked = false;
        });
        // Update array order
        flashcardsArray = Array.from(document.querySelectorAll('.flashcard'));
    }

    function showNextRemainingCard() {
        currentCardIndex++;
        if (currentCardIndex >= flashcardsArray.length) {
            currentCardIndex = 0;
        }
        
        // Skip completed cards
        while (currentCardIndex < flashcardsArray.length && 
               flashcardsArray[currentCardIndex].dataset.completed === 'true') {
            currentCardIndex++;
            if (currentCardIndex >= flashcardsArray.length) {
                currentCardIndex = 0;
            }
        }
        
        showCard(currentCardIndex);
    }

    function showCompletion() {
        const container = document.getElementById('flashcardsContainer');
        container.innerHTML = `
            <div class="completion-message">
                <h2>🎉 Congratulations!</h2>
                <p>You've successfully completed all flashcards.</p>
                <p>Final Score: ${score}/${flashcardsArray.length}</p>
                <a href="${window.location.href}" class="button">Study Again</a>
                <a href="/" class="button">Back to Topics</a>
            </div>
        `;
    }

    // Navigation functions
    function showCard(index) {
        // Hide all cards and remove active class
        flashcardsArray.forEach(card => {
            card.style.display = 'none';
            card.classList.remove('active');
        });

        // Show and activate current card
        const currentCard = flashcardsArray[index];
        if (currentCard) {
            currentCard.style.display = 'block';
            currentCard.classList.add('active');
            
            // Update the card counter
            const remaining = flashcardsArray.length - score;
            document.getElementById('cardNumber').textContent = 
                `Card ${index + 1} of ${flashcardsArray.length} (${remaining} remaining)`;
        }
    }

    function showNextCard() {
        if (currentCardIndex < flashcardsArray.length - 1) {
            currentCardIndex++;
            showCard(currentCardIndex);
        }
    }

    function showPrevCard() {
        if (currentCardIndex > 0) {
            currentCardIndex--;
            showCard(currentCardIndex);
        }
    }

    // Make sure initialization happens at the end
    // Initialize flashcards and event listeners
    flashcardsArray.forEach(initializeFlashcard);
    
    // Initialize the first card explicitly
    if (flashcardsArray.length > 0) {
        showCard(0);
    }

    // Add event listeners after initialization
    document.getElementById('nextCard').addEventListener('click', showNextCard);
    document.getElementById('prevCard').addEventListener('click', showPrevCard);

    // Keyboard navigation
    document.addEventListener('keydown', function(e) {
        const currentCard = document.querySelector('.flashcard[style*="display: block"]');
        if (!currentCard) return;

        const answers = Array.from(currentCard.querySelectorAll('.answer-option'));
        
        switch(e.key) {
            case '1':
            case '2':
            case '3':
            case '4':
                const index = parseInt(e.key) - 1;
                if (index < answers.length) {
                    const radio = answers[index].querySelector('input[type="radio"]');
                    if (!radio.checked) {
                        radio.checked = true;
                        handleAnswer(radio.value, currentCard);
                    }
                }
                break;
            case 'ArrowRight':
                showNextCard();
                break;
            case 'ArrowLeft':
                showPrevCard();
                break;
        }
    });

    // Initialize the first card
    showCard(0);
});