window.wardrobeFilter = {
    initialize() {
        document.getElementById('category-filter').addEventListener('change', this.filterItems.bind(this));
        document.getElementById('search-filter').addEventListener('input', this.filterItems.bind(this));
        this.filterItems(); // Initial filter
    },

    filterItems() {
        const categoryFilter = document.getElementById('category-filter').value;
        const searchFilter = document.getElementById('search-filter').value.toLowerCase();
        const items = document.querySelectorAll('.wardrobe-item');

        items.forEach(item => {
            const category = item.getAttribute('data-category');
            const name = item.getAttribute('data-name');

            const categoryMatch = categoryFilter === 'all' || category === categoryFilter;
            const searchMatch = name.includes(searchFilter);

            if (categoryMatch && searchMatch) {
                item.parentElement.style.display = 'block';
            } else {
                item.parentElement.style.display = 'none';
            }
        });
    }
};