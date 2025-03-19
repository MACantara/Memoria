/**
 * Question manager for displaying and handling learning questions
 */

import { showLoading, hideLoading, displayError } from './ui-utils.js';
import { updateSectionStatusInSidebar } from './ui-utils.js';

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
    
    // Create answer options
    const optionsContainer = content.querySelector('.answer-options');
    
    // Add correct answer
    const correctOption = document.createElement('div');
    correctOption.className = 'answer-option';
    correctOption.setAttribute('data-correct', 'true');
    correctOption.setAttribute('data-answer', question.correct_answer);
    correctOption.textContent = question.correct_answer;
    optionsContainer.appendChild(correctOption);
    
    // Add incorrect answers
    question.incorrect_answers.forEach(answer => {
        const option = document.createElement('div');
        option.className = 'answer-option';
        option.setAttribute('data-correct', 'false');
        option.setAttribute('data-answer', answer);
        option.textContent = answer;
        optionsContainer.appendChild(option);
    });
    
    // Shuffle answer options
    const options = Array.from(optionsContainer.children);
    for (let i = options.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        optionsContainer.appendChild(options[j]);
    }
    
    // Add click handlers to answer options
    content.querySelectorAll('.answer-option').forEach(option => {
        option.addEventListener('click', async (event) => {
            await handleAnswerSelection(event, onAnswered);
        });
    });
    
    // Add event listener to next button (when it becomes visible)
    const nextButton = content.querySelector('#nextQuestionBtn');
    nextButton.addEventListener('click', () => {
        if (typeof onAnswered === 'function') {
            onAnswered();
        }
    });
    
    // Clear existing content and append new content
    contentArea.innerHTML = '';
    contentArea.appendChild(content);
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
    
    // Mark all answers as correct/incorrect
    document.querySelectorAll('.answer-option').forEach(opt => {
        if (opt.getAttribute('data-correct') === 'true') {
            opt.classList.add('correct');
        } else if (opt === option) {
            opt.classList.add('incorrect');
        }
    });
    
    // Show temporary feedback while loading explanation
    const feedbackDiv = document.getElementById('questionFeedback');
    feedbackDiv.classList.remove('d-none');
    feedbackDiv.innerHTML = `
        <div class="alert ${isCorrect ? 'alert-success' : 'alert-danger'}">
            <div class="d-flex align-items-center mb-2">
                <i class="bi ${isCorrect ? 'bi-check-circle-fill' : 'bi-x-circle-fill'} me-2"></i>
                <strong>${isCorrect ? 'Correct!' : 'Incorrect'}</strong>
            </div>
            <div class="explanation-container">
                <div class="spinner-border spinner-border-sm me-2" role="status">
                    <span class="visually-hidden">Loading explanation...</span>
                </div>
                Generating explanation...
            </div>
        </div>
    `;
    
    // Save answer to database and get explanation
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
        
        if (response.ok && data.explanation) {
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
        } else {
            console.error('Failed to get explanation or save answer');
        }
    } catch (error) {
        console.error('Error saving answer:', error);
    }
    
    // Show next button
    const nextButtonContainer = document.getElementById('nextButtonContainer');
    nextButtonContainer.classList.remove('d-none');
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
