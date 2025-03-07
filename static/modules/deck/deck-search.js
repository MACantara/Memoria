/**
 * Deck search utility that adds search functionality to deck dropdowns
 */
export function initializeDeckSearch(selectElement, options = {}) {
    if (!selectElement) return;
    
    // Create search input
    const searchContainer = document.createElement('div');
    searchContainer.className = 'input-group mb-2';
    
    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.className = 'form-control form-control-sm';
    searchInput.placeholder = options.placeholder || 'Search decks...';
    searchInput.setAttribute('aria-label', 'Search decks');
    
    // Add clear button to search input
    const searchClear = document.createElement('button');
    searchClear.className = 'btn btn-sm btn-outline-secondary';
    searchClear.type = 'button';
    searchClear.innerHTML = '<i class="bi bi-x"></i>';
    searchClear.style.display = 'none';
    
    // Add input and clear button to container
    searchContainer.appendChild(searchInput);
    searchContainer.appendChild(searchClear);
    
    // Insert search before select element
    selectElement.parentNode.insertBefore(searchContainer, selectElement);
    
    // Store original options for filtering
    const originalOptions = Array.from(selectElement.options);
    
    // Add event listeners
    searchInput.addEventListener('input', filterOptions);
    searchClear.addEventListener('click', clearSearch);
    
    // Filter options based on search input
    function filterOptions() {
        const searchTerm = searchInput.value.toLowerCase();
        let visibleCount = 0;
        
        // Show/hide clear button
        searchClear.style.display = searchTerm ? 'block' : 'none';
        
        // Reset select to first option
        selectElement.selectedIndex = 0;
        
        // Filter options
        Array.from(originalOptions).forEach(option => {
            // Skip the first disabled placeholder option
            if (option.disabled && option.selected) {
                return;
            }
            
            const optionText = option.textContent.toLowerCase();
            const isMatch = optionText.includes(searchTerm);
            
            // Create a new option for each original option to ensure we maintain attributes
            let currentOption = selectElement.querySelector(`option[value="${option.value}"]`);
            if (!currentOption && isMatch) {
                // If the option doesn't exist and it matches, add it
                currentOption = option.cloneNode(true);
                selectElement.appendChild(currentOption);
                visibleCount++;
            } else if (currentOption && !isMatch) {
                // If the option exists but doesn't match, remove it
                currentOption.remove();
            } else if (currentOption && isMatch) {
                // Option exists and matches
                visibleCount++;
            }
        });
        
        // Show no results message if needed
        const noResultsMessage = selectElement.parentNode.querySelector('.no-results-message');
        if (visibleCount === 0 && searchTerm) {
            if (!noResultsMessage) {
                const message = document.createElement('div');
                message.className = 'no-results-message alert alert-info mt-2 mb-0 py-2';
                message.innerHTML = `<small><i class="bi bi-info-circle"></i> No decks match "${searchInput.value}"</small>`;
                selectElement.parentNode.insertBefore(message, selectElement.nextSibling);
            }
        } else if (noResultsMessage) {
            noResultsMessage.remove();
        }
    }
    
    // Clear search input and restore all options
    function clearSearch() {
        searchInput.value = '';
        searchClear.style.display = 'none';
        
        // Reset the select element
        selectElement.innerHTML = '';
        originalOptions.forEach(option => {
            selectElement.appendChild(option.cloneNode(true));
        });
        
        // Remove no results message if present
        const noResultsMessage = selectElement.parentNode.querySelector('.no-results-message');
        if (noResultsMessage) {
            noResultsMessage.remove();
        }
        
        // Set focus back to search
        searchInput.focus();
    }
    
    // Initialize with empty search to ensure proper setup
    filterOptions();
    
    // Return utilities
    return {
        clearSearch,
        updateOptions: (newOptions) => {
            // Update stored options (useful if options change)
            originalOptions.length = 0;
            newOptions.forEach(option => originalOptions.push(option.cloneNode(true)));
            filterOptions();
        }
    };
}
