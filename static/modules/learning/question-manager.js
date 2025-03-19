/**
 * Question manager for displaying and handling learning questions
 */

import { showLoading, hideLoading, displayError } from './ui-utils.js';
import { updateSectionStatusInSidebar } from './ui-utils.js';

// Add sound effect audio objects
const correctSound = new Audio('/static/sounds/success.mp3');
const incorrectSound = new Audio('/static/sounds/error.mp3');

/**
 * Mark content as read and show questions
 * @param {number} sectionId - The section ID
 * @returns {Promise<Array>} - The questions array if successful
 */
export async function markContentReadAndShowQuestions(sectionId) {
    if (!sectionId) return;
    
    showLoading('Preparing questions...');
    
    try {
        const response = await fetch(`/learning/api/section/${sectionId}/mark-read`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to process');
        }
        
        const data = await response.json();
        
        if (data.success) {
            return data.questions;
        } else {
            throw new Error(data.error || 'Failed to generate questions');
        }
    } catch (error) {
        console.error('Error preparing questions:', error);
        displayError('Failed to prepare questions. Please try again.');
        throw error;
    } finally {
        hideLoading();
    }
}

/**
 * Display a question in the dynamic content area
 * @param {Object} question - The question data
 * @param {Function} onAnswered - Callback function when question is answered
 */
export function displayQuestion(question, onAnswered) {
    const contentArea = document.getElementById('dynamicContentArea');
    const template = document.getElementById('questionTemplate');
    const content = template.content.cloneNode(true);
    
    // Set question text and ID
    const questionItem = content.querySelector('.question-item');
    questionItem.dataset.questionId = question.id;
    content.querySelector('.question-text').textContent = question.question;
    
    // Create answer options container
    const optionsContainer = content.querySelector('.answer-options');
    optionsContainer.className = 'answer-options d-flex flex-column gap-2 mb-4';
    
    // Combine all answers into one array for consistent processing
    const allAnswers = [
        { text: question.correct_answer, isCorrect: true },
        ...question.incorrect_answers.map(answer => ({ text: answer, isCorrect: false }))
    ];
    
    // Shuffle answers
    const shuffledAnswers = shuffleArray([...allAnswers]);
    
    // Create answer options with UIManager.js style
    shuffledAnswers.forEach((answer, index) => {
        const option = document.createElement('div');
        option.className = 'answer-option position-relative p-3 rounded border d-flex justify-content-between align-items-center';
        option.setAttribute('data-correct', answer.isCorrect.toString());
        option.setAttribute('data-answer', answer.text);
        option.setAttribute('data-option-num', (index + 1).toString());
        
        // Create left side with option number and text
        const leftSide = document.createElement('div');
        leftSide.className = 'd-flex align-items-center';
        
        // Add option number badge
        const optionNum = document.createElement('span');
        optionNum.className = 'option-num me-3';
        optionNum.textContent = (index + 1).toString();
        leftSide.appendChild(optionNum);
        
        // Add answer text
        const textSpan = document.createElement('span');
        textSpan.className = 'answer-text';
        textSpan.textContent = answer.text;
        leftSide.appendChild(textSpan);
        
        option.appendChild(leftSide);
        
        // Create right side for feedback icons (initially hidden)
        const rightSide = document.createElement('div');
        rightSide.className = 'answer-icon';
        
        // Create check mark for correct answers
        if (answer.isCorrect) {
            const checkIcon = document.createElement('i');
            checkIcon.className = 'bi bi-check-circle-fill text-success';
            checkIcon.style.opacity = '0';
            rightSide.appendChild(checkIcon);
        } else {
            // Create X mark for incorrect answers
            const xIcon = document.createElement('i');
            xIcon.className = 'bi bi-x-circle-fill text-danger';
            xIcon.style.opacity = '0';
            rightSide.appendChild(xIcon);
        }
        
        option.appendChild(rightSide);
        optionsContainer.appendChild(option);
    });
    
    // Add click handlers to answer options
    content.querySelectorAll('.answer-option').forEach(option => {
        option.addEventListener('click', async (event) => {
            await handleAnswerSelection(event, onAnswered);
        });
    });
    
    // Add keyboard navigation for answer selection and next question
    enableAnswerKeyboardNavigation(onAnswered);
    
    // Set up next button
    const nextButton = content.querySelector('#nextQuestionBtn');
    if (nextButton) {
        nextButton.addEventListener('click', () => {
            if (typeof onAnswered === 'function') {
                onAnswered();
            }
        });
    }
    
    // Clear existing content and append new content
    contentArea.innerHTML = '';
    contentArea.appendChild(content);
    
    // Add hint about keyboard shortcuts
    const keyboardHint = document.createElement('div');
    keyboardHint.className = 'keyboard-hints text-muted small';
    keyboardHint.innerHTML = 'Tip: Use number keys 1-4 to select answers';
    contentArea.appendChild(keyboardHint);
}

