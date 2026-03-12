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
        accessorySize:     '',
        sizeOptions:       [],

        skinTones: [
            { value: 'very_light', label: 'Very Light', hex: '#FAE7D3' },
            { value: 'light',      label: 'Light',      hex: '#E8C8A0' },
            { value: 'medium',     label: 'Medium',     hex: '#C68642' },
            { value: 'dark',       label: 'Dark',       hex: '#8D5524' },
            { value: 'very_dark',  label: 'Very Dark',  hex: '#4A2912' },
        ],

        surfaces: [
            { value: 'white_marble',  label: 'White Marble',  icon: '\u2B1C' },
            { value: 'wooden_table',  label: 'Wooden Table',  icon: '\uD83E\uDEB5' },
            { value: 'velvet_fabric', label: 'Velvet Fabric', icon: '\uD83D\uDFE3' },
            { value: 'linen_cloth',   label: 'Linen Cloth',   icon: '\uD83D\uDFE4' },
            { value: 'concrete',      label: 'Concrete',      icon: '\uD83D\uDD18' },
            { value: 'rose_petals',   label: 'Rose Petals',   icon: '\uD83C\uDF39' },
        ],

        scenes: [
            { value: 'cafe',         label: 'Cafe',         icon: '\u2615' },
            { value: 'garden',       label: 'Garden',       icon: '\uD83C\uDF3F' },
            { value: 'beach',        label: 'Beach',        icon: '\uD83C\uDFD6\uFE0F' },
            { value: 'urban_street', label: 'Urban Street', icon: '\uD83C\uDFD9\uFE0F' },
            { value: 'cozy_room',    label: 'Cozy Room',    icon: '\uD83D\uDECB\uFE0F' },
            { value: 'office',       label: 'Office',       icon: '\uD83D\uDCBC' },
        ],

        // Size options per accessory category
        sizeLookup: {
            necklace: [
                { value: 'choker',  label: 'Choker (tight)' },
                { value: 'short',   label: 'Short (collar-bone)' },
                { value: 'medium',  label: 'Medium (chest)' },
                { value: 'long',    label: 'Long (below chest)' },
            ],
            earrings: [
                { value: 'stud',    label: 'Stud (small)' },
                { value: 'drop',    label: 'Drop (medium)' },
                { value: 'dangle',  label: 'Dangle (long)' },
                { value: 'hoop',    label: 'Hoop' },
            ],
            bracelet: [
                { value: 'thin',    label: 'Thin / Delicate' },
                { value: 'medium',  label: 'Medium' },
                { value: 'wide',    label: 'Wide / Cuff' },
            ],
            ring: [
                { value: 'thin_band',  label: 'Thin Band' },
                { value: 'statement',  label: 'Statement (large)' },
            ],
            handbag: [
                { value: 'clutch',  label: 'Clutch (small)' },
                { value: 'small',   label: 'Small' },
                { value: 'medium',  label: 'Medium' },
                { value: 'large',   label: 'Large / Tote' },
            ],
            hat: [
                { value: 'fitted',     label: 'Fitted / Cap' },
                { value: 'wide_brim',  label: 'Wide Brim' },
            ],
            scarf: [
                { value: 'small',   label: 'Small / Neck scarf' },
                { value: 'medium',  label: 'Medium' },
                { value: 'large',   label: 'Large / Shawl' },
            ],
            crochet: [
                { value: 'small',   label: 'Small item' },
                { value: 'medium',  label: 'Medium item' },
                { value: 'large',   label: 'Large item' },
            ],
            hair_accessory: [
                { value: 'tiny',    label: 'Tiny (pin/clip)' },
                { value: 'small',   label: 'Small (bow/band)' },
                { value: 'large',   label: 'Large (headpiece)' },
            ],
        },

        /**
         * Update sizeOptions based on current category.
         */
        updateSizeOptions() {
            this.sizeOptions = this.sizeLookup[this.category] || [];
            if (this.sizeOptions.length > 0) {
                this.accessorySize = this.sizeOptions[0].value;
            } else {
                this.accessorySize = '';
            }
        },

        /**
         * Restore category from sessionStorage if navigating back.
         */
        initFromSession() {
            var savedCategory = sessionStorage.getItem('accessoryCategory');
            if (savedCategory) {
                this.category = savedCategory;
            }
            this.updateSizeOptions();
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

            if (this.accessorySize) {
                params.set('accessory_size', this.accessorySize);
            }

            window.location.href = '/accessories/review?' + params.toString();
        },
    };
}
