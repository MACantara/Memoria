/**
 * Handles loading stats data and updating the UI
 */
export class StatsLoader {
    constructor(deckId) {
        this.deckId = deckId;
    }
    
    /**
     * Load stats data and update summary cards
     */
    async loadStats() {
        try {
            const response = await fetch(`/stats/deck/${this.deckId}/stats`);
            const stats = await response.json();
            
            // Debug info
            console.log("Stats data:", stats);
            
            // Update each summary card
            this.updateSummaryCards(stats);
            
            // Return stats data for charts
            return stats;
        } catch (error) {
            console.error('Error loading stats:', error);
            throw error;
        }
    }
    
    /**
     * Update the stats summary cards with data
     */
    updateSummaryCards(stats) {
        // Update total cards
        document.getElementById('total-cards').textContent = stats.total_cards;
        
        // Update due count
        document.getElementById('due-count').textContent = stats.due_count;
        
        // Update mastered count
        document.getElementById('mastered-count').textContent = stats.state_counts.mastered;
        
        // Update retention data with coverage context
        this.updateRetentionCard(stats);
    }
    
    /**
     * Update the retention card with appropriate context and warnings
     */
    updateRetentionCard(stats) {
        const retentionElement = document.getElementById('retention');
        if (!retentionElement) return;
        
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
    }
    
    /**
     * Load retention distribution data - can be used for additional charts
     */
    async loadRetentionDistribution() {
        try {
            const response = await fetch(`/stats/deck/${this.deckId}/retention`);
            const retentionData = await response.json();
            
            // You can display this data in an additional chart if needed
            console.log("Retention distribution:", retentionData);
            
            return retentionData;
        } catch (error) {
            console.error('Error loading retention data:', error);
            throw error;
        }
    }
    
    /**
     * Load upcoming review cards data for the table - simplified without filter parameter
     */
    async loadUpcomingReviews(page = 1) {
        try {
            const url = new URL(`/stats/deck/${this.deckId}/upcoming-reviews`, window.location.origin);
            url.searchParams.append('page', page);
            url.searchParams.append('per_page', 20);
            
            const response = await fetch(url);
            const data = await response.json();
            
            // Process dates in the data to add local time versions if needed
            if (data.cards && data.cards.length > 0) {
                data.cards.forEach(card => {
                    // Add locally formatted date strings for use in components
                    if (card.due_date && card.due_date !== "Not scheduled") {
                        card.due_date_local = this.formatDateWithTimezone(card.due_date);
                    }
                    
                    if (card.last_reviewed && card.last_reviewed !== "Never") {
                        card.last_reviewed_local = this.formatDateWithTimezone(card.last_reviewed);
                    }
                });
            }
            
            console.log("Upcoming reviews data (with local dates):", data);
            
            return data;
        } catch (error) {
            console.error('Error loading upcoming reviews:', error);
            throw error;
        }
    }
    
    /**
     * Convert a UTC ISO string to local date object
     * @param {string} utcDateString - ISO date string in UTC format
     * @returns {Date} Date object in local time
     */
    convertToLocalDate(utcDateString) {
        if (!utcDateString) return null;
        
        try {
            // Create a date object - JS automatically converts to local time
            return new Date(utcDateString);
        } catch (error) {
            console.error("Error converting date:", error);
            return null;
        }
    }
    
    /**
     * Format a date object with local timezone information
     * @param {Date|string} date - Date object or ISO string
     * @returns {string} Formatted date string with timezone info
     */
    formatDateWithTimezone(date) {
        if (!date) return "N/A";
        
        try {
            // Convert string to Date if needed
            const dateObj = typeof date === 'string' ? new Date(date) : date;
            
            // Check if date is valid
            if (isNaN(dateObj.getTime())) return "Invalid Date";
            
            // Format with date, time and timezone
            return dateObj.toLocaleString(undefined, {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                timeZoneName: 'short'
            });
        } catch (error) {
            console.error("Error formatting date with timezone:", error);
            return String(date);
        }
    }
}
