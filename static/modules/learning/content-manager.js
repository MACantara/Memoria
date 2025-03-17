/**
 * Content manager for loading and displaying learning content
 */

import { showLoading, hideLoading, displayError, updateActiveSectionInSidebar } from './ui-utils.js';

/**
 * Load section content, generating it if needed
 * @param {number} sectionId - The section ID to load
 * @param {boolean} generateContent - Whether to generate content or load existing
 * @returns {Promise<Object>} - The section data
 */
export async function loadSectionContent(sectionId, generateContent = false) {
    showLoading('Loading section content...');
    
    try {
        if (generateContent) {
            await generateSectionContent(sectionId);
        }
        
        // Fetch section content
        const response = await fetch(`/learning/api/section/${sectionId}`);
        if (!response.ok) throw new Error('Failed to load section content');
        
        const sectionData = await response.json();
        
        // Update active section in the sidebar
        updateActiveSectionInSidebar(sectionId);
        
        return sectionData;
    } catch (error) {
        console.error('Error loading section content:', error);
        displayError('Failed to load section content. Please try again.');
        throw error;
    } finally {
        hideLoading();
    }
}

/**
 * Generate content for a section
 * @param {number} sectionId - The section ID to generate content for
 */
export async function generateSectionContent(sectionId) {
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
export function displaySectionContent(sectionData) {
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
 * Display completed section view
 * @param {Object} sectionData - The section data
 */
export function displayCompletedSection(sectionData) {
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
 * Generate an outline for a learning session
 */
export async function generateOutline() {
    const statusElement = document.getElementById('generationStatus');
    const errorContainer = document.getElementById('generationError');
    const errorMessage = document.getElementById('errorMessage');
    
    // Get session ID from URL
    const urlParts = window.location.pathname.split('/');
    const sessionIdIndex = urlParts.indexOf('session') + 1;
    
    if (sessionIdIndex >= urlParts.length) {
        console.error("Could not determine session ID");
        return;
    }
    
    const sessionId = urlParts[sessionIdIndex];
    
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
