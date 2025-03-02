export function initializeImportModal() {
    // Initialize drag and drop for file upload
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('fileInput');
    const importModal = document.getElementById('importContentModal');
    
    // Skip if we're not on a page with the import modal
    if (!importModal) {
        console.log("Import modal not found, skipping initialization");
        return;
    }
    
    const bsImportModal = new bootstrap.Modal(importModal);
    
    // Set up window functions for modal
    window.showImportModal = () => {
        console.log("Opening import modal");
        // Clear previous results and form inputs
        const uploadResult = document.getElementById('uploadResult');
        const textResult = document.getElementById('textResult');
        if (uploadResult) uploadResult.innerHTML = '';
        if (textResult) textResult.innerHTML = '';
        
        const fileUploadForm = document.getElementById('fileUploadForm');
        const textForm = document.getElementById('textForm');
        if (fileUploadForm) fileUploadForm.reset();
        if (textForm) textForm.reset();
        
        // Remove any file info message
        if (dropArea) {
            const existingInfo = dropArea.querySelector('p:not(:first-child)');
            if (existingInfo) {
                existingInfo.remove();
            }
        }
        
        // Load parent decks for both forms - call this BEFORE showing the modal
        loadParentDecks();
        
        // Show the modal
        bsImportModal.show();
        
        // Activate first tab
        const firstTab = document.querySelector('#importTabs .nav-link');
        if (firstTab) {
            const tabTrigger = new bootstrap.Tab(firstTab);
            tabTrigger.show();
        }
    };
    
    // Also attach the loadParentDecks function to the modal's shown.bs.modal event
    importModal.addEventListener('shown.bs.modal', function() {
        console.log("Import modal shown event triggered");
        loadParentDecks();  // Load decks when modal is fully shown
    });
    
    // Skip if drag and drop elements aren't present
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
    if (fileUploadForm) {
        fileUploadForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const fileInput = document.getElementById('fileInput');
            const uploadBtn = document.getElementById('uploadBtn');
            const normalState = uploadBtn.querySelector('.normal-state');
            const loadingState = uploadBtn.querySelector('.loading-state');
            const uploadResult = document.getElementById('uploadResult');
            
            // Clear previous results
            uploadResult.innerHTML = '';
            
            uploadBtn.disabled = true;
            loadingState.classList.remove('d-none');
            normalState.classList.add('d-none');
            
            const formData = new FormData(fileUploadForm);
            
            try {
                uploadResult.innerHTML = `
                    <div class="alert alert-info">
                        <span class="spinner-border spinner-border-sm me-2" role="status"></span>
                        Processing your file. This may take a moment for larger documents...
                    </div>
                `;
                
                const response = await fetch(fileUploadForm.action, {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const errorText = await response.text();
                    try {
                        // Try to parse as JSON
                        const errorData = JSON.parse(errorText);
                        throw new Error(errorData.error || 'Server error occurred');
                    } catch (jsonError) {
                        // If not valid JSON, use text or generic message
                        throw new Error(errorText || 'An unknown error occurred');
                    }
                }
                
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
    }
    
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
        console.log("Fetching parent decks for import modal");
        
        // Set loading state for the select elements
        const parentDeckId = document.getElementById('parentDeckId');
        const textParentDeckId = document.getElementById('textParentDeckId');
        
        if (parentDeckId) {
            parentDeckId.innerHTML = '<option value="">Loading decks...</option>';
            parentDeckId.parentElement.classList.add('select-loading');
        }
        
        if (textParentDeckId) {
            textParentDeckId.innerHTML = '<option value="">Loading decks...</option>';
            textParentDeckId.parentElement.classList.add('select-loading');
        }
        
        // Fetch the decks
        const response = await fetch('/deck/api/list');
        
        if (!response.ok) {
            throw new Error(`Failed to fetch decks: ${response.statusText}`);
        }
        
        const decks = await response.json();
        console.log(`Fetched ${decks.length} decks`, decks);
        
        // Check if the select elements exist
        if (!parentDeckId && !textParentDeckId) {
            console.warn("Parent deck select elements not found");
            return;
        }
        
        // Reset the first option for both selects
        if (parentDeckId) {
            parentDeckId.innerHTML = '<option value="">Select a parent deck</option>';
            parentDeckId.parentElement.classList.remove('select-loading');
        }
        
        if (textParentDeckId) {
            textParentDeckId.innerHTML = '<option value="">Select a parent deck</option>';
            textParentDeckId.parentElement.classList.remove('select-loading');
        }
        
        // Helper function to populate select element
        function populateSelect(selectElement, decks, level = 0) {
            if (!selectElement) return;
            
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
        
        console.log("Finished populating deck selectors");
        
    } catch (error) {
        console.error('Error loading parent decks:', error);
        
        // Set error state if loading fails
        const errorMsg = 'Failed to load decks';
        
        const parentDeckId = document.getElementById('parentDeckId');
        const textParentDeckId = document.getElementById('textParentDeckId');
        
        if (parentDeckId) {
            parentDeckId.innerHTML = `<option value="">${errorMsg}</option>`;
            parentDeckId.parentElement.classList.remove('select-loading');
        }
        
        if (textParentDeckId) {
            textParentDeckId.innerHTML = `<option value="">${errorMsg}</option>`;
            textParentDeckId.parentElement.classList.remove('select-loading');
        }
    }
}
