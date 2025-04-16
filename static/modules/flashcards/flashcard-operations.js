/**
 * Handles flashcard CRUD operations
 */
export function initializeFlashcardOperations() {
    // Initialize modals
    const addFlashcardModal = new bootstrap.Modal(document.getElementById('addFlashcardModal'));
    const editFlashcardModal = new bootstrap.Modal(document.getElementById('editFlashcardModal'));
    const deleteFlashcardModal = new bootstrap.Modal(document.getElementById('deleteFlashcardModal'));
    
    // Event listener for "Add Flashcard" button
    document.querySelectorAll('#addManualFlashcardBtn').forEach(btn => {
        btn.addEventListener('click', () => {
            const deckId = btn.dataset.deckId;
            document.getElementById('addFlashcardDeckId').value = deckId;
            document.getElementById('addFlashcardForm').reset();
            document.getElementById('addFlashcardStatus').innerHTML = '';
            addFlashcardModal.show();
        });
    });
    
    // Event listener for "Save Flashcard" button
    document.getElementById('saveFlashcardBtn').addEventListener('click', async () => {
        await saveFlashcard();
    });
    
    // Event listeners for "Edit Flashcard" buttons
    document.querySelectorAll('.edit-flashcard-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const flashcardId = btn.dataset.flashcardId;
            const question = btn.dataset.question;
            const correctAnswer = btn.dataset.correctAnswer;
            let incorrectAnswers = [];
            
            try {
                // Improved JSON parsing with better error handling
                if (btn.dataset.incorrectAnswers) {
                    // First replace HTML entities if they exist
                    const decodedJson = btn.dataset.incorrectAnswers
                        .replace(/&quot;/g, '"')
                        .replace(/&#39;/g, "'")
                        .replace(/&lt;/g, '<')
                        .replace(/&gt;/g, '>');
                    
                    try {
                        // Try to parse the cleaned JSON
                        incorrectAnswers = JSON.parse(decodedJson);
                    } catch (jsonError) {
                        console.error("Error parsing decoded JSON:", jsonError);
                        console.log("Decoded data:", decodedJson);
                        
                        // Fallback to string handling
                        incorrectAnswers = decodedJson.split(',').map(s => s.trim()).filter(s => s);
                    }
                }
            } catch (e) {
                console.error("Error handling incorrect answers:", e);
                incorrectAnswers = []; // Default to empty array on error
            }
            
            // Ensure incorrectAnswers is an array
            if (!Array.isArray(incorrectAnswers)) {
                incorrectAnswers = [incorrectAnswers].filter(Boolean);
            }
            
            console.log("Editing flashcard:", {
                id: flashcardId,
                question: question,
                correctAnswer: correctAnswer,
                incorrectAnswers: incorrectAnswers
            });
            
            // Populate form fields
            document.getElementById('editFlashcardId').value = flashcardId;
            document.getElementById('editFlashcardQuestion').value = question || '';
            document.getElementById('editFlashcardCorrectAnswer').value = correctAnswer || '';
            
            // Populate incorrect answers
            const container = document.getElementById('editIncorrectAnswersContainer');
            container.innerHTML = '';
            
            // Add each incorrect answer field
            incorrectAnswers.forEach((answer, index) => {
                container.innerHTML += `
                    <div class="mb-2">
                        <textarea class="form-control incorrect-answer mb-2" name="incorrect_answers[]" rows="2">${answer || ''}</textarea>
                    </div>
                `;
            });
            
            // Make sure we have at least 3 fields
            while (container.children.length < 3) {
                container.innerHTML += `
                    <div class="mb-2">
                        <textarea class="form-control incorrect-answer mb-2" name="incorrect_answers[]" rows="2"></textarea>
                    </div>
                `;
            }
            
            document.getElementById('editFlashcardStatus').innerHTML = '';
            editFlashcardModal.show();
        });
    });
    
    // Event listener for "Update Flashcard" button
    document.getElementById('updateFlashcardBtn').addEventListener('click', async () => {
        await updateFlashcard();
    });
    
    // Event listeners for "Delete Flashcard" buttons
    document.querySelectorAll('.delete-flashcard-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const flashcardId = btn.dataset.flashcardId;
            const question = btn.dataset.question;
            
            document.getElementById('deleteFlashcardId').value = flashcardId;
            document.getElementById('deleteFlashcardQuestion').textContent = question;
            document.getElementById('deleteFlashcardStatus').innerHTML = '';
            
            deleteFlashcardModal.show();
        });
    });
    
    // Event listener for "Confirm Delete Flashcard" button
    document.getElementById('confirmDeleteFlashcardBtn').addEventListener('click', async () => {
        await deleteFlashcard();
    });
}

