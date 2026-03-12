/**
 * DrapeStudio — Children's module Alpine.js age-adaptive configuration state.
 * Provides reactive filtering of poses, backgrounds, hair options, and expressions
 * based on the selected age group (baby | toddler | kid | teen).
 */

function childrenConfig(initialAgeGroup) {

    const AGE_CONFIG = {
        baby: {
            label: 'Baby', ageRange: '0–2 years', emoji: '👶',
            poses: [
                { id: 'sitting', label: 'Sitting', icon: '🪑' },
                { id: 'lying',   label: 'Lying',   icon: '😴' },
                { id: 'held',    label: 'Held',    icon: '🤱' },
            ],
            backgrounds: [
                { id: 'nursery',       label: 'Nursery',  icon: '🍼' },
                { id: 'soft_blanket',  label: 'Blanket',  icon: '🛏️' },
                { id: 'pastel_studio', label: 'Pastel',   icon: '🎨' },
            ],
            hairOptions: [
                { id: 'none',   label: 'None / Natural', icon: '✨' },
                { id: 'bonnet', label: 'Bonnet',          icon: '🎀' },
                { id: 'cap',    label: 'Cap',             icon: '🧢' },
            ],
            expressions: [
                { id: 'happy',   label: 'Happy',   icon: '😊' },
                { id: 'neutral', label: 'Neutral', icon: '😐' },
            ],
        },

        toddler: {
            label: 'Toddler', ageRange: '2–5 years', emoji: '🧒',
            poses: [
                { id: 'standing', label: 'Standing', icon: '🧍' },
                { id: 'walking',  label: 'Walking',  icon: '🚶' },
                { id: 'playing',  label: 'Playing',  icon: '🎮' },
                { id: 'sitting',  label: 'Sitting',  icon: '🪑' },
            ],
            backgrounds: [
                { id: 'playground',      label: 'Playground', icon: '🛝' },
                { id: 'garden',          label: 'Garden',     icon: '🌿' },
                { id: 'colorful_studio', label: 'Colorful',   icon: '🎨' },
                { id: 'park',            label: 'Park',       icon: '🌳' },
            ],
            hairOptions: [
                { id: 'short',      label: 'Short',      icon: '✂️' },
                { id: 'curly',      label: 'Curly',      icon: '🌀' },
                { id: 'with_bow',   label: 'With Bow',   icon: '🎀' },
                { id: 'with_clips', label: 'With Clips', icon: '📎' },
            ],
            expressions: [
                { id: 'happy',    label: 'Happy',    icon: '😊' },
                { id: 'curious',  label: 'Curious',  icon: '🤔' },
                { id: 'laughing', label: 'Laughing', icon: '😄' },
            ],
        },

        kid: {
            label: 'Kid', ageRange: '6–12 years', emoji: '👧',
            poses: [
                { id: 'standing', label: 'Standing', icon: '🧍' },
                { id: 'casual',   label: 'Casual',   icon: '🚶' },
                { id: 'school',   label: 'School',   icon: '🎒' },
                { id: 'active',   label: 'Active',   icon: '⚡' },
            ],
            backgrounds: [
                { id: 'park',    label: 'Park',    icon: '🌳' },
                { id: 'studio',  label: 'Studio',  icon: '🏛️' },
                { id: 'bedroom', label: 'Bedroom', icon: '🛏️' },
                { id: 'school',  label: 'School',  icon: '🏫' },
            ],
            hairOptions: [
                { id: 'short',    label: 'Short',    icon: '✂️' },
                { id: 'medium',   label: 'Medium',   icon: '💆' },
                { id: 'long',     label: 'Long',     icon: '💇' },
                { id: 'ponytail', label: 'Ponytail', icon: '🐴' },
                { id: 'braids',   label: 'Braids',   icon: '🧶' },
                { id: 'curly',    label: 'Curly',    icon: '🌀' },
            ],
            expressions: [
                { id: 'happy',     label: 'Happy',     icon: '😊' },
                { id: 'confident', label: 'Confident', icon: '😎' },
                { id: 'casual',    label: 'Casual',    icon: '🙂' },
            ],
        },

        teen: {
            label: 'Teen', ageRange: '13–17 years', emoji: '🧑',
            poses: [
                { id: 'fashion_standing', label: 'Fashion', icon: '💃' },
                { id: 'casual',           label: 'Casual',  icon: '🚶' },
                { id: 'urban',            label: 'Urban',   icon: '🏙️' },
                { id: 'seated',           label: 'Seated',  icon: '🪑' },
            ],
            backgrounds: [
                { id: 'urban',   label: 'Urban',   icon: '🏙️' },
                { id: 'studio',  label: 'Studio',  icon: '🏛️' },
                { id: 'campus',  label: 'Campus',  icon: '🏫' },
                { id: 'outdoor', label: 'Outdoor', icon: '🌿' },
                { id: 'beach',   label: 'Beach',   icon: '🏖️' },
            ],
            hairOptions: [
                { id: 'short',    label: 'Short',    icon: '✂️' },
                { id: 'medium',   label: 'Medium',   icon: '💆' },
                { id: 'long',     label: 'Long',     icon: '💇' },
                { id: 'ponytail', label: 'Ponytail', icon: '🐴' },
                { id: 'braids',   label: 'Braids',   icon: '🧶' },
                { id: 'curly',    label: 'Curly',    icon: '🌀' },
                { id: 'trending', label: 'Trending', icon: '✨' },
            ],
            expressions: [
                { id: 'confident', label: 'Confident', icon: '😎' },
                { id: 'casual',    label: 'Casual',    icon: '🙂' },
                { id: 'cool',      label: 'Cool',      icon: '😏' },
            ],
        },
    };

    // Gender-aware hair options loaded from backend config
    var CHILDREN_HAIR = (window.CHILDREN_HAIR_OPTIONS) || {};

    var initial = AGE_CONFIG[initialAgeGroup] || AGE_CONFIG.kid;

    return {
        // ── State ─────────────────────────────────────────────────────────────
        ageGroup:           initialAgeGroup,
        config:             initial,
        childGender:        'girl',
        selectedPose:       initial.poses[0].id,
        selectedBackground: initial.backgrounds[0].id,
        selectedHair:       initial.hairOptions[0].id,
        selectedExpression: initial.expressions[0].id,
        skinTone:           'medium',
        skinTones: [
            { value: 'very_light', label: 'Very Light', hex: '#FDE3CC' },
            { value: 'light',      label: 'Light',      hex: '#F5C9A0' },
            { value: 'medium',     label: 'Medium',     hex: '#D4956A' },
            { value: 'dark',       label: 'Dark',       hex: '#9B6441' },
            { value: 'very_dark',  label: 'Very Dark',  hex: '#4A2C17' },
        ],
        AGE_CONFIG,

        // ── Init: restore childGender from sessionStorage ──────────────────
        initFromSession() {
            var cg = sessionStorage.getItem('childGender');
            if (cg) this.childGender = cg;
            // Validate hair selection against gender-filtered options
            var validHair = this.currentHairOptions.map(function(h) { return h.id; });
            if (!validHair.includes(this.selectedHair)) {
                this.selectedHair = validHair[0] || this.config.hairOptions[0].id;
            }
        },

        // ── Change age group: update config and reset selections ───────────
        changeAgeGroup(newGroup) {
            if (!this.AGE_CONFIG[newGroup]) return;
            this.ageGroup           = newGroup;
            this.config             = this.AGE_CONFIG[newGroup];
            this.selectedPose       = this.config.poses[0].id;
            this.selectedBackground = this.config.backgrounds[0].id;
            var genderHair = this.currentHairOptions;
            this.selectedHair       = genderHair.length > 0 ? genderHair[0].id : this.config.hairOptions[0].id;
            this.selectedExpression = this.config.expressions[0].id;
            // Update URL so back-button preserves the selected age group
            history.replaceState(null, '', '/children/configure?age_group=' + newGroup);
        },

        // ── Navigate to children's review with all params ─────────────────
        saveAndProceed() {
            var params = new URLSearchParams({
                age_group:          this.ageGroup,
                child_gender:       this.childGender,
                skin_tone:          this.skinTone,
                pose_style:         this.selectedPose,
                background_preset:  this.selectedBackground,
                hair_style:         this.selectedHair,
                expression:         this.selectedExpression,
            });
            window.location.href = '/children/review?' + params.toString();
        },

        // ── Summary for display ───────────────────────────────────────────
        get currentHairOptions() {
            var ageHair = CHILDREN_HAIR[this.ageGroup];
            if (!ageHair) return this.config.hairOptions;  // fallback to hardcoded
            var opts = ageHair[this.childGender] || ageHair['unisex'] || this.config.hairOptions;
            return opts.map(function(o) { return { id: o.id, label: o.label ? o.label.en : o.id, icon: o.icon || '' }; });
        },

        get summary() {
            var pose = this.config.poses.find(function(p) { return p.id === this.selectedPose; }.bind(this));
            var bg   = this.config.backgrounds.find(function(b) { return b.id === this.selectedBackground; }.bind(this));
            return (pose ? pose.label : '') + ' · ' + (bg ? bg.label : '');
        },
    };
}
