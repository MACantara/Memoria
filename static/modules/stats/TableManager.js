/**
 * Manages the upcoming review cards table and pagination
 */
export class TableManager {
    constructor() {
        this.currentPage = 1;
        this.filter = 'today'; // Default to today's reviews
    }
    
    /**
     * Initialize the table filter buttons
     */
    initializeFilterButtons() {
        // Set the Today button as active by default
        document.getElementById('showTodayBtn').classList.replace('btn-outline-primary', 'btn-primary');
        
        // Set up filter buttons for upcoming reviews table
        document.getElementById('showTodayBtn')?.addEventListener('click', () => {
            this.filterUpcomingReviews('today');
        });
        
        document.getElementById('showWeekBtn')?.addEventListener('click', () => {
            this.filterUpcomingReviews('week');
        });
        
        document.getElementById('showAllBtn')?.addEventListener('click', () => {
            this.filterUpcomingReviews('all');
        });
    }
    
    /**
     * Filter the upcoming reviews table
     */
    filterUpcomingReviews(filterType, callback) {
        // Reset all buttons to outline style
        document.querySelectorAll('.btn-group .btn').forEach(btn => {
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-outline-primary');
        });
        
        // Set active button style
        const activeButton = document.getElementById(`show${filterType.charAt(0).toUpperCase() + filterType.slice(1)}Btn`);
        if (activeButton) {
            activeButton.classList.remove('btn-outline-primary');
            activeButton.classList.add('btn-primary');
        }
        
        // Update filter and reset to first page
        this.filter = filterType;
        this.currentPage = 1;
        
        // Call the callback to reload the data with new filter
        if (typeof callback === 'function') {
            callback(this.filter, this.currentPage);
        }
        
        // Add some debug info
        console.log(`Filtered to: ${filterType}, page: ${this.currentPage}`);
    }
    
    /**
     * Updates the upcoming reviews table with data
     */
    updateUpcomingReviewsTable(data) {
        const tableBody = document.getElementById('upcomingReviewsBody');
        if (!tableBody) return;
        
        // Clear existing table content
        tableBody.innerHTML = '';
        
        // Check if we have any cards to display
        if (!data.cards || data.cards.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center">
                        <i class="bi bi-info-circle"></i> No upcoming reviews found.
                    </td>
                </tr>
            `;
            return;
        }
        
        // Update the count display
        const reviewCountElem = document.getElementById('reviewCount');
        if (reviewCountElem) {
            reviewCountElem.textContent = 
                `Showing ${data.cards.length} of ${data.pagination.total} cards`;
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
            
            // Create table row
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="align-middle">
                    <div class="text-truncate" style="max-width: 250px;" title="${card.question}">
                        ${card.question}
                    </div>
                </td>
                <td class="align-middle">${lastReviewed}</td>
                <td class="align-middle">${dueDate}</td>
                <td class="align-middle">
                    <span class="badge ${stateBadgeClass}">${card.state}</span>
                </td>
                <td class="align-middle">${card.state_value > 0 ? retrievability : 'N/A'}</td>
                <td class="align-middle">
                    <button class="btn btn-sm btn-primary review-now-btn" 
                            data-card-id="${card.id}" data-deck-id="${card.deck_id}">
                        Review
                    </button>
                </td>
            `;
            
            tableBody.appendChild(row);
        });
        
        // Add event listeners for the Review buttons
        document.querySelectorAll('.review-now-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const deckId = btn.dataset.deckId;
                window.location.href = `/deck/${deckId}/study?card_id=${btn.dataset.cardId}`;
            });
        });
    }
    
    /**
     * Update the pagination controls
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
        prevLink.href = '#';
        prevLink.innerHTML = '&laquo;';
        prevItem.appendChild(prevLink);
        paginationElement.appendChild(prevItem);
        
        // Page numbers
        for (let i = 1; i <= pagination.pages; i++) {
            const pageItem = document.createElement('li');
            pageItem.className = `page-item ${i === pagination.page ? 'active' : ''}`;
            const pageLink = document.createElement('a');
            pageLink.className = 'page-link';
            pageLink.href = '#';
            pageLink.textContent = i;
            pageLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.currentPage = i;
                if (typeof callback === 'function') {
                    callback(this.filter, this.currentPage);
                }
            });
            pageItem.appendChild(pageLink);
            paginationElement.appendChild(pageItem);
        }
        
        // Next button
        const nextItem = document.createElement('li');
        nextItem.className = `page-item ${!pagination.has_next ? 'disabled' : ''}`;
        const nextLink = document.createElement('a');
        nextLink.className = 'page-link';
        nextLink.href = '#';
        nextLink.innerHTML = '&raquo;';
        nextItem.appendChild(nextLink);
        paginationElement.appendChild(nextItem);
        
        // Add event listeners for next/previous
        if (pagination.has_prev) {
            prevLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.currentPage = pagination.prev_page;
                if (typeof callback === 'function') {
                    callback(this.filter, this.currentPage);
                }
            });
        }
        
        if (pagination.has_next) {
            nextLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.currentPage = pagination.next_page;
                if (typeof callback === 'function') {
                    callback(this.filter, this.currentPage);
                }
            });
        }
    }
    
    /**
     * Show error in the table
     */
    showError(message) {
        const tableBody = document.getElementById('upcomingReviewsBody');
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-danger">
                        <i class="bi bi-exclamation-triangle"></i> 
                        ${message || 'Failed to load upcoming reviews. Please try again.'}
                    </td>
                </tr>
            `;
        }
    }
}
