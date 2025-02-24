export function initializeModals() {
    const deckModal = new bootstrap.Modal(document.getElementById('deckModal'), {
        backdrop: true,
        keyboard: true
    });
    
    const generateModal = new bootstrap.Modal(document.getElementById('generateModal'), {
        backdrop: true,
        keyboard: true
    });
    
    const noCardsModal = new bootstrap.Modal(document.getElementById('noCardsModal'));
    let currentDeckId = null;

    // Button click handlers
    document.getElementById('createDeckBtn').onclick = () => {
        document.getElementById('createDeckForm').reset();
        deckModal.show();
    };
    
    document.querySelectorAll('.add-cards-btn').forEach(button => {
        button.addEventListener('click', () => {
            document.getElementById('generateForm').reset();
            document.getElementById('generateDeckId').value = button.dataset.deckId;
            generateModal.show();
        });
    });

    document.querySelectorAll('.no-cards').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            currentDeckId = link.dataset.deckId;
            noCardsModal.show();
        });
    });
    
    document.getElementById('generateFromNoCards').addEventListener('click', () => {
        noCardsModal.hide();
        document.getElementById('generateDeckId').value = currentDeckId;
        generateModal.show();
    });

    return { deckModal, generateModal };
}
