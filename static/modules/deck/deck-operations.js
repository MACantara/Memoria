import { renameDeck } from '../utils.js';

export function initializeDeckOperations() {
    let deckToDelete = null;
    const deleteModal = new bootstrap.Modal(document.getElementById('deleteDeckModal'));
    
    window.deleteDeck = async (deckId) => {
        deckToDelete = deckId;
        deleteModal.show();
    };
    
    window.showRenameDeckModal = (deckId, currentName, currentDescription) => {
        const modal = new bootstrap.Modal(document.getElementById('renameDeckModal'));
        document.getElementById('deckId').value = deckId;
        document.getElementById('newDeckName').value = currentName;
        document.getElementById('newDeckDescription').value = currentDescription;
        document.getElementById('renameStatus').innerHTML = '';
        modal.show();
    };

    document.getElementById('renameDeckForm').addEventListener('submit', handleRenameSubmit);
    document.getElementById('confirmDeleteBtn').addEventListener('click', () => handleDelete(deckToDelete));
}

async function handleRenameSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const submitButton = form.querySelector('button[type="submit"]');
    const normalState = submitButton.querySelector('.normal-state');
    const loadingState = submitButton.querySelector('.loading-state');
    const statusDiv = document.getElementById('renameStatus');

    submitButton.disabled = true;
    normalState.classList.add('d-none');
    loadingState.classList.remove('d-none');

    try {
        const deckId = document.getElementById('deckId').value;
        const newName = document.getElementById('newDeckName').value;
        const newDescription = document.getElementById('newDeckDescription').value;
        const result = await renameDeck(deckId, newName, newDescription);
        
        if (result.success) {
            statusDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i> Deck renamed successfully!
                </div>
            `;
            setTimeout(() => location.reload(), 1000);
        } else {
            throw new Error(result.error || 'Failed to rename deck');
        }
    } catch (error) {
        statusDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i> ${error.message}
            </div>
        `;
        submitButton.disabled = false;
        normalState.classList.remove('d-none');
        loadingState.classList.add('d-none');
    }
}

async function handleDelete(deckToDelete) {
    const button = document.getElementById('confirmDeleteBtn');
    const normalState = button.querySelector('.normal-state');
    const loadingState = button.querySelector('.loading-state');
    const statusDiv = document.getElementById('deleteStatus');
    
    button.disabled = true;
    normalState.classList.add('d-none');
    loadingState.classList.remove('d-none');
    
    try {
        const response = await fetch(`/deck/delete/${deckToDelete}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            statusDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i> Sub-deck deleted successfully!
                </div>
            `;
            setTimeout(() => location.reload(), 1000);
        } else {
            throw new Error('Failed to delete sub-deck');
        }
    } catch (error) {
        statusDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i> ${error.message}
            </div>
        `;
        button.disabled = false;
        normalState.classList.remove('d-none');
        loadingState.classList.add('d-none');
    }
}