/**
 * Shuffle array elements using Fisher-Yates algorithm
 * @param {Array} array - The array to shuffle
 * @returns {Array} - The shuffled array
 */
function shuffleArray(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
    return array;
}

/**
 * Enable keyboard navigation for answering questions and proceeding to next question
 * @param {Function} onAnswered - Callback for when the next button is triggered
 */
function enableAnswerKeyboardNavigation(onAnswered) {
    // Remove any existing keydown handlers first
    document.removeEventListener('keydown', handleKeyNavigation);
    document.removeEventListener('keydown', handleAnswerKeyNavigation);
    
    // Add the answer selection handler
    document.addEventListener('keydown', handleAnswerKeyNavigation);
    
    // Store the callback in a global variable to make it accessible to the handler
    window._nextQuestionCallback = onAnswered;
}

/**
 * Handle keyboard navigation for answer selection
 * @param {KeyboardEvent} event - The keyboard event
 */
function handleAnswerKeyNavigation(event) {
    // Only proceed if an answer hasn't been selected yet
    if (document.querySelector('.answer-option.selected, .answer-option.correct, .answer-option.incorrect')) {
        // If an answer is already selected, switch to the next question handler
        document.removeEventListener('keydown', handleAnswerKeyNavigation);
        document.addEventListener('keydown', handleKeyNavigation);
        return;
    }
    
    // Skip if user is typing in an input field
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
        return;
    }
    
    // Check if a number key 1-4 was pressed
    const num = parseInt(event.key);
    if (num >= 1 && num <= 4) {
        // Find the corresponding option
        const option = document.querySelector(`.answer-option[data-option-num="${num}"]`);
        if (option) {
            // Simulate click on this option
            option.click();
            
            // Add visual feedback
            option.classList.add('keyboard-selected');
            setTimeout(() => option.classList.remove('keyboard-selected'), 200);
            
            // Switch to next question handler
            document.removeEventListener('keydown', handleAnswerKeyNavigation);
            document.addEventListener('keydown', handleKeyNavigation);
        }
    }
}

/**
 * Handle keyboard navigation for next question
 * @param {KeyboardEvent} event - The keyboard event
 */
function handleKeyNavigation(event) {
    // Only proceed if the next button is visible
    const nextButtonContainer = document.getElementById('nextButtonContainer');
    if (nextButtonContainer && !nextButtonContainer.classList.contains('d-none')) {
        // Skip if user is typing in an input field
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
            return;
        }
        
        // Any key will trigger the next question
        const nextButton = document.getElementById('nextQuestionBtn');
        if (nextButton && !nextButton.disabled) {
            console.log('Key pressed - advancing to next question');
            
            // Execute the stored callback directly instead of clicking the button
            if (typeof window._nextQuestionCallback === 'function') {
                // Remove the event listeners before proceeding
                document.removeEventListener('keydown', handleKeyNavigation);
                document.removeEventListener('keydown', handleAnswerKeyNavigation);
                
                // Call the callback function
                window._nextQuestionCallback();
            } else {
                // Fallback to clicking the button if callback isn't available
                nextButton.click();
            }
        }
    }
}

/**
 * Handle when a user selects an answer
 * @param {Event} event - The click event
 * @param {Function} onComplete - Callback for when answer is recorded
 */
