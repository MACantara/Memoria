import { ChartManager } from './ChartManager.js';
import { TableManager } from './TableManager.js';
import { StatsLoader } from './StatsLoader.js';

/**
 * Main manager class that orchestrates all stats components
 */
export class StatsManager {
    constructor(deckId) {
        this.deckId = deckId;
        
        // Initialize components
        this.chartManager = new ChartManager();
        this.tableManager = new TableManager();
        this.statsLoader = new StatsLoader(deckId);
        
        // Timer and observer for updates and theme changes
        this.observer = null;
        this.refreshInterval = null;
    }

    initialize() {
        // Load initial data
        this.loadAllStats();
        
        // Initialize table filter buttons
        this.tableManager.initializeFilterButtons();
        
        // Bind the loadUpcomingReviews method to this instance for callbacks
        const loadUpcomingReviewsCallback = this.loadUpcomingReviews.bind(this);
        
        // Set filter callback to reload data when filter changes
        const originalFilterMethod = this.tableManager.filterUpcomingReviews;
        this.tableManager.filterUpcomingReviews = function(filterType) {
            originalFilterMethod.call(this, filterType, loadUpcomingReviewsCallback);
        };
        
        // Refresh stats every 30 seconds
        this.refreshInterval = setInterval(() => this.loadAllStats(), 30000);
        
        // Listen for theme changes to update charts
        this.observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'data-bs-theme') {
                    // Redraw charts when theme changes
                    this.loadAllStats();
                }
            });
        });
        
        this.observer.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['data-bs-theme']
        });
    }
    
    /**
     * Load all stats data and update UI components
     */
    async loadAllStats() {
        try {
            // Load summary stats
            const stats = await this.statsLoader.loadStats();
            
            // Update charts with the data
            this.chartManager.updateStateChart(stats.state_counts);
            this.chartManager.updateUpcomingChart(stats.upcoming_reviews);
            
            // Load table data with current filter and page
            await this.loadUpcomingReviews(this.tableManager.filter, this.tableManager.currentPage);
        } catch (error) {
            console.error('Error loading all stats:', error);
        }
    }
    
    /**
     * Load upcoming reviews and update the table
     */
    async loadUpcomingReviews(filter, page) {
        try {
            // Load reviews for the table with current filter and page
            const reviewsData = await this.statsLoader.loadUpcomingReviews(filter, page);
            
            // Update table and pagination
            this.tableManager.updateUpcomingReviewsTable(reviewsData);
            
            // Use the callback pattern to pass the loadUpcomingReviews method for pagination clicks
            const loadUpcomingReviewsCallback = this.loadUpcomingReviews.bind(this);
            this.tableManager.updatePagination(reviewsData.pagination, loadUpcomingReviewsCallback);
            
            return reviewsData;
        } catch (error) {
            console.error('Error loading upcoming reviews:', error);
            this.tableManager.showError('Failed to load upcoming reviews. Please try again.');
        }
    }

    /**
     * Clean up method to prevent memory leaks
     */
    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }

        if (this.observer) {
            this.observer.disconnect();
        }

        // Clean up chart resources
        this.chartManager.destroy();
    }
}
