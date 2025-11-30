// View management and basic UI functionality
function showView(viewName) {
    document.querySelectorAll('.view').forEach(view => {
        view.classList.remove('active');
    });
    document.getElementById(viewName + '-view').classList.add('active');
}

// In app/static/js/app.js - update the showOutfitLibrary function
function showOutfitLibrary() {
    showView('outfit-library');

    if (window.outfitsManager) {
        if (!window.outfitsManager.isConnected()) {
            window.outfitsManager.connect();
        }
        // Tell outfits manager that library is now visible
        window.outfitsManager.showLibrary();
    }
}

function showWardrobe() {
    showView('wardrobe');
    if (window.outfitsManager) {
        window.outfitsManager.hideLibrary();
    }
}

function showOutfitBuilder() {
    showView('outfit-builder');
    if (window.outfitsManager) {
        window.outfitsManager.hideLibrary();
    }
    if (window.outfitBuilder) {
        window.outfitBuilder.reset();
        window.outfitBuilder.initializeDragAndDrop();
    }
}

function showRecommendations() {
    alert('Personal Recommendations feature coming soon!');
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing app modules...');

    // Initialize all modules
    if (window.wardrobeFilter) {
        window.wardrobeFilter.initialize();
    }

    // Connect WebSocket for outfits
    if (window.outfitsManager) {
        window.outfitsManager.connect();
    }

    if (window.outfitBuilder) {
        window.outfitBuilder.initialize();
    }

    console.log('App initialized successfully');
});