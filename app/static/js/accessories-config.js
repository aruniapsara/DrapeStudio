/**
 * DrapeStudio — Accessories configure page
 * Alpine.js reactive data factory for the accessories configuration step.
 */

function accessoriesConfig(initialCategory) {
    return {
        category:          initialCategory || 'necklace',
        displayMode:       'on_model',
        skinTone:          'medium',
        backgroundSurface: 'white_marble',
        contextScene:      'garden',

        skinTones: [
            { value: 'very_light', label: 'Very Light', hex: '#FAE7D3' },
            { value: 'light',      label: 'Light',      hex: '#E8C8A0' },
            { value: 'medium',     label: 'Medium',     hex: '#C68642' },
            { value: 'dark',       label: 'Dark',       hex: '#8D5524' },
            { value: 'very_dark',  label: 'Very Dark',  hex: '#4A2912' },
        ],

        surfaces: [
            { value: 'white_marble',  label: 'White Marble',  icon: '⬜' },
            { value: 'wooden_table',  label: 'Wooden Table',  icon: '🪵' },
            { value: 'velvet_fabric', label: 'Velvet Fabric', icon: '🟣' },
            { value: 'linen_cloth',   label: 'Linen Cloth',   icon: '🟤' },
            { value: 'concrete',      label: 'Concrete',      icon: '🔘' },
            { value: 'rose_petals',   label: 'Rose Petals',   icon: '🌹' },
        ],

        scenes: [
            { value: 'cafe',         label: 'Café',         icon: '☕' },
            { value: 'garden',       label: 'Garden',       icon: '🌿' },
            { value: 'beach',        label: 'Beach',        icon: '🏖️' },
            { value: 'urban_street', label: 'Urban Street', icon: '🏙️' },
            { value: 'cozy_room',    label: 'Cozy Room',    icon: '🛋️' },
            { value: 'office',       label: 'Office',       icon: '💼' },
        ],

        /**
         * Restore category from sessionStorage if navigating back.
         */
        initFromSession() {
            var savedCategory = sessionStorage.getItem('accessoryCategory');
            if (savedCategory) {
                this.category = savedCategory;
            }
        },

        /**
         * Navigate to a different category tab (updates URL via redirect).
         */
        changeCategory(newCategory) {
            this.category = newCategory;
            sessionStorage.setItem('accessoryCategory', newCategory);
            window.location.href = '/accessories/configure?category=' + newCategory;
        },

        /**
         * Build review URL params and navigate to /accessories/review.
         */
        saveAndProceed() {
            var params = new URLSearchParams({
                accessory_category: this.category,
                display_mode:       this.displayMode,
            });

            if (this.displayMode === 'on_model') {
                params.set('model_skin_tone', this.skinTone);
            } else if (this.displayMode === 'flat_lay') {
                params.set('background_surface', this.backgroundSurface);
            } else if (this.displayMode === 'lifestyle') {
                params.set('context_scene', this.contextScene);
            }

            window.location.href = '/accessories/review?' + params.toString();
        },
    };
}
