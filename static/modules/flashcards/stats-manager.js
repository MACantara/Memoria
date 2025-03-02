export class StatsManager {
    constructor(deckId) {
        this.deckId = deckId;
        this.stateChart = null;
        this.upcomingChart = null;
        this.observer = null;
        this.refreshInterval = null;
        this.upcomingFilter = 'week'; // Default to showing this week's reviews
        this.upcomingCurrentPage = 1;
    }

    initialize() {
        this.loadStats();
        this.loadUpcomingReviews();
        
        // Refresh stats every 30 seconds
        this.refreshInterval = setInterval(() => this.loadStats(), 30000);
        
        // Listen for theme changes to update charts
        this.observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'data-bs-theme') {
                    // Redraw charts when theme changes
                    this.loadStats();
                }
            });
        });
        
        this.observer.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['data-bs-theme']
        });
    }

    async loadStats() {
        try {
            const response = await fetch(`/stats/deck/${this.deckId}/stats`);
            const stats = await response.json();
            
            console.log("Stats data:", stats); // Debug info
            
            // Update summary cards
            document.getElementById('total-cards').textContent = stats.total_cards;
            document.getElementById('due-count').textContent = stats.due_count;
            
            // Handle retention data with coverage context
            const retentionElement = document.getElementById('retention');
            if (stats.has_retention_data) {
                // Format as percentage with coverage context
                const retentionPct = (stats.average_retention * 100).toFixed(0) + '%';
                
                if (stats.has_significant_retention_data) {
                    // Good amount of data (20+ cards or 10%+ coverage)
                    retentionElement.textContent = retentionPct;
                    retentionElement.classList.remove('text-muted', 'text-warning');
                } else {
                    // Limited data - show with warning
                    retentionElement.textContent = `${retentionPct}*`;
                    retentionElement.classList.remove('text-muted');
                    retentionElement.classList.add('text-warning');
                    
                    // Add a tooltip explaining the asterisk with updated thresholds
                    retentionElement.title = `Based on limited data: ${stats.reviewed_count} out of ${stats.total_cards} cards (${stats.review_coverage}% coverage). For reliable statistics, review at least 20 cards or 10% of the deck.`;
                    
                    // Add an explanation below if there's space
                    const retentionNoteElement = document.getElementById('retention-note');
                    if (retentionNoteElement) {
                        retentionNoteElement.textContent = 
                            `*Limited data (${stats.review_coverage}% of cards reviewed)`;
                        retentionNoteElement.classList.remove('d-none');
                    }
                }
            } else {
                // No review history available
                retentionElement.textContent = 'No data';
                retentionElement.classList.add('text-muted');
                retentionElement.classList.remove('text-warning');
                retentionElement.title = 'No cards have been reviewed yet';
                
                // Hide the note if present
                const retentionNoteElement = document.getElementById('retention-note');
                if (retentionNoteElement) {
                    retentionNoteElement.classList.add('d-none');
                }
            }
            
            document.getElementById('mastered-count').textContent = stats.state_counts.mastered;
            
            // Update charts
            this.updateStateChart(stats.state_counts);
            this.updateUpcomingChart(stats.upcoming_reviews);
            
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }
    
    async loadRetentionDistribution() {
        try {
            const response = await fetch(`/stats/deck/${this.deckId}/retention`);
            const retentionData = await response.json();
            
            // You can display this data in an additional chart if needed
            console.log("Retention distribution:", retentionData);
            
            // Build retention chart here if desired
            // this.updateRetentionChart(retentionData.retention_distribution);
            
        } catch (error) {
            console.error('Error loading retention data:', error);
        }
    }
    
    updateStateChart(stateCounts) {
        const ctx = document.getElementById('stateChart').getContext('2d');
        
        // Log the state counts for debugging
        console.log("State counts:", stateCounts);
        
        // Ensure we have numeric values for all states (default to 0)
        const data = [
            stateCounts.new || 0, 
            stateCounts.learning || 0,
            stateCounts.mastered || 0,
            stateCounts.forgotten || 0
        ];
        
        // Use theme-appropriate colors
        const isDarkMode = document.documentElement.getAttribute('data-bs-theme') === 'dark';
        const backgroundColor = [
            isDarkMode ? '#6c757d' : '#6c757d',  // New (gray)
            isDarkMode ? '#e6b400' : '#ffc107',  // Learning (yellow)
            isDarkMode ? '#198754' : '#28a745',  // Mastered (green)
            isDarkMode ? '#bb2d3b' : '#dc3545'   // Forgotten (red)
        ];
        
        // Adjust text/border colors based on theme
        const textColor = isDarkMode ? '#e0e0e0' : '#212529';
        const borderColor = isDarkMode ? '#2d2d2d' : '#ffffff';
        
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 1000 // Smoother animation for updates
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: textColor,
                        padding: 15,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: isDarkMode ? '#212121' : '#ffffff',
                    borderColor: isDarkMode ? '#3d3d3d' : '#e0e0e0',
                    borderWidth: 1,
                    bodyColor: textColor,
                    titleColor: textColor,
                    callbacks: {
                        label: function(context) {
                            let label = context.label || '';
                            let value = context.raw || 0;
                            let total = data.reduce((a, b) => a + b, 0);
                            let percentage = Math.round((value / total) * 100);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        };
        
        // If we already have a chart, update it
        if (this.stateChart) {
            this.stateChart.data.datasets[0].backgroundColor = backgroundColor;
            this.stateChart.data.datasets[0].data = data;
            this.stateChart.options = chartOptions;
            this.stateChart.update();
        } else {
            // Create a new chart
            this.stateChart = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: ['New', 'Learning', 'Mastered', 'Forgotten'],
                    datasets: [{
                        data: data,
                        backgroundColor: backgroundColor,
                        borderColor: borderColor,
                        borderWidth: 1
                    }]
                },
                options: chartOptions
            });
        }
        
        // Handle empty data case
        if (data.every(val => val === 0)) {
            ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
            ctx.font = '16px Arial';
            ctx.fillStyle = isDarkMode ? '#e0e0e0' : '#666';
            ctx.textAlign = 'center';
            ctx.fillText('No card data available', 
                         ctx.canvas.width / 2, ctx.canvas.height / 2);
        }
    }
    
    updateUpcomingChart(upcomingReviews) {
        const ctx = document.getElementById('upcomingChart').getContext('2d');
        const labels = [];
        const data = [];
        
        console.log("Upcoming reviews data:", upcomingReviews); // Debug info
        
        // Extract labels and data from reviews
        upcomingReviews.forEach(item => {
            try {
                // Parse the ISO date string
                const date = new Date(item.date);
                
                // Check if date is valid
                if (isNaN(date.getTime())) {
                    console.error("Invalid date:", item.date);
                    return;
                }
                
                // Format as "Mon DD"
                const formatted = date.toLocaleDateString('en-US', {
                    weekday: 'short',
                    day: 'numeric'
                });
                
                labels.push(formatted);
                data.push(item.count);
            } catch (e) {
                console.error("Error processing review date:", e);
            }
        });
        
        // Use theme-appropriate colors
        const isDarkMode = document.documentElement.getAttribute('data-bs-theme') === 'dark';
        
        // Theme-based colors
        const textColor = isDarkMode ? '#e0e0e0' : '#212529';
        const gridColor = isDarkMode ? '#444' : '#ddd';
        const barColor = isDarkMode ? 'rgba(13, 110, 253, 0.8)' : '#0d6efd';
        const barBorderColor = isDarkMode ? 'rgba(13, 110, 253, 1)' : '#0b5ed7';
        
        // Chart options
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: gridColor
                    },
                    ticks: {
                        precision: 0,
                        color: textColor
                    }
                },
                x: {
                    grid: {
                        color: gridColor
                    },
                    ticks: {
                        color: textColor
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: textColor
                    }
                },
                tooltip: {
                    backgroundColor: isDarkMode ? '#212121' : '#ffffff',
                    borderColor: isDarkMode ? '#3d3d3d' : '#e0e0e0',
                    borderWidth: 1,
                    bodyColor: textColor,
                    titleColor: textColor
                }
            }
        };
        
        // If chart exists, destroy it to prevent memory leaks
        if (this.upcomingChart) {
            this.upcomingChart.destroy();
        }
        
        // Handle empty data case
        if (!upcomingReviews || upcomingReviews.length === 0) {
            ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
            ctx.font = '16px Arial';
            ctx.fillStyle = isDarkMode ? '#e0e0e0' : '#666';
            ctx.textAlign = 'center';
            ctx.fillText('No upcoming reviews for the next 7 days', 
                        ctx.canvas.width / 2, ctx.canvas.height / 2);
            return;
        }
        
        // Create new chart
        this.upcomingChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: '# of Cards Due',
                    data: data,
                    backgroundColor: barColor,
                    borderColor: barBorderColor,
                    borderWidth: 1
                }]
            },
            options: chartOptions
        });
    }

    /**
     * Load upcoming review cards for the data table
     */
    async loadUpcomingReviews() {
        try {
            const url = new URL(`/stats/deck/${this.deckId}/upcoming-reviews`, window.location.origin);
            url.searchParams.append('filter', this.upcomingFilter);
            url.searchParams.append('page', this.upcomingCurrentPage);
            url.searchParams.append('per_page', 20);
            
            const response = await fetch(url);
            const data = await response.json();
            
            console.log("Upcoming reviews data:", data);
            
            // Update the table with the fetched data
            this.updateUpcomingReviewsTable(data);
            
            // Update pagination
            this.updatePagination(data.pagination);
            
        } catch (error) {
            console.error('Error loading upcoming reviews:', error);
            const tableBody = document.getElementById('upcomingReviewsBody');
            if (tableBody) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center text-danger">
                            <i class="bi bi-exclamation-triangle"></i> 
                            Failed to load upcoming reviews. Please try again.
                        </td>
                    </tr>
                `;
            }
        }
    }
    
    /**
     * Updates the upcoming reviews table with the fetched data
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
    updatePagination(pagination) {
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
                this.upcomingCurrentPage = i;
                this.loadUpcomingReviews();
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
                this.upcomingCurrentPage = pagination.prev_page;
                this.loadUpcomingReviews();
            });
        }
        
        if (pagination.has_next) {
            nextLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.upcomingCurrentPage = pagination.next_page;
                this.loadUpcomingReviews();
            });
        }
    }
    
    /**
     * Filter the upcoming reviews based on time period
     */
    filterUpcomingReviews(filterType) {
        // Update active filter button
        document.querySelectorAll('.btn-group .btn').forEach(btn => {
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-outline-primary');
        });
        
        document.getElementById(`show${filterType.charAt(0).toUpperCase() + filterType.slice(1)}Btn`)
            .classList.replace('btn-outline-primary', 'btn-primary');
        
        // Update filter and reload data
        this.upcomingFilter = filterType;
        this.upcomingCurrentPage = 1; // Reset to first page
        this.loadUpcomingReviews();
    }

    // Clean up method to prevent memory leaks
    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }

        if (this.observer) {
            this.observer.disconnect();
        }

        if (this.stateChart) {
            this.stateChart.destroy();
        }

        if (this.upcomingChart) {
            this.upcomingChart.destroy();
        }
    }
}
