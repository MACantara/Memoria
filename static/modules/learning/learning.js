/**
 * Unified learning module that handles all learning functionality within a single page
 */

// Global state to track learning progress
let currentState = {
    sessionId: null,
    sectionId: null,
    step: 'content',  // 'content', 'question', 'complete'
    currentQuestionIndex: 0,
    questions: []
};

/**
 * Initialize the unified learning experience
 * @param {number} sessionId - The current learning session ID
 */
export function initializeUnifiedLearning(sessionId) {
    if (!sessionId) return;
    
    // Initialize state
    currentState.sessionId = sessionId;
    
    // Set up event listeners
    setupEventListeners();
    
    // Check if we should auto-start first section
    const startLearningBtn = document.getElementById('startLearningBtn');
    if (startLearningBtn) {
        const sectionId = startLearningBtn.dataset.sectionId;
        if (sectionId) {
            startLearningBtn.addEventListener('click', () => {
                loadSectionContent(sectionId);
            });
        }
    }
}

/**
 * Set up all event listeners needed for the unified learning experience
 */
function setupEventListeners() {
    // Add click handlers for section links
    document.querySelectorAll('.section-link').forEach(link => {
        link.addEventListener('click', () => {
            const sectionId = link.dataset.sectionId;
            const hasContent = link.dataset.hasContent === 'true';
            const isCompleted = link.dataset.isCompleted === 'true';
            
            if (isCompleted) {
                // If completed, just show the content
                loadSectionContent(sectionId);
            } else if (hasContent) {
                // If has content but not completed, load content
                loadSectionContent(sectionId);
            } else {
                // If no content, generate it
                loadSectionContent(sectionId, true);
            }
        });
    });
    
    // Event delegation for dynamically created buttons
    document.getElementById('dynamicContentArea').addEventListener('click', async (event) => {
        // Continue to questions button
        if (event.target.id === 'completeContentBtn' || event.target.closest('#completeContentBtn')) {
            await markContentReadAndShowQuestions();
        }
        
        // Complete section button
        if (event.target.id === 'completeSectionBtn' || event.target.closest('#completeSectionBtn')) {
            await completeSectionAndContinue();
        }
        
        // Next section button
        if (event.target.classList.contains('next-section-btn') || event.target.closest('.next-section-btn')) {
            const nextSectionBtn = event.target.classList.contains('next-section-btn') ? 
                event.target : event.target.closest('.next-section-btn');
            
            if (nextSectionBtn.dataset.sectionId) {
                loadSectionContent(nextSectionBtn.dataset.sectionId);
            }
        }
    });
}

/**
 * Load section content, generating it if needed
 * @param {number} sectionId - The section ID to load
 * @param {boolean} generateContent - Whether to generate content or load existing
 */
async function loadSectionContent(sectionId, generateContent = false) {
    showLoading('Loading section content...');
    currentState.sectionId = sectionId;
    
    try {
        if (generateContent) {
            await generateSectionContent(sectionId);
        }
        
        // Fetch section content
        const response = await fetch(`/learning/api/section/${sectionId}`);
        if (!response.ok) throw new Error('Failed to load section content');
        
        const sectionData = await response.json();
        
        if (sectionData.is_completed) {
            currentState.step = 'complete';
            displayCompletedSection(sectionData);
        } else if (sectionData.content) {
            currentState.step = 'content';
            displaySectionContent(sectionData);
        } else {
            throw new Error('No content available for this section');
        }
        
        // Update active section in the sidebar
        updateActiveSectionInSidebar(sectionId);
        
    } catch (error) {
        console.error('Error loading section content:', error);
        displayError('Failed to load section content. Please try again.');
    } finally {
        hideLoading();
    }
}

/**
 * Generate content for a section
 * @param {number} sectionId - The section ID to generate content for
 */
async function generateSectionContent(sectionId) {
    showLoading('Generating educational content...');
    
    try {
        const response = await fetch(`/learning/api/section/${sectionId}/generate-content`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to generate content');
        }
        
        const data = await response.json();
        if (!data.success) {
            throw new Error(data.error || 'Content generation failed');
        }
        
        return data;
    } catch (error) {
        console.error('Content generation error:', error);
        throw error;
    }
}

/**
 * Display section content in the dynamic content area
 * @param {Object} sectionData - The section data including content
 */
function displaySectionContent(sectionData) {
    const contentArea = document.getElementById('dynamicContentArea');
    const template = document.getElementById('sectionContentTemplate');
    const content = template.content.cloneNode(true);
    
    // Set section title and content
    content.querySelector('.section-title').textContent = sectionData.title;
    content.querySelector('.learning-content').innerHTML = sectionData.content;
    
    // Clear existing content and append new content
    contentArea.innerHTML = '';
    contentArea.appendChild(content);
}

