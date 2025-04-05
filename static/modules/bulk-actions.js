/**
 * Bulk action functionality for Memoria
 * Allows selecting multiple decks or flashcards and performing bulk operations
 */

// Import the bulk move modal handlers
import { showBulkMoveFlashcardModal, showBulkMoveDeckModal } from "./bulk/bulk-move-handler.js";

class BulkActionManager {
    constructor(options = {}) {
        // Set default options
        this.options = Object.assign({
            container: document, // Container to initialize within
            itemSelector: '.selectable-item', // Selector for items that can be selected
            checkboxSelector: '.item-checkbox', // Selector for checkboxes within items
            bulkActionsBar: null, // Element containing bulk action buttons
            selectAllCheckbox: null, // Checkbox for selecting all items
            selectedClass: 'selected', // Class added to selected items
            onSelectionChange: null, // Callback when selection changes
            countElement: null, // Element to show selected count
            entityType: 'item', // Type of entity ('deck' or 'flashcard')
            selectionKey: 'bulk-selection', // LocalStorage key prefix for selection
        }, options);

        // Initialize state
        this.selectedItems = new Set();
        this.allCheckboxes = [];
        this.isSelectMode = false;
        
        // Find elements
        this.container = typeof this.options.container === 'string' 
            ? document.querySelector(this.options.container) 
            : this.options.container;
            
        this.bulkActionsBar = this.options.bulkActionsBar instanceof HTMLElement 
            ? this.options.bulkActionsBar 
            : document.querySelector(this.options.bulkActionsBar);
            
        this.selectAllCheckbox = this.options.selectAllCheckbox instanceof HTMLElement 
            ? this.options.selectAllCheckbox 
            : document.querySelector(this.options.selectAllCheckbox);
            
        this.countElement = this.options.countElement instanceof HTMLElement 
            ? this.options.countElement 
            : document.querySelector(this.options.countElement);
            
        // If we have a valid container, initialize
        if (this.container) {
            this.init();
        }
    }
    
    /**
     * Initialize the bulk action manager
     */
    init() {
        // Find all checkboxes
        this.refreshItems();
        
        // Bind events
        this.bindEvents();
        
        // Restore selection state if needed
        this.restoreSelectionState();
        
        console.log(`Bulk action manager initialized with ${this.allCheckboxes.length} ${this.options.entityType}s`);
    }
    
    /**
     * Refresh the items list (useful after DOM changes)
     */
    refreshItems() {
        this.allCheckboxes = Array.from(
            this.container.querySelectorAll(this.options.checkboxSelector)
        );
    }
    
    /**
     * Bind event listeners
     */
    bindEvents() {
        // Listen for checkbox changes
        this.container.addEventListener('change', (event) => {
            const checkbox = event.target.closest(this.options.checkboxSelector);
            if (checkbox) {
                const item = checkbox.closest(this.options.itemSelector);
                if (item) {
                    this.toggleItemSelection(item, checkbox.checked);
                }
            }
        });
        
        // Handle select all checkbox
        if (this.selectAllCheckbox) {
            this.selectAllCheckbox.addEventListener('change', () => {
                this.toggleSelectAll(this.selectAllCheckbox.checked);
            });
        }
        
        // Handle bulk action buttons if we have a bulk actions bar
        if (this.bulkActionsBar) {
            // Delete action
            const deleteBtn = this.bulkActionsBar.querySelector('.bulk-action-delete');
            if (deleteBtn) {
                deleteBtn.addEventListener('click', () => this.performBulkDelete());
            }
            
            // Move action
            const moveBtn = this.bulkActionsBar.querySelector('.bulk-action-move');
            if (moveBtn) {
                moveBtn.addEventListener('click', () => this.showMoveDialog());
            }
            
            // Cancel selection
            const cancelBtn = this.bulkActionsBar.querySelector('.bulk-action-cancel');
            if (cancelBtn) {
                cancelBtn.addEventListener('click', () => this.cancelSelection());
            }
        }
    }
    
    /**
     * Toggle selection for a single item
     */
    toggleItemSelection(item, isSelected) {
        const id = item.dataset.id || item.dataset.deckId || item.dataset.flashcardId;
        
        if (!id) {
            console.error('Item has no ID', item);
            return;
        }
        
        if (isSelected) {
            this.selectedItems.add(id);
            item.classList.add(this.options.selectedClass);
        } else {
            this.selectedItems.delete(id);
            item.classList.remove(this.options.selectedClass);
        }
        
        // Update UI
        this.updateSelectionUI();
        
        // Save selection state
        this.saveSelectionState();
        
        // Call callback if provided
        if (typeof this.options.onSelectionChange === 'function') {
            this.options.onSelectionChange(this.getSelectedIds());
        }
    }
    
