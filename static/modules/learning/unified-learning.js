/**
 * Unified learning module that coordinates the learning experience
 */

import { loadSectionContent, displaySectionContent, displayCompletedSection, generateOutline } from './content-manager.js';
import { markContentReadAndShowQuestions, displayQuestion, displayCompleteSectionPrompt, 
         completeSectionAndContinue, displaySectionCompleted, displayAllSectionsCompleted } from './question-manager.js';

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
                handleLoadSection(sectionId);
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
        
        // Next section button
        if (event.target.classList.contains('next-section-btn') || event.target.closest('.next-section-btn')) {
            const nextSectionBtn = event.target.classList.contains('next-section-btn') ? 
                event.target : event.target.closest('.next-section-btn');
            
            if (nextSectionBtn.dataset.sectionId) {
                handleLoadSection(nextSectionBtn.dataset.sectionId);
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
        const result = await completeSectionAndContinue(currentState.sectionId);
        
        if (result.all_completed) {
            displayAllSectionsCompleted();
        } else if (result.next_section_id) {
            displaySectionCompleted(result.next_section_id);
        }
    } catch (error) {
        console.error('Failed to complete section:', error);
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
