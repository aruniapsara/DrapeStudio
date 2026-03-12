/**
 * DrapeStudio — Configure page Alpine.js state
 * Manages all model + scene selections, smart defaults, and sessionStorage persistence.
 */

function configureState() {
    return {

        // ── Accordion open states ─────────────────────────────────────────────
        showAppearance:    true,
        showScene:         true,
        showViewsQuality:  true,
        showAdvanced:      false,

        // ── Model appearance ──────────────────────────────────────────────────
        gender:                 'feminine',
        age_range:              '25-34',
        skin_tone:              'medium',
        body_type:              'average',
        hair_style:             'long_straight',
        hair_color:             'black',
        additional_description: '',

        // ── Scene ─────────────────────────────────────────────────────────────
        environment: 'studio_white',
        pose_preset: 'front_standing',
        framing:     'full_body',

        // ── Advanced ─────────────────────────────────────────────────────────
        lighting:        'auto',
        m_height_cm:     '',
        m_chest_bust_cm: '',
        m_waist_cm:      '',
        m_hips_cm:       '',

        // ── Views & Quality ──────────────────────────────────────────────────
        selected_views:   ['front'],
        selected_quality: '1k',

        // ── From previous step ────────────────────────────────────────────────
        product_type:    'casual',
        model_photo_url: '',
        garment_preview: '',

        // ── Option data ───────────────────────────────────────────────────────
        skinTones: [
            { value: 'very_light', label: 'Very Light', hex: '#FDEBD0' },
            { value: 'light',      label: 'Light',      hex: '#E8C39E' },
            { value: 'medium',     label: 'Medium',     hex: '#C68642' },
            { value: 'dark',       label: 'Dark',       hex: '#8D5524' },
            { value: 'very_dark',  label: 'Very Dark',  hex: '#5C3A1E' },
        ],

        hairColors: [
            { value: 'black',      label: 'Black',    hex: '#1A1A1A' },
            { value: 'dark_brown', label: 'Dk Brown', hex: '#3D1C02' },
            { value: 'brown',      label: 'Brown',    hex: '#6B4F4F' },
            { value: 'auburn',     label: 'Auburn',   hex: '#922724' },
            { value: 'blonde',     label: 'Blonde',   hex: '#D4A017' },
            { value: 'gray',       label: 'Gray',     hex: '#9E9E9E' },
            { value: 'white',      label: 'White',    hex: '#E8E8E8' },
        ],

        hairStyleOptions: {
            feminine: [
                { value: 'long_straight',  label: 'Long Straight', icon: '💇‍♀️' },
                { value: 'long_wavy',      label: 'Long Wavy',     icon: '🌊'  },
                { value: 'medium_layered', label: 'Med Layered',   icon: '✂️'  },
                { value: 'short_bob',      label: 'Short Bob',     icon: '👩'  },
                { value: 'curly',          label: 'Curly',         icon: '🌀'  },
                { value: 'braided',        label: 'Braided',       icon: '🎀'  },
            ],
            masculine: [
                { value: 'short_crop',   label: 'Short Crop',   icon: '💇‍♂️' },
                { value: 'side_part',    label: 'Side Part',    icon: '💈'   },
                { value: 'slicked_back', label: 'Slicked Back', icon: '⬅️'   },
                { value: 'curly_short',  label: 'Curly Short',  icon: '🌀'   },
                { value: 'buzz_cut',     label: 'Buzz Cut',     icon: '⚡'   },
                { value: 'long',         label: 'Long',         icon: '🎸'   },
            ],
            neutral: [
                { value: 'short_straight', label: 'Short',        icon: '✂️' },
                { value: 'medium_length',  label: 'Medium',       icon: '💁' },
                { value: 'long_straight',  label: 'Long Straight',icon: '💇' },
                { value: 'shaved',         label: 'Shaved',       icon: '⚡' },
                { value: 'natural_curly',  label: 'Curly',        icon: '🌀' },
            ],
        },

        viewOptions: [
            { value: 'front', label: 'Front',  icon: '👤' },
            { value: 'side',  label: 'Side',   icon: '🔄' },
            { value: 'back',  label: 'Back',   icon: '🔙' },
        ],

        qualityTiers: [
            { value: '1k', label: 'Standard', resolution: '1024px', description: 'Best for social media',  price_lkr: 40  },
            { value: '2k', label: 'HD',       resolution: '2048px', description: 'Best for online shops', price_lkr: 60  },
            { value: '4k', label: 'Ultra',    resolution: '4096px', description: 'Best for print',        price_lkr: 100 },
        ],

        // ── Computed getters ──────────────────────────────────────────────────

        get currentHairStyles() {
            return this.hairStyleOptions[this.gender] || this.hairStyleOptions.neutral;
        },

        get appearanceSummary() {
            var gMap = { feminine: 'Female', masculine: 'Male', neutral: 'Unisex' };
            return [
                gMap[this.gender]      || this.gender,
                this.age_range,
            ].join(' · ');
        },

        get viewsQualitySummary() {
            var viewNames = this.selected_views.map(function(v) {
                return v.charAt(0).toUpperCase() + v.slice(1);
            });
            var tierMap = { '1k': 'Standard', '2k': 'HD', '4k': 'Ultra' };
            return viewNames.join(', ') + ' · ' + (tierMap[this.selected_quality] || this.selected_quality) + ' · Rs. ' + this.totalCost;
        },

        get currentPricePerImage() {
            var priceMap = { '1k': 40, '2k': 60, '4k': 100 };
            return priceMap[this.selected_quality] || 40;
        },

        get totalCost() {
            return this.selected_views.length * this.currentPricePerImage;
        },

        get sceneSummary() {
            var envMap = {
                studio_white:     'White Studio',
                urban_street:     'Urban Street',
                beach:            'Beach',
                garden:           'Garden',
                indoor_office:    'Office',
                coffee_shop:      'Café',
                traditional_room: 'Traditional Room',
            };
            var poseMap = {
                front_standing: 'Standing',
                casual_walking: 'Walking',
                seated:         'Seated',
                dynamic:        'Dynamic',
            };
            return (envMap[this.environment]   || this.environment)  + ' · ' +
                   (poseMap[this.pose_preset]  || this.pose_preset)  + ' · ' +
                   this.framing.replace('_', ' ');
        },

        // ── Init ──────────────────────────────────────────────────────────────

        init() {
            // Load context from upload step
            this.gender          = sessionStorage.getItem('genderPresentation') || 'feminine';
            this.product_type    = sessionStorage.getItem('productType')         || 'casual';
            this.model_photo_url = sessionStorage.getItem('modelPhotoUrl')       || '';

            var files = [];
            try { files = JSON.parse(sessionStorage.getItem('uploadedFiles') || '[]'); } catch(e) {}
            var raw = files[0] || '';
            this.garment_preview = raw.startsWith('local://') ? '/v1/files/' + raw.replace('local://', '') : raw;

            // Smart defaults based on product type chosen in upload step
            var SMART = {
                saree:   { pose_preset: 'front_standing', environment: 'traditional_room' },
                formal:  { pose_preset: 'front_standing', environment: 'indoor_office'    },
                casual:  { pose_preset: 'casual_walking', environment: 'urban_street'     },
                batik:   { pose_preset: 'front_standing', environment: 'garden'           },
                shalwar: { pose_preset: 'front_standing', environment: 'traditional_room' },
                sarong:  { pose_preset: 'casual_walking', environment: 'beach'            },
            };
            var d = SMART[this.product_type];
            if (d) {
                this.pose_preset = d.pose_preset;
                this.environment = d.environment;
            }

            // Restore previously saved selections (user pressed Back)
            try {
                var saved = sessionStorage.getItem('configureState');
                if (saved) {
                    var s = JSON.parse(saved);
                    var g = this.gender; // gender always comes from upload step
                    Object.assign(this, s);
                    this.gender = g;
                }
            } catch (e) {}

            // Validate hair_style is valid for current gender
            var validStyles = this.currentHairStyles.map(function(s) { return s.value; });
            if (!validStyles.includes(this.hair_style)) {
                this.hair_style = validStyles[0] || '';
            }
        },

        // ── Actions ───────────────────────────────────────────────────────────

        saveAndProceed() {
            // Ensure 'front' is always included
            if (!this.selected_views.includes('front')) {
                this.selected_views.unshift('front');
            }
            sessionStorage.setItem('configureState', JSON.stringify({
                age_range:              this.age_range,
                skin_tone:              this.skin_tone,
                body_type:              this.body_type,
                hair_style:             this.hair_style,
                hair_color:             this.hair_color,
                additional_description: this.additional_description,
                environment:            this.environment,
                pose_preset:            this.pose_preset,
                framing:                this.framing,
                lighting:               this.lighting,
                m_height_cm:            this.m_height_cm,
                m_chest_bust_cm:        this.m_chest_bust_cm,
                m_waist_cm:             this.m_waist_cm,
                m_hips_cm:              this.m_hips_cm,
                selected_views:         this.selected_views,
                selected_quality:       this.selected_quality,
            }));
            document.getElementById('configure-form').submit();
        },
    };
}
