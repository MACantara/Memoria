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
                    callback(i);
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
                    callback(this.currentPage);
                }
            });
        }
        
        if (pagination.has_next) {
            nextLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.currentPage = pagination.next_page;
                if (typeof callback === 'function') {
                    callback(this.currentPage);
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
                    <td colspan="5" class="text-center text-danger">
                        <i class="bi bi-exclamation-triangle"></i> 
                        ${message || 'Failed to load upcoming reviews. Please try again.'}
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
