/**
 * Unified learning module that coordinates the learning experience
 */

import { loadSectionContent, displaySectionContent, displayCompletedSection, generateOutline } from './content-manager.js';
import { markContentReadAndShowQuestions, displayQuestion, displayCompleteSectionPrompt, 
         completeSectionAndContinue, displaySectionCompleted, displayAllSectionsCompleted } from './question-manager.js';
import { showLoading, hideLoading, displayError } from './ui-utils.js';

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
    
    // Check if we need to generate an outline
    if (new URLSearchParams(window.location.search).get('generate_outline') === 'true') {
        generateOutline();
    }
    
    // Check if we should auto-start first section
    const startLearningBtn = document.getElementById('startLearningBtn');
    if (startLearningBtn) {
        const sectionId = startLearningBtn.dataset.sectionId;
        if (sectionId) {
            startLearningBtn.addEventListener('click', () => {
                // Always generate content for first section when starting learning
                handleLoadSection(sectionId, true);
                
                // Update button state while generating
                startLearningBtn.disabled = true;
                startLearningBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Generating content...';
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
            const isLocked = link.dataset.isLocked === 'true';
            
            // Prevent navigation to locked sections
            if (isLocked) {
                showLockedSectionToast();
                return;
            }
            
            handleLoadSection(sectionId, !hasContent);
        });
    });
    
    // Event delegation for dynamically created buttons
    document.getElementById('dynamicContentArea').addEventListener('click', async (event) => {
        // Continue to questions button
        if (event.target.id === 'completeContentBtn' || event.target.closest('#completeContentBtn')) {
            await handleMarkContentRead();
        }
        
        // Complete section button
        if (event.target.id === 'completeSectionBtn' || event.target.closest('#completeSectionBtn')) {
            await handleCompleteSection();
        }
        
        // Next section button - Enhanced with auto content generation
        if (event.target.classList.contains('next-section-btn') || event.target.closest('.next-section-btn')) {
            const nextSectionBtn = event.target.classList.contains('next-section-btn') ? 
                event.target : event.target.closest('.next-section-btn');
            
            if (nextSectionBtn.dataset.sectionId) {
                const sectionId = nextSectionBtn.dataset.sectionId;
                // Check if the section already has content generated
                await handleNextSectionNavigation(sectionId);
            }
        }
    });
}

/**
 * Handle loading a section
 * @param {number} sectionId - The section ID to load
 * @param {boolean} generateContent - Whether to generate content
 */
async function handleLoadSection(sectionId, generateContent = false) {
    try {
        currentState.sectionId = sectionId;
        
        const sectionData = await loadSectionContent(sectionId, generateContent);
        
        if (sectionData.is_completed) {
            currentState.step = 'complete';
            displayCompletedSection(sectionData);
        } else if (sectionData.content) {
            currentState.step = 'content';
            displaySectionContent(sectionData);
        }
    } catch (error) {
        console.error('Failed to load section:', error);
    }
}

/**
 * Handle marking content as read and showing questions
 */
async function handleMarkContentRead() {
    try {
        // Show loading state
        const button = document.getElementById('completeContentBtn');
        if (button) {
            const normalState = button.querySelector('.normal-state');
            const loadingState = button.querySelector('.loading-state');
            
            if (normalState && loadingState) {
                button.disabled = true;
                normalState.classList.add('d-none');
                loadingState.classList.remove('d-none');
            }
        }
        
        // Get questions for the section
        currentState.questions = await markContentReadAndShowQuestions(currentState.sectionId);
        currentState.currentQuestionIndex = 0;
        currentState.step = 'question';
        
        // Display first question or complete section prompt if no questions
        if (currentState.questions.length > 0) {
            displayQuestion(currentState.questions[0], showNextQuestion);
        } else {
            displayCompleteSectionPrompt();
        }
    } catch (error) {
        console.error('Failed to mark content as read:', error);
    }
}

/**
 * Show the next question or complete section prompt
 */
function showNextQuestion() {
    // Show loading state if button exists
    const button = document.getElementById('nextQuestionBtn');
    if (button) {
        const normalState = button.querySelector('.normal-state');
        const loadingState = button.querySelector('.loading-state');
        
        if (normalState && loadingState) {
            button.disabled = true;
            normalState.classList.add('d-none');
            loadingState.classList.remove('d-none');
        }
    }
    
    currentState.currentQuestionIndex++;
    
    // Check if there are more questions
    if (currentState.currentQuestionIndex < currentState.questions.length) {
        displayQuestion(currentState.questions[currentState.currentQuestionIndex], showNextQuestion);
    } else {
        // No more questions, show complete section prompt
        displayCompleteSectionPrompt();
    }
}

/**
 * Handle completing a section and continuing to the next one
 */
async function handleCompleteSection() {
    try {
        // Show loading state
        const button = document.getElementById('completeSectionBtn');
        if (button) {
            const normalState = button.querySelector('.normal-state');
            const loadingState = button.querySelector('.loading-state');
            
            if (normalState && loadingState) {
                button.disabled = true;
                normalState.classList.add('d-none');
                loadingState.classList.remove('d-none');
            }
        }
        
        const result = await completeSectionAndContinue(currentState.sectionId);
        
        // Update the progress bar after completing a section
        updateProgressDisplay();
        
        if (result.all_completed) {
            // If all sections are completed, show the completion screen
            displayAllSectionsCompleted();
        } else if (result.next_section_id) {
            // Update UI to unlock the next section
            unlockNextSection(currentState.sectionId);
            
            // Instead of displaying completion message, directly navigate to the next section
            showLoading('Moving to next section...');
            await handleNextSectionNavigation(result.next_section_id);
        }
    } catch (error) {
        console.error('Failed to complete section:', error);
    }
}

