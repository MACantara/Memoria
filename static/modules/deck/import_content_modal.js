document.addEventListener('DOMContentLoaded', function() {
    // Cache DOM elements
    const fileUploadForm = document.getElementById('fileUploadForm');
    const textForm = document.getElementById('textForm');
    const uploadBtn = document.getElementById('uploadBtn');
    const textBtn = document.getElementById('textBtn');
    const uploadResult = document.getElementById('uploadResult');
    const textResult = document.getElementById('textResult');
    const fileInput = document.getElementById('fileInput');
    const dropArea = document.getElementById('drop-area');
    const importContentModal = document.getElementById('importContentModal');
    
    // Load decks for parent deck dropdowns
    loadDecks();
    
    // Set up drag and drop functionality
    setupDragAndDrop();
    
    // Handle file upload form submission
    fileUploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        uploadResult.innerHTML = '';
        
        // Show loading state
        toggleLoadingState(uploadBtn, true);
        
        const formData = new FormData(fileUploadForm);
        
        // First, upload the file
        fetch(fileUploadForm.action, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) throw new Error('Upload failed');
            return response.json();
        })
        .then(data => {
            if (!data.success) throw new Error(data.error || 'Unknown error');
            
            const fileKey = data.file_key;
            const deckId = data.deck_id;
            
            // Show processing status
            uploadResult.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i>
                    <p>Processing file...</p>
                    <p><strong>${data.total_chunks}</strong> chunks to process</p>
                    <div class="progress mt-2">
                        <div class="progress-bar" role="progressbar" style="width: 0%;" 
                             aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">0%</div>
                    </div>
                </div>
            `;
            
            // Start processing chunks
            return processChunks(fileKey, deckId);
        })
        .catch(error => {
            console.error('Error:', error);
            uploadResult.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i>
                    Error: ${error.message}
                </div>
            `;
            toggleLoadingState(uploadBtn, false);
        });
    });
    
    // Handle text form submission
    textForm.addEventListener('submit', function(e) {
        e.preventDefault();
        textResult.innerHTML = '';
        
        // Show loading state
        toggleLoadingState(textBtn, true);
        
        const data = {
            text: document.getElementById('textContent').value,
            deck_name: document.getElementById('textDeckName').value,
            parent_deck_id: document.getElementById('textParentDeckId').value
        };
        
        fetch('/import/process-text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) throw new Error('Text processing failed');
            return response.json();
        })
        .then(data => {
            if (!data.success) throw new Error(data.error || 'Unknown error');
            
            const fileKey = data.file_key;
            const deckId = data.deck_id;
            
            // Show processing status
            textResult.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i>
                    <p>Processing text...</p>
                    <p><strong>${data.total_chunks}</strong> chunks to process</p>
                    <div class="progress mt-2">
                        <div class="progress-bar" role="progressbar" style="width: 0%;" 
                             aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">0%</div>
                    </div>
                </div>
            `;
            
            // Start processing chunks
            return processChunks(fileKey, deckId, 'text');
        })
        .catch(error => {
            console.error('Error:', error);
            textResult.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i>
                    Error: ${error.message}
                </div>
            `;
            toggleLoadingState(textBtn, false);
        });
    });

    // Process chunks recursively
    function processChunks(fileKey, deckId, type = 'file') {
        const resultElement = type === 'text' ? textResult : uploadResult;
        const buttonElement = type === 'text' ? textBtn : uploadBtn;
        
        return fetch('/import/process-chunk', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ file_key: fileKey })
        })
        .then(response => {
            if (!response.ok) throw new Error('Processing failed');
            return response.json();
        })
        .then(data => {
            if (!data.success) throw new Error(data.error || 'Unknown error');
            
            // Update progress display
            const progress = Math.round(data.processed_chunks / data.total_chunks * 100);
            resultElement.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i>
                    <p>Processing... (${data.processed_chunks}/${data.total_chunks} chunks)</p>
                    <p>Generated ${data.cards_added} flashcards in this chunk</p>
                    <div class="progress mt-2">
                        <div class="progress-bar" role="progressbar" style="width: ${progress}%;" 
                             aria-valuenow="${progress}" aria-valuemin="0" aria-valuemax="100">${progress}%</div>
                    </div>
                </div>
            `;
            
            // Check if processing is complete
            if (data.is_complete) {
                // Show completion message and redirect
                resultElement.innerHTML = `
                    <div class="alert alert-success">
                        <i class="bi bi-check-circle"></i>
                        Processing complete! Redirecting to your flashcards...
                    </div>
                `;
                
                // Redirect after a short delay
                setTimeout(() => {
                    window.location.href = `/deck/${data.deck_id}/flashcards`;
                }, 1500);
                
                return;
            }
            
            // Continue processing next chunk
            return processChunks(fileKey, deckId, type);
        })
        .catch(error => {
            console.error('Error:', error);
            resultElement.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i>
                    Error: ${error.message}
                </div>
            `;
            toggleLoadingState(buttonElement, false);
        });
    }
    
    // Load deck options for parent deck selects
    function loadDecks() {
        fetch('/deck/all')
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    console.error("Failed to load decks");
                    return;
                }
                
                const decks = data.decks;
                populateDeckDropdown('parentDeckId', decks);
                populateDeckDropdown('textParentDeckId', decks);
                
                // Hide loading spinners
                document.querySelectorAll('.loading-spinner').forEach(spinner => {
                    spinner.style.display = 'none';
                });
            })
            .catch(error => {
                console.error("Error loading decks:", error);
                document.querySelectorAll('.loading-spinner').forEach(spinner => {
                    spinner.style.display = 'none';
                });
            });
    }
    
    // Populate a dropdown with deck options
    function populateDeckDropdown(elementId, decks) {
        const dropdown = document.getElementById(elementId);
        dropdown.innerHTML = '<option value="">No parent deck (top level)</option>';
        
        // Add deck options with proper indentation to show hierarchy
        function addDecksToDropdown(deckList, level = 0) {
            deckList.forEach(deck => {
                const indent = '—'.repeat(level);
                const prefix = level > 0 ? indent + ' ' : '';
                
                dropdown.innerHTML += `<option value="${deck.id}">${prefix}${deck.name}</option>`;
                
                if (deck.children && deck.children.length > 0) {
                    addDecksToDropdown(deck.children, level + 1);
                }
            });
        }
        
        addDecksToDropdown(decks);
    }
    
    // Set up drag and drop functionality
    function setupDragAndDrop() {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight() {
            dropArea.classList.add('highlight');
        }
        
        function unhighlight() {
            dropArea.classList.remove('highlight');
        }
        
        dropArea.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files.length) {
                fileInput.files = files;
                // Update file input label to show selected file
                const fileName = files[0].name;
                dropArea.querySelector('p').textContent = `Selected file: ${fileName}`;
            }
        }
    }
    
    // Toggle loading state of a button
    function toggleLoadingState(button, isLoading) {
        const normalState = button.querySelector('.normal-state');
        const loadingState = button.querySelector('.loading-state');
        
        if (isLoading) {
            normalState.classList.add('d-none');
            loadingState.classList.remove('d-none');
            button.disabled = true;
        } else {
            normalState.classList.remove('d-none');
            loadingState.classList.add('d-none');
            button.disabled = false;
        }
    }
    
    // Reset forms when modal is hidden
    importContentModal.addEventListener('hidden.bs.modal', function() {
        fileUploadForm.reset();
        textForm.reset();
        uploadResult.innerHTML = '';
        textResult.innerHTML = '';
        toggleLoadingState(uploadBtn, false);
        toggleLoadingState(textBtn, false);
        dropArea.querySelector('p').textContent = 'Drag & Drop your text file here or';
    });
});
