/**
 * Manages the upcoming review cards table and pagination
 */
export class TableManager {
    constructor() {
        this.currentPage = 1;
        
        // Initialize the count display with a more informative loading state
        const reviewCountElem = document.getElementById('reviewCount');
        if (reviewCountElem) {
            reviewCountElem.innerHTML = '<i class="bi bi-hourglass"></i> Loading...';
        }
    }
    
    /**
     * Updates the upcoming reviews table with data
     */
    updateUpcomingReviewsTable(data) {
        const tableBody = document.getElementById('upcomingReviewsBody');
        if (!tableBody) return;
        
        // Clear existing table content
        tableBody.innerHTML = '';
        
        // Update the count display with a more meaningful message
        this.updateCountDisplay(data);
        
        // Check if we have any cards to display
        if (!data.cards || data.cards.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center">
                        <i class="bi bi-info-circle"></i> No upcoming reviews found.
                    </td>
                </tr>
            `;
            return;
        }
        
        // Populate the table with card data
        data.cards.forEach(card => {
            // Format dates for display
            const dueDate = card.due_date !== "Not scheduled" ? 
                new Date(card.due_date).toLocaleString() : "Not scheduled";
            
            const lastReviewed = card.last_reviewed !== "Never" ?
                new Date(card.last_reviewed).toLocaleString() : "Never";
            
            // Create state badge with appropriate color
            let stateBadgeClass = 'bg-secondary'; // default for "New"
            if (card.state_value === 1) stateBadgeClass = 'bg-warning text-dark';
            if (card.state_value === 2) stateBadgeClass = 'bg-success';
            if (card.state_value === 3) stateBadgeClass = 'bg-danger';
            
            // Format retrievability as percentage
            const retrievability = (card.retrievability * 100).toFixed(0) + '%';
            
            // Create table row with data-label attributes for responsive display
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="align-middle" data-label="Question">
                    <div class="text-truncate" style="max-width: 250px;" title="${card.question}">
                        ${card.question}
                    </div>
                </td>
                <td class="align-middle" data-label="Last Reviewed">${lastReviewed}</td>
                <td class="align-middle" data-label="Due Date">${dueDate}</td>
                <td class="align-middle" data-label="State">
                    <span class="badge ${stateBadgeClass}">${card.state}</span>
                </td>
                <td class="align-middle" data-label="Retention">${card.state_value > 0 ? retrievability : 'N/A'}</td>
            `;
            
            tableBody.appendChild(row);
        });
    }
    
    /**
     * Update the count display with a more meaningful message
     */
    updateCountDisplay(data) {
        const reviewCountElem = document.getElementById('reviewCount');
        if (!reviewCountElem) return;
        
        if (!data || !data.pagination) {
            reviewCountElem.innerHTML = '<i class="bi bi-x-circle"></i> No data available';
            return;
        }
        
        const { total, page, per_page } = data.pagination;
        const currentCards = data.cards ? data.cards.length : 0;
        
        if (total === 0) {
            // No cards at all
            reviewCountElem.innerHTML = '<i class="bi bi-card-list"></i> No upcoming reviews scheduled';
        } else if (currentCards === 0) {
            // No cards on this page (should rarely happen)
            reviewCountElem.innerHTML = `<i class="bi bi-card-list"></i> No cards on this page (of ${total} total)`;
        } else {
            // Calculate the range of cards being shown
            const startCard = (page - 1) * per_page + 1;
            const endCard = Math.min(startCard + currentCards - 1, total);
            
            // Show range of cards: "Showing 1-20 of 57 cards"
            reviewCountElem.innerHTML = `
                <i class="bi bi-card-list"></i> 
                Showing ${startCard}-${endCard} of ${total} ${total === 1 ? 'card' : 'cards'}
            `;
        }
    }
    
    /**
     * Update the pagination controls with dropdown page selector and URL state management
     */
    updatePagination(pagination, callback) {
        const paginationElement = document.querySelector('#upcomingPagination .pagination');
        if (!paginationElement) return;
        
        // Clear existing pagination
        paginationElement.innerHTML = '';
        
        // Only show pagination if we have multiple pages
        if (pagination.pages <= 1) return;
        
        // Previous button
        const prevItem = document.createElement('li');
        prevItem.className = `page-item ${!pagination.has_prev ? 'disabled' : ''}`;
        const prevLink = document.createElement('a');
        prevLink.className = 'page-link';
        prevLink.href = '#'; // Default to hash
        prevLink.setAttribute('aria-label', 'Previous');
        prevLink.innerHTML = '<i class="bi bi-chevron-left"></i>';
        prevItem.appendChild(prevLink);
        paginationElement.appendChild(prevItem);
        
        // Page dropdown
        const pageDropdownItem = document.createElement('li');
        pageDropdownItem.className = 'page-item dropdown';
        
        // Create dropdown toggle button
        const dropdownButton = document.createElement('a');
        dropdownButton.className = 'page-link dropdown-toggle';
        dropdownButton.href = '#';
        dropdownButton.setAttribute('data-bs-toggle', 'dropdown');
        dropdownButton.setAttribute('aria-expanded', 'false');
        dropdownButton.setAttribute('role', 'button');
        dropdownButton.innerHTML = `Page ${pagination.page} of ${pagination.pages}`;
        pageDropdownItem.appendChild(dropdownButton);
        
        // Create dropdown menu
        const dropdownMenu = document.createElement('ul');
        dropdownMenu.className = 'dropdown-menu';
        
        // Generate the base URL for pagination - safely
        let baseUrlPath;
        try {
            // First try to use the deck_id from pagination to build a path
            if (pagination.urls && pagination.urls.base_url) {
                // Try to extract just the path without query parameters
                const urlObj = new URL(pagination.urls.base_url, window.location.origin);
                baseUrlPath = urlObj.pathname;
            } else {
                // Fall back to current path without query params
                baseUrlPath = window.location.pathname;
            }
        } catch (error) {
            console.warn("Error creating base URL, using current path:", error);
            baseUrlPath = window.location.pathname;
        }
        
        // Add dropdown items for each page
        for (let i = 1; i <= pagination.pages; i++) {
            const dropdownItem = document.createElement('li');
            const dropdownLink = document.createElement('a');
            dropdownLink.className = `dropdown-item ${i === pagination.page ? 'active' : ''}`;
            
            // Build URL with query params (safer method)
            const params = new URLSearchParams();
            params.set('page', i);
            
            // Final URL construction
            dropdownLink.href = `${baseUrlPath}?${params.toString()}`;
            dropdownLink.textContent = `Page ${i}`;
            dropdownLink.setAttribute('data-page', i);
            
            dropdownLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.currentPage = i;
                
                // Update browser URL without reload - safely
                try {
                    if (history.pushState) {
                        history.pushState(null, null, dropdownLink.href);
                    }
                } catch (error) {
                    console.warn("Error updating URL history:", error);
                }
                
                if (typeof callback === 'function') {
                    callback(i);
                }
            });
            
            dropdownItem.appendChild(dropdownLink);
            dropdownMenu.appendChild(dropdownItem);
        }
        
        pageDropdownItem.appendChild(dropdownMenu);
        paginationElement.appendChild(pageDropdownItem);
        
        // Next button - using same safe URL construction
        const nextItem = document.createElement('li');
        nextItem.className = `page-item ${!pagination.has_next ? 'disabled' : ''}`;
        const nextLink = document.createElement('a');
        nextLink.className = 'page-link';
        nextLink.href = '#';
        if (pagination.has_next) {
            const nextParams = new URLSearchParams();
            nextParams.set('page', pagination.next_page);
            nextLink.href = `${baseUrlPath}?${nextParams.toString()}`;
        }
        nextLink.setAttribute('aria-label', 'Next');
        nextLink.innerHTML = '<i class="bi bi-chevron-right"></i>';
        nextItem.appendChild(nextLink);
        paginationElement.appendChild(nextItem);
        
        // Set prev link href using same safe method
        if (pagination.has_prev) {
            const prevParams = new URLSearchParams();
            prevParams.set('page', pagination.prev_page);
            prevLink.href = `${baseUrlPath}?${prevParams.toString()}`;
        }
        
        // Add event listeners for next/previous with URL updates
        if (pagination.has_prev) {
            prevLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.currentPage = pagination.prev_page;
                
                // Update browser URL without reload - safely
                try {
                    if (history.pushState) {
                        history.pushState(null, null, prevLink.href);
                    }
                } catch (error) {
                    console.warn("Error updating URL history:", error);
                }
                
                if (typeof callback === 'function') {
                    callback(this.currentPage);
                }
            });
        }
        
        if (pagination.has_next) {
            nextLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.currentPage = pagination.next_page;
                
                // Update browser URL without reload - safely
                try {
                    if (history.pushState) {
                        history.pushState(null, null, nextLink.href);
                    }
                } catch (error) {
                    console.warn("Error updating URL history:", error);
                }
                
                if (typeof callback === 'function') {
                    callback(this.currentPage);
                }
            });
        }
        
        // For debugging
        console.log("Pagination setup complete:", {
            currentPage: pagination.page,
            totalPages: pagination.pages,
            baseUrlPath
        });
    }
    
    /**
     * Show error in the table - improved for mobile
     */
    showError(message) {
        const tableBody = document.getElementById('upcomingReviewsBody');
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center">
                        <div class="py-4">
                            <i class="bi bi-exclamation-triangle text-danger" style="font-size: 2rem;"></i>
                            <p class="mt-3">
                                ${message || 'Failed to load upcoming reviews. Please try again.'}
                            </p>
                            <button class="btn btn-sm btn-outline-primary mt-2" onclick="window.location.reload()">
                                <i class="bi bi-arrow-clockwise"></i> Retry
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }
        
        // Update the count display to show error
        const reviewCountElem = document.getElementById('reviewCount');
        if (reviewCountElem) {
            reviewCountElem.innerHTML = '<i class="bi bi-exclamation-triangle text-danger"></i> Error loading data';
        }
    }
}