/**
 * Unlock the next section in the sequence
 * @param {number} completedSectionId - ID of the section that was just completed
 */
function unlockNextSection(completedSectionId) {
    // Find the completed section in the sidebar
    const completedLink = document.querySelector(`.section-link[data-section-id="${completedSectionId}"]`);
    if (!completedLink) return;
    
    const completedItem = completedLink.closest('.toc-item');
    if (!completedItem) return;
    
    // Find the next item in the list
    const nextItem = completedItem.nextElementSibling;
    if (!nextItem) return;
    
    // Unlock the next section
    const nextLink = nextItem.querySelector('.section-link');
    if (nextLink) {
        nextLink.dataset.isLocked = 'false';
        nextItem.classList.remove('locked');
        
        // Update the icon
        const icon = nextLink.querySelector('i');
        if (icon && icon.classList.contains('bi-lock-fill')) {
            icon.classList.remove('bi-lock-fill');
            icon.classList.add('bi-circle');
        }
    }
}

/**
 * Show a toast message indicating that a section is locked
 */
function showLockedSectionToast() {
    // Create a toast element if it doesn't exist
    let toastContainer = document.getElementById('lockedSectionToast');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'lockedSectionToast';
        toastContainer.className = 'position-fixed bottom-0 end-0 p-3';
        toastContainer.style.zIndex = '5';
        document.body.appendChild(toastContainer);
    }
    
    // Create the toast content with theme-aware styling
    const toastId = 'sectionLockedToast' + Date.now();
    toastContainer.innerHTML = `
        <div id="${toastId}" class="toast border-warning" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header bg-warning text-dark">
                <i class="bi bi-lock-fill me-2"></i>
                <strong class="me-auto">Section Locked</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                Complete the previous section before continuing to this one.
            </div>
        </div>
    `;
    
    // Show the toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
    toast.show();
}

/**
 * Handle navigation to next section with automatic content generation if needed
 * @param {number} sectionId - The section ID to navigate to
 */
async function handleNextSectionNavigation(sectionId) {
    // Show loading state on the button first
    const nextButton = document.querySelector('.next-section-btn');
    if (nextButton) {
        const normalState = nextButton.querySelector('.normal-state');
        const loadingState = nextButton.querySelector('.loading-state');
        
        if (normalState && loadingState) {
            nextButton.disabled = true;
            normalState.classList.add('d-none');
            loadingState.classList.remove('d-none');
        }
    }
    
    showLoading('Preparing next section...');
    
    try {
        // First, check if the section has content
        const response = await fetch(`/learning/api/section/${sectionId}`);
        if (!response.ok) throw new Error('Failed to check section status');
        
        const sectionData = await response.json();
        
        if (sectionData.content) {
            // Content already exists, just navigate to it
            handleLoadSection(sectionId);
        } else {
            // Content doesn't exist, generate it first
            showLoading('Generating content for next section...');
            
            // Update the button text to show generation is happening
            const nextButton = document.querySelector('.next-section-btn');
            if (nextButton) {
                const btnText = nextButton.querySelector('.next-button-text');
                if (btnText) btnText.textContent = 'Generating Content...';
                nextButton.disabled = true;
            }
            
            await generateSectionContent(sectionId);
            
            // Now navigate to the section with the fresh content
            handleLoadSection(sectionId);
        }
    } catch (error) {
        console.error('Failed to prepare next section:', error);
        displayError('Failed to prepare the next section. Please try refreshing the page.');
        hideLoading();
    }
}

/**
 * Update the progress display in the UI
 */
function updateProgressDisplay() {
    // Count total and completed sections
    const allSections = document.querySelectorAll('.section-toc .toc-item');
    const completedSections = document.querySelectorAll('.section-toc .toc-item.completed');
    
    // Calculate percentage
    const total = allSections.length;
    const completed = completedSections.length;
    const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;
    
    // Update progress bar width
    const progressBar = document.querySelector('.progress-bar');
    if (progressBar) {
        progressBar.style.width = `${percentage}%`;
        progressBar.setAttribute('aria-valuenow', percentage);
        
        // Update color if completed
        if (percentage === 100) {
            progressBar.classList.remove('bg-primary');
            progressBar.classList.add('bg-success');
        }
    }
    
    // Update percentage text
    const percentageText = document.querySelector('.progress + .mt-3 span, .d-flex > span.fs-5');
    if (percentageText) {
        percentageText.textContent = `${percentage}% Complete`;
    }
}

/**
 * Make retry generation accessible globally for the retry button
 */
window.retryGeneration = function() {
    const errorContainer = document.getElementById('generationError');
    const statusElement = document.getElementById('generationStatus');
    
    errorContainer.classList.add('d-none');
    statusElement.textContent = "Retrying generation...";
    
    generateOutline();
}
