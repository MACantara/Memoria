export function shuffleArray(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
    return array;
}

export async function updateProgress(flashcardId, isCorrect) {
    await fetch('/update_progress', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            flashcard_id: flashcardId,
            is_correct: isCorrect
        })
    });
}

export async function deleteTopic(topicId) {
    if (!confirm('Are you sure you want to delete this topic?')) return;
    try {
        const response = await fetch(`/topic/delete/${topicId}`, {
            method: 'DELETE'
        });
        if (response.ok) {
            location.reload();
        } else {
            throw new Error('Failed to delete topic');
        }
    } catch (error) {
        console.error('Error deleting topic:', error);
        alert('Failed to delete topic. Please try again.');
    }
}

export async function deleteDeck(deckId) {
    if (!confirm('Are you sure you want to delete this deck?')) return;
    try {
        const response = await fetch(`/deck/delete/${deckId}`, {
            method: 'DELETE'
        });
        if (response.ok) {
            location.reload();
        } else {
            throw new Error('Failed to delete deck');
        }
    } catch (error) {
        console.error('Error deleting deck:', error);
        alert('Failed to delete deck. Please try again.');
    }
}

export async function renameTopic(topicId, newName) {
    try {
        const response = await fetch(`/topic/rename/${topicId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name: newName })
        });
        if (response.ok) {
            location.reload();
        } else {
            throw new Error('Failed to rename topic');
        }
    } catch (error) {
        console.error('Error renaming topic:', error);
        alert('Failed to rename topic. Please try again.');
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
        if (response.ok) {
            location.reload();
        } else {
            throw new Error('Failed to rename deck');
        }
    } catch (error) {
        console.error('Error renaming deck:', error);
        alert('Failed to rename deck. Please try again.');
    }
}