    /**
     * Toggle select all items
     */
    toggleSelectAll(selectAll) {
        this.allCheckboxes.forEach(checkbox => {
            checkbox.checked = selectAll;
            const item = checkbox.closest(this.options.itemSelector);
            if (item) {
                this.toggleItemSelection(item, selectAll);
            }
        });
    }
    
    /**
     * Update UI based on current selection
     */
    updateSelectionUI() {
        const selectedCount = this.selectedItems.size;
        
        // Update select all checkbox state
        if (this.selectAllCheckbox) {
            this.selectAllCheckbox.checked = selectedCount > 0 && selectedCount === this.allCheckboxes.length;
            this.selectAllCheckbox.indeterminate = selectedCount > 0 && selectedCount < this.allCheckboxes.length;
        }
        
        // Show/hide bulk actions bar
        if (this.bulkActionsBar) {
            if (selectedCount > 0) {
                this.bulkActionsBar.classList.add('show');
                this.isSelectMode = true;
            } else {
                this.bulkActionsBar.classList.remove('show');
                this.isSelectMode = false;
            }
        }
        
        // Update count if we have a count element
        if (this.countElement) {
            this.countElement.textContent = selectedCount.toString();
        }
    }
    
    /**
     * Get array of selected item IDs
     */
    getSelectedIds() {
        return Array.from(this.selectedItems);
    }
    
    /**
     * Cancel selection mode
     */
    cancelSelection() {
        this.toggleSelectAll(false);
        this.selectedItems.clear();
        this.updateSelectionUI();
        this.saveSelectionState();
    }
    
    /**
     * Save selection state to localStorage
     */
    saveSelectionState() {
        try {
            localStorage.setItem(
                `${this.options.selectionKey}-${window.location.pathname}`,
                JSON.stringify(Array.from(this.selectedItems))
            );
        } catch (e) {
            console.warn('Could not save selection state', e);
        }
    }
    
    /**
     * Restore selection state from localStorage
     */
    restoreSelectionState() {
        try {
            const savedSelection = localStorage.getItem(`${this.options.selectionKey}-${window.location.pathname}`);
            if (savedSelection) {
                const ids = JSON.parse(savedSelection);
                
                // Reset selection
                this.selectedItems.clear();
                
                // Re-select items that exist
                ids.forEach(id => {
                    const item = this.container.querySelector(`${this.options.itemSelector}[data-id="${id}"], 
                                                            ${this.options.itemSelector}[data-deck-id="${id}"],
                                                            ${this.options.itemSelector}[data-flashcard-id="${id}"]`);
                    if (item) {
                        const checkbox = item.querySelector(this.options.checkboxSelector);
                        if (checkbox) {
                            checkbox.checked = true;
                            this.toggleItemSelection(item, true);
                        }
                    }
                });
            }
        } catch (e) {
            console.warn('Could not restore selection state', e);
        }
    }
    
