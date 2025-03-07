/**
 * Deck search utility that adds search functionality directly inside dropdowns
 */
export function initializeDeckSearch(selectElement, options = {}) {
    if (!selectElement) return;
    
    // Store original options for filtering
    const originalOptions = Array.from(selectElement.options);
    let searchTerm = '';
    let searchTimeout = null;
    
    // Add search instruction placeholder
    const placeholderText = options.placeholder || 'Type to search decks...';
    const firstOption = selectElement.options[0];
    if (firstOption && firstOption.disabled) {
        firstOption.text = placeholderText;
    } else {
        const placeholder = document.createElement('option');
        placeholder.disabled = true;
        placeholder.selected = true;
        placeholder.text = placeholderText;
        selectElement.prepend(placeholder);
    }
    
    // Add keyboard event to capture typing
    selectElement.addEventListener('keydown', function(e) {
        // Prevent default actions for some keys to avoid conflicts
        if (e.key.length === 1 || e.key === 'Backspace') {
            e.stopPropagation();
            
            // Don't prevent default for Backspace to allow clearing selection
            if (e.key !== 'Backspace') {
                e.preventDefault();
            }
            
            // Update search term
            if (e.key === 'Backspace') {
                searchTerm = searchTerm.slice(0, -1);
            } else {
                searchTerm += e.key;
            }
            
            // Show visual feedback of search in placeholder
            updatePlaceholder();
            
            // Filter options based on search term
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                filterOptions();
            }, 300);
        }
        
        // Clear search on Escape key
        if (e.key === 'Escape') {
            clearSearch();
            e.preventDefault();
        }
    });
    
    // Reset search when dropdown is closed
    selectElement.addEventListener('blur', function() {
        setTimeout(() => {
            clearSearch();
        }, 300);
    });
    
    // Update placeholder to show search text
    function updatePlaceholder() {
        const firstOption = selectElement.options[0];
        if (firstOption && firstOption.disabled) {
            if (searchTerm) {
                firstOption.text = `Search: ${searchTerm}`;
            } else {
                firstOption.text = placeholderText;
            }
        }
    }
    
    // Filter options based on search input
    function filterOptions() {
        if (!searchTerm) {
            resetOptions();
            return;
        }
        
        // Reset to placeholder option
        selectElement.selectedIndex = 0;
        
        // Remove all options except the first placeholder
        while (selectElement.options.length > 1) {
            selectElement.remove(1);
        }
        
        // Add matching options
        let visibleCount = 0;
        originalOptions.forEach(option => {
            // Skip the first placeholder option
            if (option.disabled && option.selected) {
                return;
            }
            
            const optionText = option.textContent.toLowerCase();
            if (optionText.includes(searchTerm.toLowerCase())) {
                const newOption = option.cloneNode(true);
                selectElement.add(newOption);
                visibleCount++;
            }
        });
        
        // Show no results message if needed
        if (visibleCount === 0) {
            const noMatchOption = document.createElement('option');
            noMatchOption.disabled = true;
            noMatchOption.text = `No matches for "${searchTerm}"`;
            selectElement.add(noMatchOption);
        }
    }
    
    // Clear search and restore all options
    function clearSearch() {
        searchTerm = '';
        updatePlaceholder();
        resetOptions();
    }
    
    // Reset options to original list
    function resetOptions() {
        // Keep only the first placeholder option
        while (selectElement.options.length > 1) {
            selectElement.remove(1);
        }
        
        // Add all original options back
        originalOptions.forEach(option => {
            // Skip the first placeholder option
            if (option.disabled && option.selected) {
                return;
            }
            
            selectElement.add(option.cloneNode(true));
        });
    }
    
    // Ensure select has proper styling for searchable dropdown
    selectElement.classList.add('searchable-select');
    
    // Return utilities
    return {
        clearSearch,
        updateOptions: (newOptions) => {
            // Update stored options (useful if options change)
            originalOptions.length = 0;
            newOptions.forEach(option => originalOptions.push(option.cloneNode(true)));
        }
    };
}
