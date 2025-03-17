/**
 * Learning module that handles all learning-related functionality
 */
export function initializeLearningModules() {
    // Initialize different parts based on page context
    if (document.getElementById('generationStatus') && document.getElementById('generationError')) {
        // On outline or content generation page
        if (window.location.href.includes('generate-outline')) {
            // Outline generation page
            generateOutline();
        } else if (window.location.href.includes('generate')) {
            // Content generation page
            generateContent();
        }
    }
    
    // Section page components
    if (document.getElementById('completeContentBtn')) {
        document.getElementById('completeContentBtn').addEventListener('click', markContentRead);
    }
    
    // Initialize question UI if we're on a section page with questions
    if (document.getElementById('questionContainer')) {
        initializeQuestionUI();
    }
    
    // Initialize complete section button if present
    if (document.getElementById('completeSectionBtn')) {
        document.getElementById('completeSectionBtn').addEventListener('click', completeSection);
    }
}

/**
 * Generate an outline for a learning session
 */
async function generateOutline() {
    const statusElement = document.getElementById('generationStatus');
    const errorContainer = document.getElementById('generationError');
    const errorMessage = document.getElementById('errorMessage');
    const sessionId = getSessionIdFromUrl();
    
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
            statusElement.textContent = "Learning path created successfully! Redirecting...";
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
 * Generate content for a learning section
 */
async function generateContent() {
    const statusElement = document.getElementById('generationStatus');
    const errorContainer = document.getElementById('generationError');
    const errorMessage = document.getElementById('errorMessage');
    const sectionId = getSectionIdFromUrl();
    
    if (!sectionId) {
        console.error("Could not determine section ID");
        return;
    }
    
    try {
        statusElement.textContent = "Researching topic and creating educational content...";
        
        // Send request to generate content
        const response = await fetch(`/learning/section/${sectionId}/process-content`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || "Failed to generate content");
        }
        
        if (data.success) {
            statusElement.textContent = "Content created successfully! Redirecting...";
            window.location.href = data.redirect;
        } else {
            throw new Error(data.error || "Unknown error");
        }
        
    } catch (error) {
        console.error("Content generation error:", error);
        statusElement.textContent = "Generation failed.";
        errorMessage.textContent = error.message || "Failed to generate content. Please try again.";
        errorContainer.classList.remove('d-none');
    }
}

/**
 * Retry content or outline generation
 */
export function retryGeneration() {
    const errorContainer = document.getElementById('generationError');
    const statusElement = document.getElementById('generationStatus');
    
    errorContainer.classList.add('d-none');
    statusElement.textContent = "Retrying generation...";
    
    if (window.location.href.includes('generate-outline')) {
        generateOutline();
    } else if (window.location.href.includes('generate')) {
        generateContent();
    }
}

/**
 * Initialize question UI components
 */
function initializeQuestionUI() {
    const answerOptions = document.querySelectorAll('.answer-option');
    const nextButtonContainer = document.getElementById('nextButtonContainer');
    const nextButton = document.getElementById('nextQuestionBtn');
    
    // Shuffle answer options - Add null checking
    const optionsContainer = document.querySelector('.answer-options');
    if (optionsContainer) {
        const options = Array.from(optionsContainer.children);
        for (let i = options.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            optionsContainer.appendChild(options[j]);
        }
    }
    
    // Add click handlers to answer options (only if they exist)
    if (answerOptions.length > 0) {
        answerOptions.forEach(option => {
            option.addEventListener('click', function() {
                if (this.classList.contains('selected') || 
                    this.classList.contains('correct') || 
                    this.classList.contains('incorrect')) {
                    return; // Already answered
                }
                
                // Select this option
                answerOptions.forEach(opt => opt.classList.remove('selected'));
                this.classList.add('selected');
                
                // Check if correct
                const isCorrect = this.getAttribute('data-correct') === 'true';
                const questionId = this.closest('.question-item').getAttribute('data-question-id');
                const answerValue = this.getAttribute('data-answer');
                
                // Show feedback
                showAnswerFeedback(isCorrect, questionId, answerValue);
            });
        });
    }
    
    // Next question handler
    if (nextButton) {
        nextButton.addEventListener('click', function() {
            window.location.reload();
        });
    }
}

