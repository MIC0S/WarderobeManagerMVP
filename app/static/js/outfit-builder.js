window.outfitBuilder = {
    initialize() {
        this.initializeSearch();
        this.initializeDragAndDrop(); // ADD THIS LINE - was missing!
    },

    initializeSearch() {
        const wardrobeSearch = document.getElementById('wardrobe-search');
        const outfitSearch = document.getElementById('outfit-search');

        if (wardrobeSearch) {
            wardrobeSearch.addEventListener('input', () => this.filterBuilderItems());
        }
        if (outfitSearch) {
            outfitSearch.addEventListener('input', () => this.filterBuilderItems());
        }
    },

    filterBuilderItems() {
        const wardrobeSearch = document.getElementById('wardrobe-search')?.value.toLowerCase() || '';
        const outfitSearch = document.getElementById('outfit-search')?.value.toLowerCase() || '';

        // Filter available clothes
        const availableItems = document.querySelectorAll('#available-clothes .builder-clothing-item');
        availableItems.forEach(item => {
            const name = item.getAttribute('data-item-name');
            if (name.includes(wardrobeSearch)) {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });

        // Filter selected items
        const selectedItems = document.querySelectorAll('#selected-items .builder-clothing-item');
        selectedItems.forEach(item => {
            const name = item.getAttribute('data-item-name');
            if (name.includes(outfitSearch)) {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });
    },

    initializeDragAndDrop() {
        const availableContainer = document.getElementById('available-clothes');
        const selectedContainer = document.getElementById('selected-items');

        if (!availableContainer || !selectedContainer) {
            console.log('Drag and drop containers not found');
            return;
        }

        // Make both containers droppable
        [availableContainer, selectedContainer].forEach(container => {
            container.addEventListener('dragover', (e) => {
                e.preventDefault();
                container.classList.add('drag-over');
            });

            container.addEventListener('dragleave', () => {
                container.classList.remove('drag-over');
            });

            container.addEventListener('drop', (e) => {
                e.preventDefault();
                container.classList.remove('drag-over');

                const itemId = e.dataTransfer.getData('text/plain');
                const draggedItem = document.querySelector(`[data-item-id="${itemId}"]`);

                if (draggedItem && container !== draggedItem.parentElement) {
                    // Remove from current parent
                    draggedItem.remove();

                    // Add to new container
                    container.appendChild(draggedItem);

                    // Update empty states
                    this.updateEmptyStates();
                    this.filterBuilderItems(); // ADD THIS - update search filters
                }
            });
        });

        // Make all items draggable
        const allItems = document.querySelectorAll('.builder-clothing-item');
        allItems.forEach(item => {
            item.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('text/plain', item.getAttribute('data-item-id'));
                item.classList.add('dragging');
            });

            item.addEventListener('dragend', () => {
                item.classList.remove('dragging');
            });
        });

        this.updateEmptyStates(); // INITIALIZE EMPTY STATES
    },

    updateEmptyStates() {
        const selectedContainer = document.getElementById('selected-items');
        const availableContainer = document.getElementById('available-clothes');

        if (!selectedContainer || !availableContainer) return;

        // Update selected items empty state
        const selectedItems = selectedContainer.querySelectorAll('.builder-clothing-item');
        let selectedEmptyState = selectedContainer.querySelector('.empty-state');

        if (selectedItems.length === 0 && !selectedEmptyState) {
            selectedContainer.innerHTML = '<div class="empty-state">Drag items here to build your outfit</div>';
        } else if (selectedItems.length > 0 && selectedEmptyState) {
            selectedEmptyState.remove();
        }

        // Update available clothes empty state
        const availableItems = availableContainer.querySelectorAll('.builder-clothing-item');
        let availableEmptyState = availableContainer.querySelector('.empty-state');

        if (availableItems.length === 0 && !availableEmptyState) {
            availableContainer.innerHTML = '<div class="empty-state">All items are in your outfit</div>';
        } else if (availableItems.length > 0 && availableEmptyState) {
            availableEmptyState.remove();
        }
    },

    reset() {
        // Clear outfit name
        const outfitNameInput = document.getElementById('outfit-name');
        if (outfitNameInput) {
            outfitNameInput.value = '';
        }

        // Clear search inputs
        const wardrobeSearch = document.getElementById('wardrobe-search');
        const outfitSearch = document.getElementById('outfit-search');
        if (wardrobeSearch) wardrobeSearch.value = '';
        if (outfitSearch) outfitSearch.value = '';

        // Move all items back to available clothes
        const selectedContainer = document.getElementById('selected-items');
        const availableContainer = document.getElementById('available-clothes');

        if (selectedContainer && availableContainer) {
            const selectedItems = selectedContainer.querySelectorAll('.builder-clothing-item');
            selectedItems.forEach(item => {
                availableContainer.appendChild(item);
                item.style.display = 'flex'; // Ensure it's visible
            });

            // Reset empty states
            this.updateEmptyStates();
            this.filterBuilderItems();
        }
    },

    saveOutfit() {
        const outfitName = document.getElementById('outfit-name')?.value.trim();
        const selectedItems = document.querySelectorAll('#selected-items .builder-clothing-item');

        if (selectedItems.length === 0) {
            alert('Please add at least one item to your outfit');
            return;
        }

        if (!outfitName) {
            alert('Please enter a name for your outfit');
            return;
        }

        const itemIds = Array.from(selectedItems).map(item => item.getAttribute('data-item-id'));

        if (window.outfitsManager && window.outfitsManager.isConnected()) {
            // Show loading state
            this.setSaveButtonState('Saving...', true);

            const success = window.outfitsManager.createOutfit(outfitName, itemIds);

            if (!success) {
                alert('Failed to send outfit creation request. Please check connection.');
                this.setSaveButtonState('Save Outfit', false);
            }
            // If success, we wait for WebSocket response to reset
        } else {
            alert('Not connected to server. Please try again.');
            this.setSaveButtonState('Save Outfit', false);
        }
    },

    setSaveButtonState(text, disabled) {
        const saveButton = document.querySelector('.btn-save-outfit');
        if (saveButton) {
            saveButton.textContent = text;
            saveButton.disabled = disabled;
        }
    },

    // Call this when outfit is successfully created via WebSocket
    onOutfitCreated() {
        this.reset();
        this.setSaveButtonState('Save Outfit', false);
        showOutfitLibrary();
    }
};