/**
 * Mark content as read and show questions
 */
async function markContentReadAndShowQuestions() {
    if (!currentState.sectionId) return;
    
    showLoading('Preparing questions...');
    
    try {
        const response = await fetch(`/learning/api/section/${currentState.sectionId}/mark-read`, {
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
            // Store questions for later use
            currentState.questions = data.questions;
            currentState.currentQuestionIndex = 0;
            currentState.step = 'question';
            
            // Display first question
            if (currentState.questions.length > 0) {
                displayQuestion(currentState.questions[0]);
            } else {
                displayCompleteSectionPrompt();
            }
        } else {
            throw new Error(data.error || 'Failed to generate questions');
        }
    } catch (error) {
        console.error('Error preparing questions:', error);
        displayError('Failed to prepare questions. Please try again.');
    } finally {
        hideLoading();
    }
}

/**
 * Display a question in the dynamic content area
 * @param {Object} question - The question data
 */
function displayQuestion(question) {
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
        option.addEventListener('click', handleAnswerSelection);
    });
    
    // Add event listener to next button (when it becomes visible)
    const nextButton = content.querySelector('#nextQuestionBtn');
    nextButton.addEventListener('click', showNextQuestion);
    
    // Clear existing content and append new content
    contentArea.innerHTML = '';
    contentArea.appendChild(content);
}

/**
 * Handle when a user selects an answer
 * @param {Event} event - The click event
 */
async function handleAnswerSelection(event) {
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
    
    // Show feedback
    const feedbackDiv = document.getElementById('questionFeedback');
    feedbackDiv.classList.remove('d-none');
    feedbackDiv.innerHTML = isCorrect ? 
        '<div class="alert alert-success"><i class="bi bi-check-circle-fill me-2"></i>Correct!</div>' : 
        '<div class="alert alert-danger"><i class="bi bi-x-circle-fill me-2"></i>Incorrect. The correct answer is highlighted.</div>';
    
    // Show next button
    const nextButtonContainer = document.getElementById('nextButtonContainer');
    nextButtonContainer.classList.remove('d-none');
    
    // Save answer to database
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
        
        if (!response.ok) {
            console.error('Failed to save answer');
        }
    } catch (error) {
        console.error('Error saving answer:', error);
    }
}

/**
 * Show the next question or complete section prompt
 */
function showNextQuestion() {
    currentState.currentQuestionIndex++;
    
    // Check if there are more questions
    if (currentState.currentQuestionIndex < currentState.questions.length) {
        displayQuestion(currentState.questions[currentState.currentQuestionIndex]);
    } else {
        // No more questions, show complete section prompt
        displayCompleteSectionPrompt();
    }
}

/**
 * Display the prompt to complete the section
 */
function displayCompleteSectionPrompt() {
    const contentArea = document.getElementById('dynamicContentArea');
    const template = document.getElementById('completeSectionTemplate');
    const content = template.content.cloneNode(true);
    
    // Clear existing content and append new content
    contentArea.innerHTML = '';
    contentArea.appendChild(content);
}

/**
 * Complete the section and continue to the next one
 */
