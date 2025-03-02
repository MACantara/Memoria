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
        
        // Get initial page from URL if available
        const urlParams = new URLSearchParams(window.location.search);
        const pageParam = urlParams.get('page');
        if (pageParam && !isNaN(parseInt(pageParam))) {
            this.tableManager.currentPage = parseInt(pageParam);
        }
        
        // Timer and observer for updates and theme changes
        this.observer = null;
        this.refreshInterval = null;
    }

    initialize() {
        // Load initial data
        this.loadAllStats();
        
        // Handle browser back/forward navigation
        window.addEventListener('popstate', () => {
            // Re-extract the page from URL when navigating with browser buttons
            const urlParams = new URLSearchParams(window.location.search);
            const pageParam = urlParams.get('page');
            if (pageParam && !isNaN(parseInt(pageParam))) {
                this.tableManager.currentPage = parseInt(pageParam);
                this.loadUpcomingReviews(this.tableManager.currentPage);
            } else {
                this.tableManager.currentPage = 1;
                this.loadUpcomingReviews(1);
            }
        });
        
        // Bind the loadUpcomingReviews method to this instance for callbacks
        const loadUpcomingReviewsCallback = this.loadUpcomingReviews.bind(this);
        
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
            
            // Load table data - always using 'all' filter now
            await this.loadUpcomingReviews(1);
        } catch (error) {
            console.error('Error loading all stats:', error);
        }
    }
    
    /**
     * Load upcoming reviews and update the table
     * No longer takes a filter parameter, just page number
     */
    async loadUpcomingReviews(page = 1) {
        try {
            // No filter parameter needed anymore
            const reviewsData = await this.statsLoader.loadUpcomingReviews(page);
            
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
