/**
 * UI utility functions for the learning module
 */

/**
 * Display an error message in the content area
 * @param {string} message - The error message to display
 */
export function displayError(message) {
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
export function showLoading(message = 'Loading...') {
    const loadingIndicator = document.getElementById('loadingIndicator');
    const loadingMessage = document.getElementById('loadingMessage');
    
    loadingMessage.textContent = message;
    loadingIndicator.classList.remove('d-none');
}

/**
 * Hide loading indicator
 */
export function hideLoading() {
    const loadingIndicator = document.getElementById('loadingIndicator');
    loadingIndicator.classList.add('d-none');
}

/**
 * Update the active section in the sidebar
 * @param {number} sectionId - The active section ID
 */
export function updateActiveSectionInSidebar(sectionId) {
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
export function updateSectionStatusInSidebar(sectionId, completed) {
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
 * Get the current session ID from the URL
 */
export function getCurrentSessionId() {
    const urlParts = window.location.pathname.split('/');
    const sessionIdIndex = urlParts.indexOf('session') + 1;
    
    if (sessionIdIndex < urlParts.length) {
        return urlParts[sessionIdIndex];
    }
    
    return null;
}
