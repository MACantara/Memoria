/**
 * Learning index module - handles functionality for the learning landing page
 */

/**
 * Initialize the learning index page
 */
export function initializeLearningIndex() {
    // Initialize form validation
    const learningForm = document.querySelector('form[action*="start_session"]');
    if (learningForm) {
        learningForm.addEventListener('submit', function(event) {
            const topicInput = this.querySelector('input[name="topic"]');
            if (!topicInput.value.trim()) {
                event.preventDefault();
                // Add validation feedback
                topicInput.classList.add('is-invalid');
                
                // Create error message if it doesn't exist
                if (!document.getElementById('topic-error')) {
                    const errorDiv = document.createElement('div');
                    errorDiv.id = 'topic-error';
                    errorDiv.className = 'invalid-feedback';
                    errorDiv.textContent = 'Please enter a topic to learn about';
                    topicInput.parentNode.appendChild(errorDiv);
                }
            }
        });

        // Clear validation state on input
        const topicInput = learningForm.querySelector('input[name="topic"]');
        if (topicInput) {
            topicInput.addEventListener('input', function() {
                this.classList.remove('is-invalid');
            });
        }
    }

    // Add topic suggestion functionality if needed
    initializeTopicSuggestions();
}

/**
 * Initialize topic suggestion functionality
 */
function initializeTopicSuggestions() {
    // Example topics that could be suggested
    const exampleTopics = [
        "Quantum Computing",
        "Climate Change",
        "Machine Learning",
        "World History",
        "Renewable Energy",
        "Psychology",
        "Blockchain Technology",
        "Artificial Intelligence",
        "Human Anatomy"
    ];

    // Add a suggestion button if needed
    const topicInput = document.querySelector('input[name="topic"]');
    if (topicInput) {
        // Add placeholder that cycles through example topics
        let currentIndex = 0;
        
        // Set initial placeholder
        topicInput.setAttribute('placeholder', `e.g., ${exampleTopics[currentIndex]}`);
        
        // Cycle through examples
        const interval = setInterval(() => {
            currentIndex = (currentIndex + 1) % exampleTopics.length;
            topicInput.setAttribute('placeholder', `e.g., ${exampleTopics[currentIndex]}`);
        }, 3000);
    }
}
