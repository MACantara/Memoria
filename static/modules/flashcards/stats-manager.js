export class StatsManager {
    constructor(deckId) {
        this.deckId = deckId;
        this.stateChart = null;
        this.upcomingChart = null;
        this.observer = null;
        this.refreshInterval = null;
    }

    initialize() {
        this.loadStats();
        
        // Optional: Load advanced retention stats
        // this.loadRetentionDistribution();
        
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
                    // Good amount of data
                    retentionElement.textContent = retentionPct;
                    retentionElement.classList.remove('text-muted', 'text-warning');
                } else {
                    // Limited data - show with warning
                    retentionElement.textContent = `${retentionPct}*`;
                    retentionElement.classList.remove('text-muted');
                    retentionElement.classList.add('text-warning');
                    
                    // Add a tooltip explaining the asterisk
                    retentionElement.title = `Based on only ${stats.reviewed_count} out of ${stats.total_cards} cards (${stats.review_coverage}% coverage)`;
                    
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
