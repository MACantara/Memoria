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
        } catch (error) {
            console.error('Error refreshing tasks:', error);
        }
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
        
        // Set task ID
        taskElement.dataset.taskId = task.id;
        
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
        }
        
        // For completed tasks, show solid bar
        if (task.status === 'completed') {
            progressBar.classList.remove('progress-bar-striped', 'progress-bar-animated');
            progressBar.textContent = 'Complete';
        }
        
        // Set stats
        const statsElement = taskElement.querySelector('.import-stats');
        if (task.saved_cards > 0) {
            statsElement.textContent = `${task.saved_cards} cards saved`;
        } else {
            statsElement.textContent = 'Processing...';
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
}

// Initialize the tracker when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const tracker = new ImportTracker();
    tracker.initialize();
    
    // Make the tracker globally available
    window.importTracker = tracker;
});
