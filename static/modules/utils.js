export function shuffleArray(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
    return array;
}

export async function updateProgress(flashcardId, isCorrect) {
    try {
        // Updated URL to match new blueprint structure
        const response = await fetch('/flashcard/update_progress', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                flashcard_id: flashcardId,
                is_correct: isCorrect
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to update progress');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error updating progress:', error);
        throw error;
    }
}

/**
 * Delete a deck with the given ID
 * @param {number} deckId - The ID of the deck to delete
 * @returns {Promise<Object>} - Promise resolving to the server response
 */
export async function deleteDeck(deckId) {
    try {
        const response = await fetch(`/deck/delete/${deckId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Failed with status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error deleting deck:', error);
        throw error;
    }
}

export async function renameDeck(deckId, newName, newDescription) {
    try {
        const response = await fetch(`/deck/rename/${deckId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                name: newName,
                description: newDescription
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to rename deck');
        }
        
        return { success: true, message: data.message };
    } catch (error) {
        console.error('Error renaming deck:', error);
        return { success: false, error: error.message };
    }
}