async function handleAnswerSelection(event, onComplete) {
    const option = event.currentTarget;
    if (option.classList.contains('selected') || 
        option.classList.contains('correct') || 
        option.classList.contains('incorrect')) {
        return; // Already answered
    }
    
    // Select this option
    document.querySelectorAll('.answer-option').forEach(opt => 
        opt.classList.remove('selected'));
    option.classList.add('selected');
    
    // Get question data
    const isCorrect = option.getAttribute('data-correct') === 'true';
    const questionItem = option.closest('.question-item');
    const questionId = questionItem.dataset.questionId;
    const answerValue = option.getAttribute('data-answer');
    
    // Play appropriate sound effect
    try {
        if (isCorrect) {
            correctSound.currentTime = 0;
            await correctSound.play();
        } else {
            incorrectSound.currentTime = 0;
            await incorrectSound.play();
        }
    } catch (error) {
        console.log('Sound effect could not be played:', error);
    }
    
    // Apply UI feedback with a slight delay for animation effect
    setTimeout(() => {
        // Mark all options with proper styling
        document.querySelectorAll('.answer-option').forEach(opt => {
            // Disable all options
            opt.style.pointerEvents = 'none';
            
            // Style correct answer
            if (opt.getAttribute('data-correct') === 'true') {
                opt.classList.add('correct');
                opt.style.backgroundColor = 'rgba(var(--bs-success-rgb), 0.1)';
                opt.style.borderColor = 'var(--bs-success)';
                
                // Show the check icon
                const icon = opt.querySelector('.bi-check-circle-fill');
                if (icon) {
                    icon.style.opacity = '1';
                }
            } 
            // Style selected incorrect answer
            else if (opt === option && !isCorrect) {
                opt.classList.add('incorrect');
                opt.style.backgroundColor = 'rgba(var(--bs-danger-rgb), 0.1)';
                opt.style.borderColor = 'var(--bs-danger)';
                opt.style.textDecoration = 'line-through';
                
                // Show the X icon
                const icon = opt.querySelector('.bi-x-circle-fill');
                if (icon) {
                    icon.style.opacity = '1';
                }
            }
        });
    }, 150); // Small delay for better UX
    
    // Show feedback - different for correct vs incorrect answers
    const feedbackDiv = document.getElementById('questionFeedback');
    feedbackDiv.classList.remove('d-none');
    
    if (isCorrect) {
        // Simpler feedback for correct answers - no explanation needed
        feedbackDiv.innerHTML = `
            <div class="alert alert-success">
                <div class="d-flex align-items-center">
                    <i class="bi bi-check-circle-fill me-2"></i>
                    <strong>Correct!</strong>
                </div>
            </div>
        `;
    } else {
        // More detailed feedback with explanation for incorrect answers
        feedbackDiv.innerHTML = `
            <div class="alert alert-danger">
                <div class="d-flex align-items-center mb-2">
                    <i class="bi bi-x-circle-fill me-2"></i>
                    <strong>Incorrect</strong>
                </div>
                <div class="explanation-container">
                    <div class="spinner-border spinner-border-sm me-2" role="status">
                        <span class="visually-hidden">Loading explanation...</span>
                    </div>
                    Generating explanation...
                </div>
            </div>
        `;
    }
    
    // Save answer to database and get explanation if wrong
    try {
        const response = await fetch('/learning/api/question/answer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question_id: questionId,
                answer: answerValue,
                is_correct: isCorrect
            })
        });
        
        const data = await response.json();
        
        // Only update explanation for incorrect answers
        if (!isCorrect && response.ok && data.explanation) {
            // Update feedback with explanation in a nicely formatted card
            const explanationContainer = feedbackDiv.querySelector('.explanation-container');
            explanationContainer.innerHTML = `
                <div class="card border-0 mt-3">
                    <div class="card-body py-2">
                        <h6 class="card-subtitle mb-2 text-muted">Explanation</h6>
                        <p class="card-text mb-0">${data.explanation}</p>
                    </div>
                </div>
            `;
        } else if (!isCorrect && !data.explanation) {
            // Handle case where no explanation was returned
            const explanationContainer = feedbackDiv.querySelector('.explanation-container');
            explanationContainer.innerHTML = `
                <div class="alert alert-light mt-2">
                    <i class="bi bi-info-circle me-2"></i>
                    The correct answer was provided above.
                </div>
            `;
        }
    } catch (error) {
        console.error('Error saving answer:', error);
        
        // If there was an error and the answer was incorrect, update the UI
        if (!isCorrect) {
            const explanationContainer = feedbackDiv.querySelector('.explanation-container');
            explanationContainer.innerHTML = `
                <div class="alert alert-light mt-2">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Failed to load explanation. The correct answer is highlighted.
                </div>
            `;
        }
    }
    
    // Show next button with pulse animation to draw attention
    const nextButtonContainer = document.getElementById('nextButtonContainer');
    nextButtonContainer.classList.remove('d-none');
    const nextButton = document.getElementById('nextQuestionBtn');
    nextButton.classList.add('animate__animated', 'animate__pulse');
    
    // Switch from answer selection keyboard handling to next question handling
    document.removeEventListener('keydown', handleAnswerKeyNavigation);
    document.addEventListener('keydown', handleKeyNavigation);
    
    // Store the callback for later use
    window._nextQuestionCallback = onComplete;
    
    // Let the user know they can press any key to continue
    const keyHintSpan = document.createElement('div');
    keyHintSpan.className = 'text-muted small mt-2';
    keyHintSpan.innerHTML = 'Press any key to continue';
    nextButtonContainer.appendChild(keyHintSpan);
    
    // Make sure the next button properly responds to clicks
    nextButton.onclick = function() {
        if (typeof onComplete === 'function') {
            onComplete();
        }
    };
}

