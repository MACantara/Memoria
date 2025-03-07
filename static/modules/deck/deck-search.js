/**
 * Enhanced deck search utility that creates an integrated search field + dropdown
 */
export function initializeDeckSearch(selectElement, options = {}) {
    if (!selectElement) return;
    
    // Check if this select has already been processed
    if (selectElement.dataset.searchInitialized === 'true') {
        return;
    }
    
    // Mark this element as processed
    selectElement.dataset.searchInitialized = 'true';
    
    // Create the container for our custom search control
    const container = document.createElement('div');
    container.className = 'deck-search-container';
    selectElement.parentNode.insertBefore(container, selectElement);
    
    // Hide the original select element but keep it in the DOM for form submission
    selectElement.style.display = 'none';
    container.appendChild(selectElement);
    
    // Create the search input field
    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.className = 'form-control deck-search-input';
    searchInput.placeholder = options.placeholder || 'Search decks...';
    container.appendChild(searchInput);
    
    // Create the dropdown container
    const dropdownContainer = document.createElement('div');
    dropdownContainer.className = 'deck-search-dropdown';
    container.appendChild(dropdownContainer);
    
    // Store original options for filtering
    const originalOptions = Array.from(selectElement.options).filter(option => !option.disabled);
    
    // Selected deck info display
    const selectedDeckInfo = document.createElement('div');
    selectedDeckInfo.className = 'selected-deck-info';
    container.appendChild(selectedDeckInfo);
    
    // Track state
    let isOpen = false;
    let selectedIndex = -1;
    
    // Event handlers
    searchInput.addEventListener('focus', showDropdown);
    searchInput.addEventListener('input', filterOptions);
    searchInput.addEventListener('keydown', handleKeyNavigation);
    document.addEventListener('click', handleOutsideClick);
    
    // Initial state setup
    updateSelectedDeckInfo();
    
    // Show the dropdown list
    function showDropdown() {
        dropdownContainer.innerHTML = ''; // Clear existing options
        
        const options = filterOptions();
        if (options.length === 0) {
            // Show empty state
            const emptyState = document.createElement('div');
            emptyState.className = 'deck-search-empty';
            emptyState.textContent = 'No matching decks found';
            dropdownContainer.appendChild(emptyState);
        }
        
        dropdownContainer.classList.add('show');
        isOpen = true;
    }
    
    // Hide the dropdown list
    function hideDropdown() {
        dropdownContainer.classList.remove('show');
        isOpen = false;
    }
    
    // Filter options based on search text
    function filterOptions() {
        const searchText = searchInput.value.toLowerCase();
        dropdownContainer.innerHTML = ''; // Clear existing options
        
        const filteredOptions = originalOptions.filter(option => {
            return option.textContent.toLowerCase().includes(searchText);
        });
        
        filteredOptions.forEach((option, index) => {
            const optionElement = document.createElement('div');
            optionElement.className = 'deck-search-option';
            optionElement.dataset.value = option.value;
            optionElement.dataset.index = index;
            
            // Add additional data attributes from original option
            if (option.dataset) {
                Object.keys(option.dataset).forEach(key => {
                    optionElement.dataset[key] = option.dataset[key];
                });
            }
            
            // Style differently if it's a subdeck
            const isDeckItem = option.textContent.includes('└');
            if (isDeckItem) {
                optionElement.classList.add('subdeck-item');
            }
            
            // Add selection styling
            if (index === selectedIndex) {
                optionElement.classList.add('selected');
            }
            
            // Highlight matching text
            let displayText = option.textContent;
            if (searchText) {
                const regex = new RegExp(`(${searchText})`, 'gi');
                displayText = displayText.replace(regex, '<mark>$1</mark>');
            }
            
            optionElement.innerHTML = displayText;
            
            optionElement.addEventListener('click', () => {
                selectOption(option.value, option.textContent, option);
                hideDropdown();
            });
            
            dropdownContainer.appendChild(optionElement);
        });
        
        if (filteredOptions.length > 0) {
            // Set the first item as pre-selected for keyboard navigation
            selectedIndex = 0;
            const firstOption = dropdownContainer.querySelector('.deck-search-option');
            if (firstOption) firstOption.classList.add('selected');
        } else {
            selectedIndex = -1;
        }
        
        return filteredOptions;
    }
    
    // Handle keyboard navigation
    function handleKeyNavigation(event) {
        const options = dropdownContainer.querySelectorAll('.deck-search-option');
        
        switch(event.key) {
            case 'ArrowDown':
                event.preventDefault();
                if (!isOpen) {
                    showDropdown();
                    return;
                }
                selectedIndex = Math.min(selectedIndex + 1, options.length - 1);
                updateSelectedOption();
                break;
                
            case 'ArrowUp':
                event.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, 0);
                updateSelectedOption();
                break;
                
            case 'Enter':
                event.preventDefault();
                if (isOpen && selectedIndex >= 0 && selectedIndex < options.length) {
                    const option = options[selectedIndex];
                    selectOption(option.dataset.value, option.textContent, option);
                    hideDropdown();
                } else if (!isOpen) {
                    showDropdown();
                }
                break;
                
            case 'Escape':
                event.preventDefault();
                hideDropdown();
                break;
        }
    }
    
    // Update which option is visually selected
    function updateSelectedOption() {
        const options = dropdownContainer.querySelectorAll('.deck-search-option');
        options.forEach((option, index) => {
            if (index === selectedIndex) {
                option.classList.add('selected');
                // Scroll into view if needed
                option.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            } else {
                option.classList.remove('selected');
            }
        });
    }
    
    // Select an option and update the original select element
    function selectOption(value, text, optionElement) {
        // Update the original select
        selectElement.value = value;
        
        // Trigger change event on the original select
        const event = new Event('change', { bubbles: true });
        selectElement.dispatchEvent(event);
        
        // Update the search input to show the selected value
        searchInput.value = text;
        
        // Update selected info display
        updateSelectedDeckInfo(optionElement);
    }
    
    // Handle clicks outside the component to close dropdown
    function handleOutsideClick(event) {
        if (isOpen && !container.contains(event.target)) {
            hideDropdown();
        }
    }
    
    // Update the selected deck info display if available
    function updateSelectedDeckInfo(optionElement) {
        // Clear the current content
        selectedDeckInfo.innerHTML = '';
        
        if (!optionElement) {
            // If no option is selected, hide the info box
            selectedDeckInfo.style.display = 'none';
            return;
        }
        
        // Check if we have additional data to display
        const hasParent = optionElement.dataset && optionElement.dataset.parent;
        const cardCount = optionElement.dataset && optionElement.dataset.cardCount;
        const dueCount = optionElement.dataset && optionElement.dataset.dueCount;
        
        if (hasParent || cardCount || dueCount) {
            selectedDeckInfo.style.display = 'block';
            
            if (hasParent) {
                const parentInfo = document.createElement('div');
                parentInfo.className = 'parent-deck-info text-muted small';
                parentInfo.innerHTML = `<i class="bi bi-folder2"></i> Sub-deck of: ${optionElement.dataset.parent}`;
                selectedDeckInfo.appendChild(parentInfo);
            }
            
            if (cardCount || dueCount) {
                const countInfo = document.createElement('div');
                countInfo.className = 'card-count-info text-muted small mt-1';
                
                if (dueCount && cardCount) {
                    countInfo.innerHTML = `
                        <span class="badge bg-primary me-1">${dueCount} due</span>
                        <span>${cardCount} total cards</span>
                    `;
                } else if (cardCount) {
                    countInfo.innerHTML = `<span>${cardCount} total cards</span>`;
                }
                
                selectedDeckInfo.appendChild(countInfo);
            }
        } else {
            selectedDeckInfo.style.display = 'none';
        }
    }
    
    // Initialize with any pre-selected value
    if (selectElement.value) {
        const selectedOption = selectElement.options[selectElement.selectedIndex];
        searchInput.value = selectedOption.textContent;
        updateSelectedDeckInfo(selectedOption);
    }
    
    return {
        searchInput,
        selectElement,
        reset: () => {
            selectElement.selectedIndex = 0;
            searchInput.value = '';
            updateSelectedDeckInfo();
        },
        setValue: (value) => {
            selectElement.value = value;
            if (value) {
                const option = selectElement.options[selectElement.selectedIndex];
                searchInput.value = option.textContent;
                updateSelectedDeckInfo(option);
            } else {
                searchInput.value = '';
                updateSelectedDeckInfo();
            }
        }
    };
}
