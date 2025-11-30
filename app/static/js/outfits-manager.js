window.outfitsManager = {
    socket: null,

    connect() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            return;
        }

        this.socket = new WebSocket(`ws://${window.location.host}/ws/outfits`);

        this.socket.onopen = (event) => {
            console.log('Outfits WebSocket connected');
            this.loadOutfits();
        };

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleOutfitsMessage(data);
        };

        this.socket.onclose = (event) => {
            console.log('Outfits WebSocket disconnected');
            setTimeout(() => this.connect(), 3000);
        };

        this.socket.onerror = (error) => {
            console.error('Outfits WebSocket error:', error);
        };
    },

    handleOutfitsMessage(data) {
        console.log('Received WebSocket message:', data);

        switch(data.type) {
            case 'outfit_created':
                this.addOutfitToGrid(data.outfit);
                // Reset the outfit builder when outfit is successfully created
                if (window.outfitBuilder) {
                    window.outfitBuilder.onOutfitCreated();
                }
                break;

            case 'outfits_list':
                this.displayOutfits(data.outfits);
                break;

            case 'error':
                console.error('WebSocket error:', data.message);
                alert('Error: ' + data.message);
                // Reset save button on error
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

    displayOutfits(outfits) {
        const outfitsGrid = document.getElementById('outfits-grid');
        const emptyState = document.getElementById('outfits-empty');

        // Check if elements exist (might not be in current view)
        if (!outfitsGrid || !emptyState) {
            console.log('Outfit library elements not found in current view');
            return;
        }

        if (outfits.length === 0) {
            emptyState.style.display = 'block';
            outfitsGrid.innerHTML = '';
            return;
        }

        emptyState.style.display = 'none';
        outfitsGrid.innerHTML = '';

        outfits.forEach(outfit => {
            outfitsGrid.appendChild(this.createOutfitCard(outfit));
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

    addOutfitToGrid(outfit) {
        const outfitsGrid = document.getElementById('outfits-grid');
        const emptyState = document.getElementById('outfits-empty');

        // Check if elements exist (might not be in current view)
        if (!outfitsGrid || !emptyState) {
            console.log('Cannot add outfit - outfit library not visible');
            return;
        }

        emptyState.style.display = 'none';

        // Check if outfit already exists (for updates)
        const existingCard = outfitsGrid.querySelector(`[data-outfit-id="${outfit.id}"]`);
        if (existingCard) {
            existingCard.replaceWith(this.createOutfitCard(outfit));
        } else {
            outfitsGrid.appendChild(this.createOutfitCard(outfit));
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