/**
 * Show feedback after answering a question
 */
async function showAnswerFeedback(isCorrect, questionId, answerValue) {
    const feedbackDiv = document.getElementById('questionFeedback');
    const nextButtonContainer = document.getElementById('nextButtonContainer');
    const selectedOption = document.querySelector('.answer-option.selected');
    
    if (!feedbackDiv || !selectedOption) return;
    
    // Mark all answers as correct/incorrect
    document.querySelectorAll('.answer-option').forEach(option => {
        if (option.getAttribute('data-correct') === 'true') {
            option.classList.add('correct');
        } else if (option === selectedOption) {
            option.classList.add('incorrect');
        }
    });
    
    // Show feedback message
    feedbackDiv.classList.remove('d-none');
    feedbackDiv.innerHTML = isCorrect ? 
        '<div class="alert alert-success"><i class="bi bi-check-circle-fill me-2"></i>Correct!</div>' : 
        '<div class="alert alert-danger"><i class="bi bi-x-circle-fill me-2"></i>Incorrect. The correct answer is highlighted.</div>';
    
    // Show next button
    nextButtonContainer.classList.remove('d-none');
    
    // Save answer to database
    try {
        const response = await fetch('/learning/question/answer', {
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
 * Mark a section as read and proceed to questions
 */
async function markContentRead() {
    const button = document.getElementById('completeContentBtn');
    const sectionId = getSectionIdFromUrl();
    
    if (!sectionId) {
        console.error("Could not determine section ID");
        return;
    }
    
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
    
    try {
        const response = await fetch(`/learning/section/${sectionId}/mark-read`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            window.location.reload();
        } else {
            throw new Error(data.error || "Failed to mark section as read");
        }
    } catch (error) {
        console.error('Error marking section as read:', error);
        button.disabled = false;
        button.innerHTML = '<i class="bi bi-check-circle me-1"></i> I\'ve Read This Section';
        
        // Show error message
        const errorMsg = document.createElement('div');
        errorMsg.className = 'alert alert-danger mt-3';
        errorMsg.innerHTML = `<i class="bi bi-exclamation-triangle me-2"></i> ${error.message || "Error processing request"}`;
        button.parentNode.appendChild(errorMsg);
    }
}

/**
 * Mark a section as complete and move to next section
 */
async function completeSection() {
    const button = document.getElementById('completeSectionBtn');
    const sectionId = getSectionIdFromUrl();
    
    if (!sectionId) {
        console.error("Could not determine section ID");
        return;
    }
    
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
    
    try {
        const response = await fetch(`/learning/section/${sectionId}/complete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            if (data.redirect) {
                window.location.href = data.redirect;
            } else {
                window.location.reload();
            }
        } else {
            throw new Error(data.error || "Failed to complete section");
        }
    } catch (error) {
        console.error('Error completing section:', error);
        button.disabled = false;
        button.innerHTML = '<i class="bi bi-check-circle me-1"></i> Complete Section';
        
        // Show error message
        const errorMsg = document.createElement('div');
        errorMsg.className = 'alert alert-danger mt-3';
        errorMsg.innerHTML = `<i class="bi bi-exclamation-triangle me-2"></i> ${error.message || "Error processing request"}`;
        button.parentNode.appendChild(errorMsg);
    }
}

/**
 * Helper function to extract section ID from URL
 */
function getSectionIdFromUrl() {
    const urlParts = window.location.pathname.split('/');
    const sectionIdIndex = urlParts.indexOf('section') + 1;
    
    if (sectionIdIndex < urlParts.length) {
        return urlParts[sectionIdIndex];
    }
    
    return null;
}

/**
 * Helper function to extract session ID from URL
 */
function getSessionIdFromUrl() {
    const urlParts = window.location.pathname.split('/');
    const sessionIdIndex = urlParts.indexOf('session') + 1;
    
    if (sessionIdIndex < urlParts.length) {
        return urlParts[sessionIdIndex];
    }
    
    return null;
}