async function completeSectionAndContinue() {
    showLoading('Completing section...');
    
    try {
        const response = await fetch(`/learning/api/section/${currentState.sectionId}/complete`, {
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
            currentState.step = 'complete';
            
            if (data.all_completed) {
                displayAllSectionsCompleted();
            } else if (data.next_section_id) {
                displaySectionCompleted(data.next_section_id);
            } else {
                // Just refresh the page as a fallback
                window.location.reload();
            }
            
            // Update section status in sidebar
            updateSectionStatusInSidebar(currentState.sectionId, true);
        } else {
            throw new Error(data.error || 'Failed to complete section');
        }
    } catch (error) {
        console.error('Error completing section:', error);
        displayError('Failed to complete section. Please try again.');
    } finally {
        hideLoading();
    }
}

/**
 * Display the section completed message
 * @param {number} nextSectionId - The ID of the next section to load
 */
function displaySectionCompleted(nextSectionId) {
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
function displayAllSectionsCompleted() {
    const contentArea = document.getElementById('dynamicContentArea');
    const template = document.getElementById('allCompletedTemplate');
    const content = template.content.cloneNode(true);
    
    // Clear existing content and append new content
    contentArea.innerHTML = '';
    contentArea.appendChild(content);
}

/**
 * Display completed section view
 * @param {Object} sectionData - The section data
 */
function displayCompletedSection(sectionData) {
    const contentArea = document.getElementById('dynamicContentArea');
    
    // Create completed section view
    contentArea.innerHTML = `
        <h2 class="h4 mb-4">${sectionData.title}</h2>
        <div class="learning-content mb-4">${sectionData.content}</div>
        <div class="alert alert-success">
            <i class="bi bi-check-circle-fill me-2"></i>
            You've already completed this section. You can review the content or select another section.
        </div>
    `;
}

/**
 * Update the active section in the sidebar
 * @param {number} sectionId - The active section ID
 */
function updateActiveSectionInSidebar(sectionId) {
    // Remove active class from all sections
    document.querySelectorAll('.section-toc .toc-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Add active class to current section
    const activeSection = document.querySelector(`.section-link[data-section-id="${sectionId}"]`);
    if (activeSection) {
        activeSection.closest('.toc-item').classList.add('active');
    }
}

/**
 * Update section status in sidebar (mark as completed)
 * @param {number} sectionId - The section ID
 * @param {boolean} completed - Whether the section is completed
 */
function updateSectionStatusInSidebar(sectionId, completed) {
    const sectionLink = document.querySelector(`.section-link[data-section-id="${sectionId}"]`);
    if (sectionLink) {
        const sectionItem = sectionLink.closest('.toc-item');
        
        if (completed) {
            sectionItem.classList.add('completed');
            sectionLink.dataset.isCompleted = 'true';
            
            // Update icon
            const icon = sectionLink.querySelector('i');
            if (icon) {
                icon.className = 'bi bi-check-circle-fill me-2';
            }
        }
    }
}

/**
 * Display an error message
 * @param {string} message - The error message to display
 */
function displayError(message) {
    const contentArea = document.getElementById('dynamicContentArea');
    contentArea.innerHTML = `
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle-fill me-2"></i>
            ${message}
        </div>
        <div class="text-center mt-3">
            <button class="btn btn-outline-primary" onclick="window.location.reload()">
                <i class="bi bi-arrow-clockwise me-1"></i> Refresh Page
            </button>
        </div>
    `;
}

/**
 * Show loading indicator
 * @param {string} message - The loading message to display
 */
function showLoading(message = 'Loading...') {
    const loadingIndicator = document.getElementById('loadingIndicator');
    const loadingMessage = document.getElementById('loadingMessage');
    
    loadingMessage.textContent = message;
    loadingIndicator.classList.remove('d-none');
}

/**
 * Hide loading indicator
 */
function hideLoading() {
    const loadingIndicator = document.getElementById('loadingIndicator');
    loadingIndicator.classList.add('d-none');
}

// Add this to your unified-learning.js or learning.js module

// Check if we need to generate an outline when the page loads
document.addEventListener('DOMContentLoaded', function() {
    if (new URLSearchParams(window.location.search).get('generate_outline') === 'true') {
        generateOutline();
    }
});

/**
 * Generate an outline for a learning session
 */
async function generateOutline() {
    const statusElement = document.getElementById('generationStatus');
    const errorContainer = document.getElementById('generationError');
    const errorMessage = document.getElementById('errorMessage');
    const sessionId = getCurrentSessionId();
    
    if (!sessionId) {
        console.error("Could not determine session ID");
        return;
    }
    
    try {
        statusElement.textContent = "Analyzing topic and creating structure...";
        
        // Send request to generate outline
        const response = await fetch(`/learning/session/${sessionId}/process-outline`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || "Failed to generate outline");
        }
        
        if (data.success) {
            statusElement.textContent = "Learning path created successfully! Reloading...";
            window.location.href = data.redirect;
        } else {
            throw new Error(data.error || "Unknown error");
        }
        
    } catch (error) {
        console.error("Outline generation error:", error);
        statusElement.textContent = "Generation failed.";
        errorMessage.textContent = error.message || "Failed to generate outline. Please try again.";
        errorContainer.classList.remove('d-none');
    }
}

/**
 * Retry outline generation
 */
window.retryGeneration = function() {
    const errorContainer = document.getElementById('generationError');
    const statusElement = document.getElementById('generationStatus');
    
    errorContainer.classList.add('d-none');
    statusElement.textContent = "Retrying generation...";
    
    generateOutline();
}

/**
 * Get the current session ID from the URL
 */
function getCurrentSessionId() {
    const urlParts = window.location.pathname.split('/');
    const sessionIdIndex = urlParts.indexOf('session') + 1;
    
    if (sessionIdIndex < urlParts.length) {
        return urlParts[sessionIdIndex];
    }
    
    return null;
}
