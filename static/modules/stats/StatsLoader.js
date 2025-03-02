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
     * Load upcoming review cards data for the table - simplified
     */
    async loadUpcomingReviews(filter = 'all', page = 1) {
        try {
            const url = new URL(`/stats/deck/${this.deckId}/upcoming-reviews`, window.location.origin);
            url.searchParams.append('filter', filter); // Always 'all'
            url.searchParams.append('page', page);
            url.searchParams.append('per_page', 20);
            
            const response = await fetch(url);
            const data = await response.json();
            
            console.log("Upcoming reviews data:", data);
            
            return data;
        } catch (error) {
            console.error('Error loading upcoming reviews:', error);
            throw error;
        }
    }
}
