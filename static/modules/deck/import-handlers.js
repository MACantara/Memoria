export function initializeImportModal() {
    // Initialize drag and drop for file upload
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('fileInput');
    const importModal = new bootstrap.Modal(document.getElementById('importContentModal'));
    
    // Set up window functions for modal
    window.showImportModal = () => {
        // Clear previous results and form inputs
        document.getElementById('uploadResult').innerHTML = '';
        document.getElementById('textResult').innerHTML = '';
        document.getElementById('fileUploadForm').reset();
        document.getElementById('textForm').reset();
        
        // Remove any file info message
        const existingInfo = dropArea?.querySelector('p:not(:first-child)');
        if (existingInfo) {
            existingInfo.remove();
        }
        
        // Load parent decks for both forms
        loadParentDecks();
        
        // Show the modal
        importModal.show();
        
        // Activate first tab
        const firstTab = document.querySelector('#importTabs .nav-link');
        if (firstTab) {
            const tabTrigger = new bootstrap.Tab(firstTab);
            tabTrigger.show();
        }
    };
    
    // Skip if we're not on a page with the import modal
    if (!dropArea || !fileInput) {
        return;
    }
    
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
        dropArea.classList.add('active');
    }
    
    function unhighlight() {
        dropArea.classList.remove('active');
    }
    
    dropArea.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            fileInput.files = files;
            // Display filename
            const file = files[0];
            const fileInfo = document.createElement('p');
            fileInfo.textContent = `Selected file: ${file.name} (${formatFileSize(file.size)})`;
            
            // Remove any existing file info
            const existingInfo = dropArea.querySelector('p:not(:first-child)');
            if (existingInfo) {
                existingInfo.remove();
            }
            
            dropArea.appendChild(fileInfo);
        }
    }
    
    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' bytes';
        else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        else return (bytes / 1048576).toFixed(1) + ' MB';
    }
    
    // File upload form submission
    const fileUploadForm = document.getElementById('fileUploadForm');
    const uploadBtn = document.getElementById('uploadBtn');
    const uploadResult = document.getElementById('uploadResult');
    
    fileUploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Get button states
        const normalState = uploadBtn.querySelector('.normal-state');
        const loadingState = uploadBtn.querySelector('.loading-state');
        
        uploadBtn.disabled = true;
        loadingState.classList.remove('d-none');
        normalState.classList.add('d-none');
        uploadResult.innerHTML = '';
        
        const formData = new FormData(fileUploadForm);
        
        try {
            const response = await fetch(fileUploadForm.action, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                uploadResult.innerHTML = `
                    <div class="alert alert-success">
                        <i class="bi bi-check-circle-fill me-2"></i>
                        ${data.message}
                    </div>
                `;
                
                // Redirect after a short delay
                if (data.redirect_url) {
                    setTimeout(() => {
                        window.location.href = data.redirect_url;
                    }, 1500);
                }
            } else {
                throw new Error(data.error || 'An error occurred during processing');
            }
        } catch (error) {
            uploadResult.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    ${error.message}
                </div>
            `;
            uploadBtn.disabled = false;
            loadingState.classList.add('d-none');
            normalState.classList.remove('d-none');
        }
    });
    
    // Text processing form submission
    const textForm = document.getElementById('textForm');
    const textBtn = document.getElementById('textBtn');
    const textResult = document.getElementById('textResult');
    
    textForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Get button states
        const normalState = textBtn.querySelector('.normal-state');
        const loadingState = textBtn.querySelector('.loading-state');
        
        textBtn.disabled = true;
        loadingState.classList.remove('d-none');
        normalState.classList.add('d-none');
        textResult.innerHTML = '';
        
        const textData = {
            deck_name: document.getElementById('textDeckName').value,
            parent_deck_id: document.getElementById('textParentDeckId').value || null,
            text: document.getElementById('textContent').value
        };
        
        try {
            const response = await fetch('/import/process-text', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(textData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                textResult.innerHTML = `
                    <div class="alert alert-success">
                        <i class="bi bi-check-circle-fill me-2"></i>
                        ${data.message}
                    </div>
                `;
                
                // Redirect after a short delay
                if (data.redirect_url) {
                    setTimeout(() => {
                        window.location.href = data.redirect_url;
                    }, 1500);
                }
            } else {
                throw new Error(data.error || 'An error occurred during processing');
            }
        } catch (error) {
            textResult.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    ${error.message}
                </div>
            `;
            textBtn.disabled = false;
            loadingState.classList.add('d-none');
            normalState.classList.remove('d-none');
        }
    });
}

async function loadParentDecks() {
    try {
        const response = await fetch('/deck/api/decks');
        const decks = await response.json();
        
        const parentDeckId = document.getElementById('parentDeckId');
        const textParentDeckId = document.getElementById('textParentDeckId');
        
        if (!parentDeckId || !textParentDeckId) return;
        
        // Clear existing options except first one
        while (parentDeckId.options.length > 1) {
            parentDeckId.remove(1);
        }
        
        while (textParentDeckId.options.length > 1) {
            textParentDeckId.remove(1);
        }
        
        // Helper function to populate select element
        function populateSelect(selectElement, decks, level = 0) {
            decks.forEach(deck => {
                const option = document.createElement('option');
                option.value = deck.id;
                option.textContent = '—'.repeat(level) + ' ' + deck.name;
                selectElement.appendChild(option);
                
                if (deck.children && deck.children.length > 0) {
                    populateSelect(selectElement, deck.children, level + 1);
                }
            });
        }
        
        // Populate both select elements
        populateSelect(parentDeckId, decks);
        populateSelect(textParentDeckId, decks);
        
    } catch (error) {
        console.error('Error loading parent decks:', error);
    }
}
