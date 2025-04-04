/**
 * Import Tracker - Handles tracking and updating import tasks
 */
class ImportTracker {
    constructor() {
        this.container = document.getElementById('importTrackerContainer');
        this.noImportsMessage = document.getElementById('noImportsMessage');
        this.importsList = document.getElementById('importsList');
        this.template = document.getElementById('importTaskTemplate');
        this.refreshButton = document.getElementById('refreshImportsBtn');
        this.tasks = {};
        this.pollingInterval = null;
        this.initialized = false;
    }

    initialize() {
        if (!this.container || this.initialized) return;
        
        // Attach event listeners
        if (this.refreshButton) {
            this.refreshButton.addEventListener('click', () => this.refreshTasks());
        }
        
        // Start polling for updates
        this.startPolling();
        
        // Load initial tasks
        this.refreshTasks();
        
        this.initialized = true;
        console.log('Import tracker initialized');
    }
    
    startPolling(intervalMs = 5000) {
        // Clear any existing interval
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
        }
        
        // Set up polling
        this.pollingInterval = setInterval(() => {
            this.refreshTasks();
        }, intervalMs);
        
        console.log(`Polling started with interval ${intervalMs}ms`);
    }
    
    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
            console.log('Polling stopped');
        }
    }
    
    async refreshTasks() {
        try {
            const response = await fetch('/import/import-tasks');
            if (!response.ok) {
                throw new Error('Failed to fetch import tasks');
            }
            
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Unknown error');
            }
            
            // Process the tasks
            this.updateTasks(data.tasks);
            
            // Also update the stats counters in the dashboard if they exist
            this.updateStatCounters(data.tasks);
        } catch (error) {
            console.error('Error refreshing tasks:', error);
        }
    }
    
    updateStatCounters(tasks) {
        // Update the stats counters if they exist on the page
        const activeCounter = document.getElementById('activeTasksCount');
        const completedCounter = document.getElementById('completedTasksCount');
        const failedCounter = document.getElementById('failedTasksCount');
        const totalCardsCounter = document.getElementById('totalSavedCardsCount');
        
        if (!activeCounter && !completedCounter && !failedCounter && !totalCardsCounter) {
            // No counters on this page
            return;
        }
        
        // Count tasks by status
        const activeCount = tasks.filter(t => t.status === 'pending' || t.status === 'running').length;
        const completedCount = tasks.filter(t => t.status === 'completed').length;
        const failedCount = tasks.filter(t => t.status === 'failed').length;
        
        // Sum up all saved cards
        const totalSavedCards = tasks.reduce((sum, task) => sum + (task.saved_cards || 0), 0);
        
        // Update the counters
        if (activeCounter) activeCounter.textContent = activeCount;
        if (completedCounter) completedCounter.textContent = completedCount;
        if (failedCounter) failedCounter.textContent = failedCount;
        if (totalCardsCounter) totalCardsCounter.textContent = totalSavedCards;
    }
    
    updateTasks(tasks) {
        // Reset the tracking object
        this.tasks = {};
        
        // Process all tasks
        tasks.forEach(task => {
            this.tasks[task.id] = task;
        });
        
        // Update the UI
        this.renderTasks();
        
        // Check if we should stop polling (no active tasks)
        const activeTasks = tasks.filter(t => t.status === 'pending' || t.status === 'running');
        if (activeTasks.length === 0 && this.pollingInterval) {
            console.log('No active tasks, reducing polling frequency');
            // Reduce polling frequency if no active tasks
            this.startPolling(30000); // 30 seconds
        } else if (activeTasks.length > 0) {
            // Ensure frequent polling for active tasks
            if (!this.pollingInterval || this.pollingInterval._idleTimeout > 5000) {
                this.startPolling(5000); // 5 seconds
            }
        }
    }
    
    renderTasks() {
        // Clear the list
        if (this.importsList) {
            this.importsList.innerHTML = '';
        }
        
        // Get all tasks as array and sort by creation date (newest first)
        const tasksArray = Object.values(this.tasks).sort((a, b) => {
            return new Date(b.created_at) - new Date(a.created_at);
        });
        
        // Show/hide no imports message
        if (tasksArray.length === 0) {
            this.noImportsMessage.classList.remove('d-none');
            return;
        } else {
            this.noImportsMessage.classList.add('d-none');
        }
        
        // Add each task to the list
        tasksArray.forEach(task => {
            const taskElement = this.createTaskElement(task);
            this.importsList.appendChild(taskElement);
        });
    }
    
    createTaskElement(task) {
        // Clone the template
        const taskElement = this.template.content.cloneNode(true).querySelector('.import-task-item');
        
        // Set task ID and status data attributes
        taskElement.dataset.taskId = task.id;
        taskElement.dataset.status = task.status;
        
        // Set basic information
        taskElement.querySelector('.import-filename').textContent = task.filename;
        taskElement.querySelector('.import-deck').textContent = task.deck_name;
        
        // Set status badge
        const statusBadge = taskElement.querySelector('.status-badge');
        switch (task.status) {
            case 'pending':
                statusBadge.textContent = 'Pending';
                statusBadge.classList.add('bg-secondary');
                break;
            case 'running':
                statusBadge.textContent = 'Processing';
                statusBadge.classList.add('bg-primary');
                break;
            case 'completed':
                statusBadge.textContent = 'Completed';
                statusBadge.classList.add('bg-success');
                break;
            case 'failed':
                statusBadge.textContent = 'Failed';
                statusBadge.classList.add('bg-danger');
                break;
        }
        
        // Set progress bar
        const progressBar = taskElement.querySelector('.progress-bar');
        progressBar.style.width = `${task.progress}%`;
        progressBar.setAttribute('aria-valuenow', task.progress);
        progressBar.textContent = `${task.progress}%`;
        
        // For failed tasks, change progress bar color
        if (task.status === 'failed') {
            progressBar.classList.remove('progress-bar-striped', 'progress-bar-animated');
            progressBar.classList.add('bg-danger');
            
            // Add error message if available
            if (task.error) {
                const errorElement = document.createElement('div');
                errorElement.className = 'error-message small text-danger mt-1';
                errorElement.innerHTML = `<i class="bi bi-exclamation-circle me-1"></i>${task.error}`;
                
                const statsElement = taskElement.querySelector('.import-stats');
                statsElement.parentNode.insertBefore(errorElement, statsElement.nextSibling);
            }
        }
        
        // For completed tasks, show solid bar
        if (task.status === 'completed') {
            progressBar.classList.remove('progress-bar-striped', 'progress-bar-animated');
            progressBar.textContent = 'Complete';
        }
        
        // Set stats
        const statsElement = taskElement.querySelector('.import-stats');
        const createdDate = new Date(task.created_at);
        
        if (task.saved_cards > 0) {
            statsElement.innerHTML = `
                <span class="badge bg-success rounded-pill me-2">${task.saved_cards} cards</span>
                <span class="text-muted">${this.formatDate(createdDate)}</span>
            `;
        } else {
            statsElement.innerHTML = `
                <span class="text-muted">${this.formatDate(createdDate)}</span>
            `;
        }
        
        // Show view deck button for completed tasks
        const viewDeckBtn = taskElement.querySelector('.view-deck-btn');
        if (task.status === 'completed' && viewDeckBtn) {
            viewDeckBtn.classList.remove('d-none');
            viewDeckBtn.addEventListener('click', () => {
                window.location.href = `/deck/${task.deck_id}`;
            });
        }
        
        return taskElement;
    }
    
    formatDate(date) {
        // Short date/time format
        const now = new Date();
        const diffMs = now - date;
        const diffSec = Math.round(diffMs / 1000);
        const diffMin = Math.round(diffSec / 60);
        const diffHours = Math.round(diffMin / 60);
        const diffDays = Math.round(diffHours / 24);
        
        if (diffSec < 60) return 'just now';
        if (diffMin < 60) return `${diffMin}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        
        // Fall back to simple date format
        return date.toLocaleDateString();
    }
}

// Initialize the tracker when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const tracker = new ImportTracker();
    tracker.initialize();
    
    // Make the tracker globally available
    window.importTracker = tracker;
});
