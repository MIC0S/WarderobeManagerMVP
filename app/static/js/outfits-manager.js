window.outfitsManager = {
    socket: null,
    outfitsGrid: null,
    emptyState: null,
    cachedOutfits: [], // Store outfits data
    isLibraryVisible: false,

    connect() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            return;
        }

        this.socket = new WebSocket(`ws://${window.location.host}/ws/outfits`);

        this.socket.onopen = (event) => {
            console.log('Outfits WebSocket connected');
            this.loadOutfits(); // Load outfits but don't display until view is visible
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleOutfitsMessage(data);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };

        this.socket.onclose = (event) => {
            console.log('Outfits WebSocket disconnected');
            setTimeout(() => this.connect(), 3000);
        };

        this.socket.onerror = (error) => {
            console.error('Outfits WebSocket error:', error);
        };
    },

    // Only try to get DOM elements when needed
    ensureDomElements() {
        if (!this.outfitsGrid || !this.emptyState) {
            this.outfitsGrid = document.getElementById('outfits-grid');
            this.emptyState = document.getElementById('outfits-empty');
        }
        return !!(this.outfitsGrid && this.emptyState);
    },

    handleOutfitsMessage(data) {
        console.log('Received WebSocket message:', data);

        switch(data.type) {
            case 'outfit_created':
                // Add to cached outfits
                this.cachedOutfits.push(data.outfit);

                // Only try to display if library is currently visible
                if (this.isLibraryVisible) {
                    this.displayOutfits(this.cachedOutfits);
                }

                // Reset the outfit builder
                if (window.outfitBuilder) {
                    window.outfitBuilder.onOutfitCreated();
                }
                break;

            case 'outfits_list':
                // Store the outfits data
                this.cachedOutfits = data.outfits;

                // Only display if library is currently visible
                if (this.isLibraryVisible) {
                    this.displayOutfits(this.cachedOutfits);
                }
                break;

            case 'outfit_deleted':
                // Remove from cached outfits
                this.cachedOutfits = this.cachedOutfits.filter(outfit => outfit.id !== data.outfit_id);

                if (this.isLibraryVisible) {
                    this.removeOutfitFromGrid(data.outfit_id);
                }
                break;

            case 'error':
                console.error('WebSocket error:', data.message);
                alert('Error: ' + data.message);
                if (window.outfitBuilder) {
                    window.outfitBuilder.setSaveButtonState('Save Outfit', false);
                }
                break;
        }
    },

    loadOutfits() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'get_outfits',
                username: this.getUsername()
            }));
        }
    },

    // Call this when library view becomes visible
    showLibrary() {
        this.isLibraryVisible = true;

        // Small delay to ensure DOM is ready
        setTimeout(() => {
            if (this.ensureDomElements()) {
                this.displayOutfits(this.cachedOutfits);
            } else {
                console.log('Library DOM elements still not available, loading outfits...');
                this.loadOutfits();
            }
        }, 100);
    },

    // Call this when leaving library view
    hideLibrary() {
        this.isLibraryVisible = false;
    },

    displayOutfits(outfits) {
        if (!this.ensureDomElements()) {
            console.log('Cannot display outfits - DOM elements not available');
            return;
        }

        console.log('Displaying outfits:', outfits.length);

        if (outfits.length === 0) {
            this.emptyState.style.display = 'block';
            this.outfitsGrid.innerHTML = '';
            return;
        }

        this.emptyState.style.display = 'none';
        this.outfitsGrid.innerHTML = '';

        outfits.forEach(outfit => {
            this.outfitsGrid.appendChild(this.createOutfitCard(outfit));
        });
    },

    createOutfitCard(outfit) {
        const card = document.createElement('div');
        card.className = 'outfit-card';
        card.setAttribute('data-outfit-id', outfit.id);
        card.innerHTML = `
            <div class="outfit-name">${this.escapeHtml(outfit.name)}</div>
            <div class="outfit-items-grid">
                ${outfit.items.map(item => `
                    <img src="${item.image_url}" alt="${this.escapeHtml(item.name)}"
                         title="${this.escapeHtml(item.name)}" class="outfit-item-img">
                `).join('')}
            </div>
            <div class="outfit-actions">
                <button class="btn-edit-outfit" onclick="outfitsManager.editOutfit(${outfit.id})">Edit</button>
                <button class="btn-delete-outfit" onclick="outfitsManager.deleteOutfit(${outfit.id})">Delete</button>
            </div>
        `;
        return card;
    },

    removeOutfitFromGrid(outfitId) {
        if (this.ensureDomElements()) {
            const outfitCard = this.outfitsGrid.querySelector(`[data-outfit-id="${outfitId}"]`);
            if (outfitCard) {
                outfitCard.remove();
            }

            // Show empty state if no outfits left
            const remainingOutfits = this.outfitsGrid.querySelectorAll('.outfit-card');
            if (remainingOutfits.length === 0) {
                this.emptyState.style.display = 'block';
            }
        }
    },

    createOutfit(outfitName, itemIds) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'create_outfit',
                username: this.getUsername(),
                outfit: {
                    name: outfitName,
                    item_ids: itemIds.map(id => parseInt(id))
                }
            }));
            return true;
        } else {
            console.error('WebSocket not connected');
            return false;
        }
    },

    editOutfit(outfitId) {
        alert('Edit outfit ' + outfitId + ' - Feature coming soon!');
    },

    deleteOutfit(outfitId) {
        if (confirm('Are you sure you want to delete this outfit?')) {
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                this.socket.send(JSON.stringify({
                    type: 'delete_outfit',
                    outfit_id: outfitId,
                    username: this.getUsername()
                }));
            }
        }
    },

    getUsername() {
        const script = document.querySelector('script[src*="outfits-manager.js"]');
        return script?.getAttribute('data-username') || '{{ username }}';
    },

    escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    },

    isConnected() {
        return this.socket && this.socket.readyState === WebSocket.OPEN;
    }
};