async function saveFlashcard() {
    const form = document.getElementById('addFlashcardForm');
    const statusDiv = document.getElementById('addFlashcardStatus');
    const button = document.getElementById('saveFlashcardBtn');
    const normalState = button.querySelector('.normal-state');
    const loadingState = button.querySelector('.loading-state');
    
    // Basic validation
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    // Show loading state
    button.disabled = true;
    normalState.classList.add('d-none');
    loadingState.classList.remove('d-none');
    
    // Collect form data
    const deckId = document.getElementById('addFlashcardDeckId').value;
    const question = document.getElementById('flashcardQuestion').value;
    const correctAnswer = document.getElementById('flashcardCorrectAnswer').value;
    const incorrectAnswers = Array.from(form.querySelectorAll('textarea[name="incorrect_answers[]"]'))
        .map(ta => ta.value);
    
    try {
        // Send API request
        const response = await fetch('/flashcard/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                deck_id: deckId,
                question: question,
                correct_answer: correctAnswer,
                incorrect_answers: incorrectAnswers
            }),
        });
        
        const result = await response.json();
        
        if (response.ok) {
            statusDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle me-2"></i> Flashcard created successfully!
                </div>
            `;
            
            // Reload the page after a short delay
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            throw new Error(result.error || 'Failed to create flashcard');
        }
    } catch (error) {
        statusDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle me-2"></i> ${error.message}
            </div>
        `;
    } finally {
        // Restore button state
        button.disabled = false;
        normalState.classList.remove('d-none');
        loadingState.classList.add('d-none');
    }
}

async function updateFlashcard() {
    const form = document.getElementById('editFlashcardForm');
    const statusDiv = document.getElementById('editFlashcardStatus');
    const button = document.getElementById('updateFlashcardBtn');
    const normalState = button.querySelector('.normal-state');
    const loadingState = button.querySelector('.loading-state');
    
    // Basic validation
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    // Show loading state
    button.disabled = true;
    normalState.classList.add('d-none');
    loadingState.classList.remove('d-none');
    
    // Collect form data
    const flashcardId = document.getElementById('editFlashcardId').value;
    const question = document.getElementById('editFlashcardQuestion').value;
    const correctAnswer = document.getElementById('editFlashcardCorrectAnswer').value;
    const incorrectAnswers = Array.from(form.querySelectorAll('textarea[name="incorrect_answers[]"]'))
        .map(ta => ta.value);
    
    try {
        // Send API request
        const response = await fetch(`/flashcard/update/${flashcardId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: question,
                correct_answer: correctAnswer,
                incorrect_answers: incorrectAnswers
            }),
        });
        
        const result = await response.json();
        
        if (response.ok) {
            statusDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle me-2"></i> Flashcard updated successfully!
                </div>
            `;
            
            // Reload the page after a short delay
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            throw new Error(result.error || 'Failed to update flashcard');
        }
    } catch (error) {
        statusDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle me-2"></i> ${error.message}
            </div>
        `;
    } finally {
        // Restore button state
        button.disabled = false;
        normalState.classList.remove('d-none');
        loadingState.classList.add('d-none');
    }
}

async function deleteFlashcard() {
    const flashcardId = document.getElementById('deleteFlashcardId').value;
    const statusDiv = document.getElementById('deleteFlashcardStatus');
    const button = document.getElementById('confirmDeleteFlashcardBtn');
    const normalState = button.querySelector('.normal-state');
    const loadingState = button.querySelector('.loading-state');
    
    // Show loading state
    button.disabled = true;
    normalState.classList.add('d-none');
    loadingState.classList.remove('d-none');
    
    try {
        // Send API request
        const response = await fetch(`/flashcard/delete/${flashcardId}`, {
            method: 'DELETE',
        });
        
        const result = await response.json();
        
        if (response.ok) {
            statusDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle me-2"></i> Flashcard deleted successfully!
                </div>
            `;
            
            // Reload the page after a short delay
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            throw new Error(result.error || 'Failed to delete flashcard');
        }
    } catch (error) {
        statusDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle me-2"></i> ${error.message}
            </div>
        `;
        
        // Restore button state
        button.disabled = false;
        normalState.classList.remove('d-none');
        loadingState.classList.add('d-none');
    }
}
