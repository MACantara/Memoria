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
        // Create a map of current tasks for quick lookups
        const currentTasks = Object.keys(this.tasks).reduce((acc, taskId) => {
            acc[taskId] = this.tasks[taskId];
            return acc;
        }, {});

        // Process all tasks
        tasks.forEach(task => {
            const taskId = task.id;
            this.tasks[taskId] = task;

            // If this task element already exists in the UI, update it instead of recreating
            const existingElement = document.querySelector(`.import-task-item[data-task-id="${taskId}"]`);
            if (existingElement) {
                this.updateTaskElement(existingElement, task);
            }
        });
        
        // Check if we need to add or remove elements
        const currentTaskIds = Object.keys(currentTasks);
        const newTaskIds = tasks.map(t => t.id);
        
        // Find tasks that were removed
        const removedTaskIds = currentTaskIds.filter(id => !newTaskIds.includes(id));
        
        // Remove elements that are no longer in the task list
        removedTaskIds.forEach(taskId => {
            delete this.tasks[taskId];
            const element = document.querySelector(`.import-task-item[data-task-id="${taskId}"]`);
            if (element) {
                // Add fade-out animation
                element.style.opacity = '0';
                element.style.transform = 'translateY(-10px)';
                element.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                
                // Remove after animation completes
                setTimeout(() => element.remove(), 300);
            }
        });
        
        // Update the UI - will only render new tasks since we already updated existing ones
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
        // Don't clear the entire list, as we've already updated existing elements
        // Only add new tasks that aren't in the DOM yet
        
        // Get all tasks as array and sort by creation date (newest first)
        const tasksArray = Object.values(this.tasks).sort((a, b) => {
            return new Date(b.created_at) - new Date(a.created_at);
        });
        
        // Show/hide no imports message
        if (tasksArray.length === 0) {
            this.noImportsMessage.classList.remove('d-none');
            // If the list exists, clear it
            if (this.importsList) {
                this.importsList.innerHTML = '';
            }
            return;
        } else {
            this.noImportsMessage.classList.add('d-none');
        }
        
        // Add each new task to the list
        tasksArray.forEach(task => {
            const taskId = task.id;
            const existingElement = document.querySelector(`.import-task-item[data-task-id="${taskId}"]`);
            
            // Only create and add elements that don't already exist in the DOM
            if (!existingElement) {
                const taskElement = this.createTaskElement(task);
                
                // Add with fade-in animation
                taskElement.style.opacity = '0';
                taskElement.style.transform = 'translateY(10px)';
                
                // Add to the list
                this.importsList.appendChild(taskElement);
                
                // Trigger reflow to ensure animation works
                void taskElement.offsetWidth;
                
                // Apply transition
                taskElement.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                taskElement.style.opacity = '1';
                taskElement.style.transform = 'translateY(0)';
            }
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
                statusBadge.classList.add('bg-warning');
                break;
            case 'running':
                statusBadge.textContent = 'Processing';
                statusBadge.classList.add('bg-warning');
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
        
        // Set progress bar with animation
        const progressBar = taskElement.querySelector('.progress-bar');
        
        // Store current progress to enable animation
        progressBar.dataset.prevProgress = 0;
        
        // Set initial progress
        const progress = Math.min(Math.max(task.progress || 0, 0), 100);
        
        // Animate progress change with a slight delay for visual feedback
        setTimeout(() => {
            progressBar.style.width = `${progress}%`;
            progressBar.setAttribute('aria-valuenow', progress);
            
            // For progress text, use different text based on status
            if (task.status === 'completed') {
                progressBar.textContent = 'Complete';
            } else if (task.status === 'failed') {
                progressBar.textContent = 'Failed';
            } else {
                progressBar.textContent = `${progress}%`;
            }
            
            // Update the previous progress value
            progressBar.dataset.prevProgress = progress;
        }, 50);
        
        // For failed tasks, change progress bar class
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
        
        // For completed tasks, add completion animation
        if (task.status === 'completed') {
            progressBar.classList.remove('progress-bar-striped', 'progress-bar-animated');
            // Add smooth completion animation
            progressBar.classList.add('progress-complete-animation');
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
    
    updateTaskElement(taskElement, task) {
        // Only update if the element exists
        if (!taskElement) return;
        
        // Update status class
        const previousStatus = taskElement.dataset.status;
        const newStatus = task.status;
        
        // Update status data attribute
        taskElement.dataset.status = newStatus;
        
        // Get the status badge and update it
        const statusBadge = taskElement.querySelector('.status-badge');
        if (statusBadge) {
            // Reset classes
            statusBadge.className = 'badge rounded-pill status-badge';
            
            // Add new status class and text
            switch (newStatus) {
                case 'pending':
                    statusBadge.textContent = 'Pending';
                    statusBadge.classList.add('bg-warning');
                    break;
                case 'running':
                    statusBadge.textContent = 'Processing';
                    statusBadge.classList.add('bg-warning');
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
        }
        
        // Update progress bar with animation
        const progressBar = taskElement.querySelector('.progress-bar');
        if (progressBar) {
            // Get previous progress for animation
            const prevProgress = parseInt(progressBar.dataset.prevProgress || 0, 10);
            const newProgress = Math.min(Math.max(task.progress || 0, 0), 100);
            
            // Only animate if progress has changed
            if (prevProgress !== newProgress) {
                // Add transition class if progress has increased
                if (newProgress > prevProgress) {
                    progressBar.classList.add('progress-increasing');
                }
                
                // Update progress with a slight delay for visual feedback
                setTimeout(() => {
                    progressBar.style.width = `${newProgress}%`;
                    progressBar.setAttribute('aria-valuenow', newProgress);
                    
                    // Update text based on status
                    if (newStatus === 'completed') {
                        progressBar.textContent = 'Complete';
                    } else if (newStatus === 'failed') {
                        progressBar.textContent = 'Failed';
                    } else {
                        progressBar.textContent = `${newProgress}%`;
                    }
                    
                    // Store the new progress
                    progressBar.dataset.prevProgress = newProgress;
                    
                    // Remove transition class after animation
                    setTimeout(() => {
                        progressBar.classList.remove('progress-increasing');
                    }, 600);
                }, 50);
            }
            
            // Handle status changes for the progress bar
            if (previousStatus !== newStatus) {
                // Reset classes
                progressBar.classList.remove('bg-danger', 'progress-bar-striped', 'progress-bar-animated', 'progress-complete-animation');
                
                // Apply appropriate classes for new status
                if (newStatus === 'pending' || newStatus === 'running') {
                    progressBar.classList.add('progress-bar-striped', 'progress-bar-animated');
                } else if (newStatus === 'completed') {
                    progressBar.classList.add('progress-complete-animation');
                } else if (newStatus === 'failed') {
                    progressBar.classList.add('bg-danger');
                }
            }
        }
        
        // Update stats (cards saved, timestamp)
        const statsElement = taskElement.querySelector('.import-stats');
        if (statsElement) {
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
        }
        
        // Show/hide view deck button
        const viewDeckBtn = taskElement.querySelector('.view-deck-btn');
        if (viewDeckBtn) {
            if (newStatus === 'completed') {
                viewDeckBtn.classList.remove('d-none');
                
                // Ensure event listener is set
                viewDeckBtn.onclick = null; // Remove any existing handler
                viewDeckBtn.addEventListener('click', () => {
                    window.location.href = `/deck/${task.deck_id}`;
                });
            } else {
                viewDeckBtn.classList.add('d-none');
            }
        }
        
        // Handle error messages
        const existingError = taskElement.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }
        
        if (newStatus === 'failed' && task.error) {
            const errorElement = document.createElement('div');
            errorElement.className = 'error-message small text-danger mt-1';
            errorElement.innerHTML = `<i class="bi bi-exclamation-circle me-1"></i>${task.error}`;
            
            const stats = taskElement.querySelector('.import-stats');
            if (stats) {
                stats.parentNode.insertBefore(errorElement, stats.nextSibling);
            }
        }
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