/**
 * Display the prompt to complete the section
 */
export function displayCompleteSectionPrompt() {
    const contentArea = document.getElementById('dynamicContentArea');
    const template = document.getElementById('completeSectionTemplate');
    const content = template.content.cloneNode(true);
    
    // Clear existing content and append new content
    contentArea.innerHTML = '';
    contentArea.appendChild(content);
}

/**
 * Complete the section and continue to the next one
 * @param {number} sectionId - The section ID to complete
 */
export async function completeSectionAndContinue(sectionId) {
    showLoading('Completing section...');
    
    try {
        const response = await fetch(`/learning/api/section/${sectionId}/complete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to complete section');
        }
        
        const data = await response.json();
        
        if (data.success) {
            updateSectionStatusInSidebar(sectionId, true);
            return data;
        } else {
            throw new Error(data.error || 'Failed to complete section');
        }
    } catch (error) {
        console.error('Error completing section:', error);
        displayError('Failed to complete section. Please try again.');
        throw error;
    } finally {
        hideLoading();
    }
}

/**
 * Display the section completed message
 * @param {number} nextSectionId - The ID of the next section to load
 */
export function displaySectionCompleted(nextSectionId) {
    const contentArea = document.getElementById('dynamicContentArea');
    const template = document.getElementById('sectionCompletedTemplate');
    const content = template.content.cloneNode(true);
    
    // Set message and button functionality
    content.querySelector('.section-completed-message').textContent = 
        "Great job! You've completed this section. Ready to continue to the next section?";
    
    const nextButton = content.querySelector('.next-section-btn');
    nextButton.dataset.sectionId = nextSectionId;
    
    // Clear existing content and append new content
    contentArea.innerHTML = '';
    contentArea.appendChild(content);
}

/**
 * Display the all sections completed message
 */
export function displayAllSectionsCompleted() {
    const contentArea = document.getElementById('dynamicContentArea');
    const template = document.getElementById('allCompletedTemplate');
    const content = template.content.cloneNode(true);
    
    // Clear existing content and append new content
    contentArea.innerHTML = '';
    contentArea.appendChild(content);
}

/**
 * Show the next question or complete section prompt
 * (This would be the implementation in unified-learning.js)
 */
export function showNextQuestion(questions, currentIndex, onComplete) {
    console.log(`Showing next question: ${currentIndex + 1} of ${questions.length}`);
    
    // Check if there are more questions
    if (currentIndex < questions.length) {
        displayQuestion(questions[currentIndex], onComplete);
    } else {
        // No more questions, show complete section prompt
        displayCompleteSectionPrompt();
    }
}