    /**
     * Show confirmation dialog for bulk delete
     */
    performBulkDelete() {
        const ids = this.getSelectedIds();
        if (ids.length === 0) return;
        
        if (this.options.entityType === 'deck') {
            // Use custom modal for decks
            const modal = document.getElementById('bulkDeleteDecksModal');
            if (modal) {
                // Update the count in the modal
                const countElement = modal.querySelector('#bulkDeleteDecksCount');
                if (countElement) {
                    countElement.textContent = ids.length;
                }
                
                // Set up the confirm button handler
                const confirmBtn = modal.querySelector('#confirmBulkDeleteDecksBtn');
                if (confirmBtn) {
                    // Remove any existing listeners to prevent duplicates
                    const newBtn = confirmBtn.cloneNode(true);
                    confirmBtn.parentNode.replaceChild(newBtn, confirmBtn);
                    
                    newBtn.addEventListener('click', () => {
                        // Update button state
                        newBtn.disabled = true;
                        const normalState = newBtn.querySelector('.normal-state');
                        const loadingState = newBtn.querySelector('.loading-state');
                        
                        if (normalState) normalState.classList.add('d-none');
                        if (loadingState) loadingState.classList.remove('d-none');
                        
                        // Execute the deletion
                        this.executeBulkDelete(ids);
                    });
                }
                
                // Reset status
                const statusElement = modal.querySelector('#bulkDeleteDecksStatus');
                if (statusElement) {
                    statusElement.innerHTML = '';
                }
                
                // Show the modal
                const bsModal = new bootstrap.Modal(modal);
                bsModal.show();
            } else {
                // Fallback to confirm if modal not found
                const entityName = 'deck';
                const confirmMessage = `Are you sure you want to delete ${ids.length} ${entityName}${ids.length !== 1 ? 's' : ''}? This action cannot be undone.`;
                
                if (confirm(confirmMessage)) {
                    this.executeBulkDelete(ids);
                }
            }
        } else {
            // For flashcards, use the custom modal
            const modal = document.getElementById('bulkDeleteFlashcardsModal');
            if (modal) {
                // Update the count in the modal
                const countElement = modal.querySelector('#bulkDeleteFlashcardsCount');
                if (countElement) {
                    countElement.textContent = ids.length;
                }
                
                // Set up the confirm button handler
                const confirmBtn = modal.querySelector('#confirmBulkDeleteFlashcardsBtn');
                if (confirmBtn) {
                    // Remove any existing listeners to prevent duplicates
                    const newBtn = confirmBtn.cloneNode(true);
                    confirmBtn.parentNode.replaceChild(newBtn, confirmBtn);
                    
                    newBtn.addEventListener('click', () => {
                        // Update button state
                        newBtn.disabled = true;
                        const normalState = newBtn.querySelector('.normal-state');
                        const loadingState = newBtn.querySelector('.loading-state');
                        
                        if (normalState) normalState.classList.add('d-none');
                        if (loadingState) loadingState.classList.remove('d-none');
                        
                        // Execute the deletion
                        this.executeBulkDelete(ids);
                    });
                }
                
                // Reset status
                const statusElement = modal.querySelector('#bulkDeleteFlashcardsStatus');
                if (statusElement) {
                    statusElement.innerHTML = '';
                }
                
                // Show the modal
                const bsModal = new bootstrap.Modal(modal);
                bsModal.show();
            } else {
                // Fallback to confirm if modal not found
                const entityName = 'flashcard';
                const confirmMessage = `Are you sure you want to delete ${ids.length} ${entityName}${ids.length !== 1 ? 's' : ''}? This action cannot be undone.`;
                
                if (confirm(confirmMessage)) {
                    this.executeBulkDelete(ids);
                }
            }
        }
    }
    
    /**
     * Execute bulk delete operation
     */
    async executeBulkDelete(ids) {
        try {
            const apiEndpoint = this.options.entityType === 'deck' 
                ? '/deck/api/decks/bulk-delete'
                : '/deck/api/flashcards/bulk-delete';
                
            const response = await fetch(apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ ids }),
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Success handling
                this.showToast(`Successfully deleted ${ids.length} ${this.options.entityType}${ids.length !== 1 ? 's' : ''}`, 'success');
                
                // Remove deleted items from DOM or refresh page
                this.refreshAfterBulkAction();
            } else {
                // Error handling
                this.showToast(`Error: ${result.error || 'Failed to delete items'}`, 'danger');
            }
        } catch (error) {
            console.error('Bulk delete error:', error);
            this.showToast('An error occurred during the bulk delete operation', 'danger');
        }
    }
    
    /**
     * Show move dialog for selected items
     */
    showMoveDialog() {
        const ids = this.getSelectedIds();
        if (ids.length === 0) return;
        
        if (this.options.entityType === 'deck') {
            // Use the imported function directly
            showBulkMoveDeckModal(ids);
        } else {
            // Show move flashcard modal
            showBulkMoveFlashcardModal(ids);
        }
    }
    
    /**
     * Refresh page or update UI after bulk action
     */
    refreshAfterBulkAction() {
        // Clear selection
        this.cancelSelection();
        
        // Either remove deleted items or refresh the page
        window.location.reload();
    }
    
    /**
     * Show a toast notification
     */
    showToast(message, type = 'info') {
        // Check if we have Bootstrap toast function
        if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
            // Create toast container if it doesn't exist
            let toastContainer = document.querySelector('.toast-container');
            if (!toastContainer) {
                toastContainer = document.createElement('div');
                toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
                document.body.appendChild(toastContainer);
            }
            
            // Create toast element
            const toastElement = document.createElement('div');
            toastElement.className = `toast align-items-center text-white bg-${type} border-0`;
            toastElement.setAttribute('role', 'alert');
            toastElement.setAttribute('aria-live', 'assertive');
            toastElement.setAttribute('aria-atomic', 'true');
            
            // Create toast content
            toastElement.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            `;
            
            // Add to container
            toastContainer.appendChild(toastElement);
            
            // Initialize and show
            const toast = new bootstrap.Toast(toastElement);
            toast.show();
            
            // Remove after hidden
            toastElement.addEventListener('hidden.bs.toast', () => {
                toastElement.remove();
            });
        } else {
            // Fallback to alert if Bootstrap not available
            alert(message);
        }
    }
}

// Global bulk actions setup function
function initBulkActions(options) {
    return new BulkActionManager(options);
}

export { BulkActionManager, initBulkActions };
