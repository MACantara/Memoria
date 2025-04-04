document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const dragArea = document.getElementById('dragArea');
    const browseBtn = document.getElementById('browseBtn');
    const fileInput = document.getElementById('fileInput');
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    const removeFile = document.getElementById('removeFile');
    const importBtn = document.getElementById('importBtn');
    const importDeckSelect = document.getElementById('importDeckSelect');
    const importFileForm = document.getElementById('importFileForm');
    const processingInfo = document.getElementById('processingInfo');
    const processingStatus = document.getElementById('processingStatus');
    const processingProgress = document.getElementById('processingProgress');
    const importResults = document.getElementById('importResults');
    const resultsTab = document.getElementById('results-tab');
    const deckSearchInput = document.getElementById('deckSearchInput');
    const viewResultsBtn = document.getElementById('viewResultsBtn');
    
    // Global variables
    let fileKey = null;
    let generatedFlashcards = [];
    let totalSavedCards = 0;
    let shouldRefreshOnClose = false; // New flag to track if we should refresh on close
    
    // Pagination state
    let currentPage = 1;
    let cardsPerPage = 25;
    
    // Initialize when modal is shown
    $('#importContentModal').on('shown.bs.modal', function () {
        // Reset drag area and file input
        resetFileInput();
        
        // Clear search input
        if (deckSearchInput) {
            deckSearchInput.value = '';
            filterDeckOptions('');
        }
        
        // Reset counters
        totalSavedCards = 0;
        
        // Show the upload tab by default
        const uploadTab = document.getElementById('upload-tab');
        if (uploadTab) {
            const tabInstance = new bootstrap.Tab(uploadTab);
            tabInstance.show();
        }
        
        // Reset the viewResultsBtn
        if (viewResultsBtn) {
            viewResultsBtn.classList.add('d-none');
        }
        
        // Call attention to drag area with subtle pulse
        dragArea.classList.add('pulse-once');
        setTimeout(() => dragArea.classList.remove('pulse-once'), 1500);

        // Reset refresh flag
        shouldRefreshOnClose = false;
    });
    
    // Add event handler for modal hidden event to refresh page if needed
    $('#importContentModal').on('hidden.bs.modal', function () {
        if (shouldRefreshOnClose && totalSavedCards > 0) {
            // If we saved cards and the flag is set, refresh the page
            window.location.reload();
        }
    });
    
    // Add search functionality
    if (deckSearchInput) {
        // Add no results feedback if not already present
        if (!importDeckSelect.nextElementSibling || !importDeckSelect.nextElementSibling.classList.contains('search-feedback')) {
            const feedbackElement = document.createElement('div');
            feedbackElement.className = 'search-feedback';
            feedbackElement.textContent = 'No matching decks found';
            importDeckSelect.parentNode.insertBefore(feedbackElement, importDeckSelect.nextSibling);
        }
        
        deckSearchInput.addEventListener('input', function() {
            const searchTerm = this.value.trim().toLowerCase();
            filterDeckOptions(searchTerm);
        });
        
        // Clear button to reset search
        deckSearchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                this.value = '';
                filterDeckOptions('');
            }
        });
    }
    
    // Filter deck options based on search term
    function filterDeckOptions(searchTerm) {
        const options = importDeckSelect.querySelectorAll('option:not([disabled])');
        let visibleCount = 0;
        
        options.forEach(option => {
            const deckName = option.dataset.deckName || option.textContent.toLowerCase();
            const isMatch = searchTerm === '' || deckName.includes(searchTerm);
            
            option.style.display = isMatch ? '' : 'none';
            if (isMatch) visibleCount++;
        });
        
        // Add or remove no-results class
        if (visibleCount === 0 && searchTerm !== '') {
            importDeckSelect.parentNode.classList.add('no-results');
        } else {
            importDeckSelect.parentNode.classList.remove('no-results');
        }
        
        // Ensure first visible option is pre-selected if there is no current selection
        if (!importDeckSelect.value || importDeckSelect.selectedOptions[0].style.display === 'none') {
            const firstVisibleOption = Array.from(options).find(opt => opt.style.display !== 'none');
            if (firstVisibleOption) {
                firstVisibleOption.selected = true;
                // Update import button state if needed
                importBtn.disabled = !importDeckSelect.value || !fileInput.files.length;
            }
        }
    }
    
    // Drag and Drop events
    dragArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.classList.add('active');
    });
    
    dragArea.addEventListener('dragleave', function() {
        this.classList.remove('active');
    });
    
    dragArea.addEventListener('drop', function(e) {
        e.preventDefault();
        this.classList.remove('active');
        
        const file = e.dataTransfer.files[0];
        handleFile(file);
    });
    
    // Make dragArea also clickable to open file dialog
    dragArea.addEventListener('click', function(e) {
        if (e.target !== browseBtn) {
            fileInput.click();
        }
    });
    
    // Browse button
    browseBtn.addEventListener('click', function() {
        fileInput.click();
    });
    
    // File input change
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            handleFile(this.files[0]);
        }
    });
    
    // Remove file
    removeFile.addEventListener('click', function() {
        resetFileInput();
    });
    
    // Handle selected file with improved UI feedback
    function handleFile(file) {
        const validTypes = ['.txt', '.pdf'];
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        
        if (!validTypes.includes(extension)) {
            // Show invalid file type error
            fileInfo.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Invalid file type. Please upload a TXT or PDF file.
                </div>
            `;
            fileInfo.classList.remove('d-none');
            importBtn.disabled = true;
            return;
        }
        
        // Show file info with enhanced styling
        fileName.textContent = file.name;
        const fileSize = (file.size / 1024).toFixed(2);
        const fileIcon = file.name.toLowerCase().endsWith('.pdf') ? 'bi-file-earmark-pdf' : 'bi-file-earmark-text';
        
        fileInfo.innerHTML = `
            <div class="alert alert-info">
                <i class="${fileIcon} me-2"></i>
                <div class="d-flex justify-content-between align-items-center w-100">
                    <div>
                        <strong>${file.name}</strong>
                        <div class="small text-muted">${fileSize} KB</div>
                    </div>
                    <button type="button" class="btn-close" id="removeFile"></button>
                </div>
            </div>
        `;
        
        fileInfo.classList.remove('d-none');
        dragArea.classList.add('d-none');
        
        // Attach remove button listener again since we recreated the button
        document.getElementById('removeFile').addEventListener('click', resetFileInput);
        
        // Enable import button if deck is selected
        importBtn.disabled = !importDeckSelect.value;
        
        // Store file in input for form submission
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        fileInput.files = dataTransfer.files;
    }
    
    // Reset file input
    function resetFileInput() {
        fileInput.value = '';
        fileInfo.classList.add('d-none');
        dragArea.classList.remove('d-none');
        importBtn.disabled = true;
    }
    
    // Enable import button only when both file and deck are selected
    importDeckSelect.addEventListener('change', function() {
        importBtn.disabled = !this.value || !fileInput.files.length;
    });
    
    // Import form submission
    importFileForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (!fileInput.files.length || !importDeckSelect.value) {
            return;
        }
        
        // Show results tab
        const resultsTabInstance = new bootstrap.Tab(resultsTab);
        resultsTabInstance.show();
        
        // Show processing info with initial animation
        processingInfo.classList.remove('d-none');
        processingProgress.style.width = '0%';
        processingProgress.textContent = '0%';
        processingProgress.classList.add('progress-bar-striped', 'progress-bar-animated');
        
        // Add the processing-active class to enable the pulse animation
        processingInfo.classList.add('processing-active');
        
        processingStatus.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="upload-spinner me-2">
                    <div class="spinner-border spinner-border-sm text-primary" role="status">
                        <span class="visually-hidden">Uploading...</span>
                    </div>
                </div>
                <span>Uploading file<span class="status-text"></span></span>
            </div>
        `;
        
        importResults.innerHTML = '';
        
        // Upload file
        const formData = new FormData(this);
        
        fetch('/import/upload-file', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) throw new Error('Upload failed');
            return response.json();
        })
        .then(data => {
            if (data.error) throw new Error(data.error);
            
            fileKey = data.file_key;
            
            // Start background processing instead of doing it in the browser
            return fetch('/import/start-background-import', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    file_key: fileKey,
                    deck_id: importDeckSelect.value
                })
            })
            .then(response => {
                if (!response.ok) throw new Error('Failed to start background processing');
                return response.json();
            })
            .then(result => {
                if (result.error) throw new Error(result.error);
                
                // Show message that processing has started in the background
                processingStatus.innerHTML = `
                    <div class="d-flex align-items-center">
                        <div class="flex-grow-1">
                            <i class="bi bi-info-circle me-2"></i>
                            <strong>Processing Started!</strong> Your import is now running in the background.
                        </div>
                    </div>
                `;
                
                // Update progress bar to show indeterminate state
                processingProgress.style.width = '100%';
                processingProgress.textContent = 'Running in background';
                
                // Set refresh flag so the page refreshes when modal is closed
                shouldRefreshOnClose = true;
                
                // Show status info with link to imports dashboard
                processingInfo.innerHTML = `
                    <div class="alert alert-info">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <i class="bi bi-arrow-repeat me-2"></i>
                                <strong>Import Started!</strong> This process will continue in the background.
                                You can close this modal and continue using the app.
                            </div>
                            <button class="btn btn-sm btn-primary" onclick="window.location.href='/import/import-dashboard'">
                                <i class="bi bi-eye me-1"></i> View All Imports
                            </button>
                        </div>
                    </div>
                `;
                
                // Show view results button
                if (viewResultsBtn) {
                    viewResultsBtn.classList.remove('d-none');
                    viewResultsBtn.innerHTML = '<i class="bi bi-arrow-left me-1"></i> View Imports Dashboard';
                    
                    // Navigate to imports dashboard
                    viewResultsBtn.onclick = () => {
                        window.location.href = '/import/import-dashboard';
                    };
                }
            });
        })
        .catch(error => {
            // Remove animation classes on error
            processingProgress.classList.remove('progress-bar-striped', 'progress-bar-animated');
            processingInfo.classList.remove('processing-active');
            
            processingInfo.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Error: ${error.message}
                </div>
            `;
        });
    });
    
    // Process file chunks
    function processNextChunk(fileKey) {
        return fetch('/import/generate-chunk', {
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
            if (data.error) throw new Error(data.error);
            
            // Update progress
            const progress = Math.round((data.chunk_index + 1) / data.total_chunks * 100);
            processingProgress.style.width = `${progress}%`;
            processingProgress.textContent = `${progress}%`;
            
            // Track saved cards
            if (data.cards_saved) {
                totalSavedCards = data.total_saved_cards || (totalSavedCards + data.cards_saved);
                // Set the refresh flag if any cards were saved
                if (data.cards_saved > 0) {
                    shouldRefreshOnClose = true;
                }
            }
            
            // Update processing status with auto-saving information
            let statusMessage = '';
            
            if (data.already_saved) {
                statusMessage = `Processing file... (${data.chunk_index + 1}/${data.total_chunks} chunks) - Already processed`;
            } else if (data.cards_saved > 0) {
                statusMessage = `Processing file... (${data.chunk_index + 1}/${data.total_chunks} chunks) - Saved ${data.cards_saved} cards`;
            } else {
                statusMessage = `Processing file... (${data.chunk_index + 1}/${data.total_chunks} chunks)`;
            }
            
            // Improved styling for the cards saved counter
            processingStatus.innerHTML = `
                <div class="d-flex align-items-center">
                    <div class="chunk-spinner me-2">
                        <div class="spinner-grow spinner-grow-sm text-primary" role="status">
                            <span class="visually-hidden">Processing...</span>
                        </div>
                    </div>
                    <div class="flex-grow-1">
                        <span>${statusMessage}</span>
                    </div>
                    <div class="ms-2">
                        <span class="badge bg-success rounded-pill d-flex align-items-center">
                            <i class="bi bi-card-list me-1"></i>
                            <strong>${totalSavedCards}</strong>&nbsp;cards saved
                        </span>
                    </div>
                </div>
            `;
            
            // Update results
            return updateResults(fileKey)
                .then(() => {
                    // Continue processing or complete
                    if (!data.is_complete) {
                        return processNextChunk(fileKey);
                    } else {
                        // Stop animations when complete
                        processingProgress.classList.remove('progress-bar-animated', 'progress-bar-striped');
                        processingInfo.classList.remove('processing-active');
                        
                        processingInfo.innerHTML = `
                            <div class="alert alert-success">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <i class="bi bi-check-circle me-2"></i>
                                        <strong>Generation Complete!</strong> 
                                        <span class="badge bg-success rounded-pill ms-2 px-3 py-2">
                                            <i class="bi bi-card-list me-1"></i>
                                            <strong>${totalSavedCards}</strong> flashcards saved
                                        </span>
                                    </div>
                                    <button class="btn btn-sm btn-primary" id="viewGeneratedCardsBtn">
                                        <i class="bi bi-eye me-1"></i> View Cards
                                    </button>
                                </div>
                            </div>
                        `;
                        
                        // Set the flag to refresh on close after successful completion
                        if (totalSavedCards > 0) {
                            shouldRefreshOnClose = true;
                        }
                        
                        // Show the view results button
                        if (viewResultsBtn) {
                            viewResultsBtn.classList.remove('d-none');
                            viewResultsBtn.innerHTML = '<i class="bi bi-journal-text me-1"></i> View Cards in Deck';
                            
                            // Ensure we only attach the event listener once
                            viewResultsBtn.onclick = () => {
                                // Navigate to the deck page
                                const deckId = importDeckSelect.value;
                                if (deckId) {
                                    window.location.href = `/deck/${deckId}`;
                                }
                            };
                        }
                        
                        // Make "View Cards" button work to show all generated cards
                        const viewBtn = document.getElementById('viewGeneratedCardsBtn');
                        if (viewBtn) {
                            viewBtn.addEventListener('click', () => {
                                // Show all generated cards
                                renderFlashcardPage();
                                
                                // Add "completed" message above the cards
                                const completionMsg = document.createElement('div');
                                completionMsg.className = 'alert alert-success mb-3';
                                completionMsg.innerHTML = `
                                    <i class="bi bi-check-circle-fill me-2"></i>
                                    <strong>Success:</strong> All ${totalSavedCards} flashcards have been automatically saved to your deck.
                                `;
                                
                                // Add the message at the top of the results
                                if (importResults.firstChild) {
                                    importResults.insertBefore(completionMsg, importResults.firstChild);
                                } else {
                                    importResults.appendChild(completionMsg);
                                }
                            });
                        }
                        
                        // Also show the View Results button in the main dialog
                        if (viewResultsBtn) {
                            viewResultsBtn.classList.remove('d-none');
                            viewResultsBtn.addEventListener('click', () => {
                                // Navigate to the deck page
                                const deckId = importDeckSelect.value;
                                if (deckId) {
                                    window.location.href = `/deck/${deckId}`;
                                }
                            });
                        }
                        
                        return Promise.resolve();
                    }
                });
        });
    }
    
    // Update flashcard results
    function updateResults(fileKey) {
        return fetch(`/import/all-file-flashcards?file_key=${fileKey}&format=mc`)
            .then(response => {
                if (!response.ok) throw new Error('Failed to fetch flashcards');
                return response.json();
            })
            .then(data => {
                generatedFlashcards = data.mc_flashcards || [];
                
                // The rest of the function can remain as is, but we'll only render when requested
                // to avoid slowing down the processing
                if (document.getElementById('cardsPreviewContainer').classList.contains('show-preview')) {
                    renderFlashcardPage();
                }
                
                return Promise.resolve();
            });
    }

    // Generate HTML for preview card
    function previewCardHTML(card, index) {
        // Build the list of incorrect answers with better formatting
        let incorrectAnswersHTML = '';
        if (card.ia && card.ia.length > 0) {
            incorrectAnswersHTML = `
                <div class="mt-3">
                    <div class="text-muted mb-1 small fw-medium">
                        <i class="bi bi-x-circle me-1"></i> Incorrect Answers:
                    </div>
                    <ul class="list-group incorrect-answers-list">
            `;
            
            // Add each incorrect answer as a separate list item
            card.ia.forEach(answer => {
                incorrectAnswersHTML += `
                    <li class="list-group-item list-group-item-light border-0 py-1 px-2 mb-1 rounded">
                        <div class="d-flex align-items-start">
                            <span class="text-danger me-2">•</span>
                            <span class="small">${answer}</span>
                        </div>
                    </li>
                `;
            });
            
            incorrectAnswersHTML += `
                    </ul>
                </div>
            `;
        } else {
            incorrectAnswersHTML = `
                <div class="mt-3 text-muted small">
                    <i class="bi bi-info-circle me-1"></i> No incorrect answers provided
                </div>
            `;
        }

        return `
            <div class="col-md-6">
                <div class="card h-100" data-card-index="${index}">
                    <div class="card-header bg-transparent d-flex justify-content-between align-items-center py-2">
                        <div class="small text-muted">Card #${index + 1}</div>
                        <button type="button" class="btn btn-sm btn-outline-danger delete-card-btn" 
                                data-index="${index}" aria-label="Delete card">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                    <div class="card-body">
                        <h5 class="card-title">
                            ${card.q}
                        </h5>
                        <hr>
                        <div class="card-text">
                            <div class="correct-answer">
                                <div class="mb-1 small fw-medium text-success">
                                    <i class="bi bi-check-circle-fill me-1"></i> Correct Answer:
                                </div>
                                <div class="p-2 bg-success-subtle border-start border-success border-2 rounded">
                                    ${card.ca}
                                </div>
                            </div>
                            ${incorrectAnswersHTML}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    // Add function to render pagination controls
    function renderPaginationControls(currentPage, totalPages) {
        let paginationHTML = `
            <nav aria-label="Flashcard pagination">
                <ul class="pagination">
                    <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                        <a class="page-link" href="#" data-page="prev" aria-label="Previous">
                            <span aria-hidden="true">&laquo;</span>
                        </a>
                    </li>
        `;
        
        // Logic for showing page numbers
        const maxVisiblePages = 5;
        let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
        let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
        
        // Adjust if we're near the end
        if (endPage - startPage + 1 < maxVisiblePages) {
            startPage = Math.max(1, endPage - maxVisiblePages + 1);
        }
        
        // Always show first page
        if (startPage > 1) {
            paginationHTML += `
                <li class="page-item">
                    <a class="page-link" href="#" data-page="1">1</a>
                </li>
            `;
            
            // Add ellipsis if needed
            if (startPage > 2) {
                paginationHTML += `
                    <li class="page-item disabled">
                        <span class="page-link">...</span>
                    </li>
                `;
            }
        }
        
        // Add page numbers
        for (let i = startPage; i <= endPage; i++) {
            paginationHTML += `
                <li class="page-item ${i === currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" data-page="${i}">${i}</a>
                </li>
            `;
        }
        
        // Add ellipsis and last page if needed
        if (endPage < totalPages - 1) {
            paginationHTML += `
                <li class="page-item disabled">
                    <span class="page-link">...</span>
                </li>
            `;
        }
        
        if (endPage < totalPages) {
            paginationHTML += `
                <li class="page-item">
                    <a class="page-link" href="#" data-page="${totalPages}">${totalPages}</a>
                </li>
            `;
        }
        
        paginationHTML += `
                    <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
                        <a class="page-link" href="#" data-page="next" aria-label="Next">
                            <span aria-hidden="true">&raquo;</span>
                        </a>
                    </li>
                </ul>
            </nav>
        `;
        
        return paginationHTML;
    }
    
    // Add function to handle pagination clicks
    function setupPaginationHandlers(totalPages) {
        document.querySelectorAll('.pagination .page-link').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                
                const pageAction = this.dataset.page;
                
                if (pageAction === 'prev') {
                    if (currentPage > 1) {
                        goToPage(currentPage - 1);
                    }
                } else if (pageAction === 'next') {
                    if (currentPage < totalPages) {
                        goToPage(currentPage + 1);
                    }
                } else {
                    const pageNumber = parseInt(pageAction);
                    if (!isNaN(pageNumber)) {
                        goToPage(pageNumber);
                    }
                }
            });
        });
    }
    
    // Function to navigate to a specific page
    function goToPage(pageNumber) {
        currentPage = pageNumber;
        
        // Show loading indicator
        importResults.innerHTML = `
            <div class="text-center py-3">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
        
        // Re-render with the same flashcards
        setTimeout(() => {
            renderFlashcardPage();
        }, 100); // Short timeout for better UX
    }
    
    // Function to render the current page of flashcards
    function renderFlashcardPage() {
        importResults.innerHTML = '';
        
        if (generatedFlashcards.length === 0) {
            importResults.innerHTML = '<p class="text-muted">No flashcards generated yet...</p>';
            return;
        }
        
        // Calculate total pages
        const totalPages = Math.ceil(generatedFlashcards.length / cardsPerPage);
        
        // Ensure current page is valid
        if (currentPage > totalPages) {
            currentPage = totalPages;
        }
        
        // Calculate start and end indices for current page
        const startIndex = (currentPage - 1) * cardsPerPage;
        const endIndex = Math.min(startIndex + cardsPerPage, generatedFlashcards.length);
        
        // Get current page cards
        const currentPageCards = generatedFlashcards.slice(startIndex, endIndex);
        
        // Create rows for current page cards
        const cardRows = [];
        for (let i = 0; i < currentPageCards.length; i += 2) {
            const row = document.createElement('div');
            row.className = 'row g-3 mb-3';
            
            // First card in row
            const card1 = previewCardHTML(currentPageCards[i], startIndex + i);
            row.innerHTML += card1;
            
            // Second card in row (if exists)
            if (i + 1 < currentPageCards.length) {
                const card2 = previewCardHTML(currentPageCards[i + 1], startIndex + i + 1);
                row.innerHTML += card2;
            }
            
            cardRows.push(row);
        }
        
        // Show message with pagination info
        const totalMessage = document.createElement('div');
        totalMessage.className = 'alert alert-info';
        totalMessage.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <i class="bi bi-info-circle me-2"></i> 
                    Showing ${startIndex + 1}-${endIndex} of ${generatedFlashcards.length} generated flashcards
                </div>
                <div class="dropdown">
                    <button class="btn btn-sm btn-secondary dropdown-toggle" type="button" id="showPerPageBtn" data-bs-toggle="dropdown" aria-expanded="false">
                        ${cardsPerPage} per page
                    </button>
                    <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="showPerPageBtn">
                        <li><a class="dropdown-item per-page-option ${cardsPerPage === 25 ? 'active' : ''}" href="#" data-value="25">25 cards</a></li>
                        <li><a class="dropdown-item per-page-option ${cardsPerPage === 50 ? 'active' : ''}" href="#" data-value="50">50 cards</a></li>
                        <li><a class="dropdown-item per-page-option ${cardsPerPage === 75 ? 'active' : ''}" href="#" data-value="75">75 cards</a></li>
                        <li><a class="dropdown-item per-page-option ${cardsPerPage === 100 ? 'active' : ''}" href="#" data-value="100">100 cards</a></li>
                    </ul>
                </div>
            </div>
        `;
        
        importResults.appendChild(totalMessage);
        cardRows.forEach(row => importResults.appendChild(row));
        
        // Add pagination controls if we have multiple pages
        if (totalPages > 1) {
            const paginationControls = document.createElement('div');
            paginationControls.className = 'mt-3 d-flex justify-content-center';
            paginationControls.innerHTML = renderPaginationControls(currentPage, totalPages);
            importResults.appendChild(paginationControls);
            
            // Add event listeners for pagination buttons
            setupPaginationHandlers(totalPages);
        }
        
        // Add event listeners for delete buttons
        setupDeleteCardButtons();
        
        // Setup per-page dropdown handlers
        setupPerPageHandlers();
    }
    
    // Add function to setup delete card buttons
    function setupDeleteCardButtons() {
        const deleteButtons = document.querySelectorAll('.delete-card-btn');
        deleteButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const index = parseInt(this.dataset.index);
                const cardElement = this.closest('.card');
                const colElement = cardElement.closest('.col-md-6');
                
                // Show confirmation dialog
                if (confirm('Are you sure you want to delete this flashcard?')) {
                    // Remove the card from the generated flashcards array
                    generatedFlashcards.splice(index, 1);
                    
                    // Remove the card from the UI with animation
                    cardElement.style.transition = 'all 0.3s ease';
                    cardElement.style.opacity = '0';
                    cardElement.style.transform = 'translateY(-10px)';
                    
                    setTimeout(() => {
                        // Check if we need to go to the previous page
                        const totalPages = Math.ceil(generatedFlashcards.length / cardsPerPage);
                        if (currentPage > totalPages && totalPages > 0) {
                            currentPage = totalPages;
                        }
                        
                        // Re-render the current page
                        renderFlashcardPage();
                        
                        // If all cards are deleted, show empty state
                        if (generatedFlashcards.length === 0) {
                            importResults.innerHTML = '<div class="alert alert-warning"><i class="bi bi-exclamation-triangle me-2"></i>All flashcards have been deleted.</div>';
                        }
                    }, 300);
                }
            });
        });
    }
    
    // Add function to handle changing cards per page
    function setupPerPageHandlers() {
        document.querySelectorAll('.per-page-option').forEach(option => {
            option.addEventListener('click', function(e) {
                e.preventDefault();
                const newPerPage = parseInt(this.dataset.value);
                
                if (newPerPage && newPerPage !== cardsPerPage) {
                    // Store the current first visible card index before changing
                    const currentStartIndex = (currentPage - 1) * cardsPerPage;
                    
                    // Update the cards per page in the original variable, not window
                    cardsPerPage = newPerPage;
                    
                    // Update the dropdown button text
                    const perPageBtn = document.getElementById('showPerPageBtn');
                    if (perPageBtn) {
                        perPageBtn.textContent = `${cardsPerPage} per page`;
                    }
                    
                    // Update active state in dropdown
                    document.querySelectorAll('.per-page-option').forEach(opt => {
                        if (parseInt(opt.dataset.value) === cardsPerPage) {
                            opt.classList.add('active');
                        } else {
                            opt.classList.remove('active');
                        }
                    });
                    
                    // Calculate which page the current first visible card would be on with new per-page setting
                    currentPage = Math.floor(currentStartIndex / newPerPage) + 1;
                    
                    // Re-render with new pagination settings
                    renderFlashcardPage();
                }
            });
        });
    }
    
    // Add a toggle button for showing/hiding card preview
    const previewToggleBtn = document.getElementById('togglePreviewBtn');
    if (previewToggleBtn) {
        previewToggleBtn.addEventListener('click', function() {
            const previewContainer = document.getElementById('cardsPreviewContainer');
            if (previewContainer) {
                if (previewContainer.classList.contains('show-preview')) {
                    previewContainer.classList.remove('show-preview');
                    this.innerHTML = '<i class="bi bi-eye"></i> Show Preview';
                } else {
                    previewContainer.classList.add('show-preview');
                    this.innerHTML = '<i class="bi bi-eye-slash"></i> Hide Preview';
                    // Render cards when showing preview
                    renderFlashcardPage();
                }
            }
        });
    }
});