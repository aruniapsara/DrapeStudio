# Gender-Aware Style Options Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make all style/appearance options (body type, hair style, pose, build) gender-aware across adult, children, and fit-on modules.

**Architecture:** Centralized Python config (`app/config/gender_options.py`) as single source of truth, injected into templates as JSON via Jinja2 context, filtered reactively with Alpine.js computed getters. Prompt assembly uses a description mapping to produce gender-appropriate terms.

**Tech Stack:** Python 3.12, FastAPI, Jinja2, Alpine.js, YAML prompt templates

**Spec:** `docs/superpowers/specs/2026-03-12-gender-aware-options-design.md`

---

## Chunk 1: Centralized Config + Adult Module

### Task 1: Create `app/config/gender_options.py`

**Files:**
- Create: `app/config/gender_options.py`

- [ ] **Step 1: Create the gender options config file**

Create `app/config/gender_options.py` with all option maps. Each option has `id`, multilingual `label` dict (en/si/ta), and `icon`.

```python
"""
Gender-aware option definitions for all DrapeStudio modules.

Single source of truth for body types, hair styles, poses, and build options
filtered by gender. Injected into templates as JSON via Jinja2 context.

Gender key mapping (preserves existing values — no migration):
  Adult:    feminine / masculine / neutral   (sessionStorage genderPresentation)
  Children: girl / boy / unisex              (sessionStorage childGender)
  Fit-on:   female / male                    (Alpine state customerGender)
"""

# ── Adult: Body Types ─────────────────────────────────────────────────────────

BODY_TYPES = {
    "feminine": [
        {"id": "slim",      "label": {"en": "Slim",      "si": "සිහින්",    "ta": "மெலிந்த"},      "icon": "🧍"},
        {"id": "average",   "label": {"en": "Average",   "si": "සාමාන්‍ය",  "ta": "சராசரி"},       "icon": "🚶"},
        {"id": "curvy",     "label": {"en": "Curvy",     "si": "වක්‍ර",      "ta": "வளைவான"},      "icon": "💃"},
        {"id": "plus_size", "label": {"en": "Plus Size", "si": "විශාල",     "ta": "பெரிய அளவு"}, "icon": "🤸"},
    ],
    "masculine": [
        {"id": "slim",     "label": {"en": "Slim",        "si": "සිහින්",       "ta": "மெலிந்த"},    "icon": "🧍"},
        {"id": "average",  "label": {"en": "Average",     "si": "සාමාන්‍ය",     "ta": "சராசரி"},     "icon": "🚶"},
        {"id": "athletic", "label": {"en": "Athletic",    "si": "ක්‍රීඩාශීලී",  "ta": "தடகள"},       "icon": "🏋️"},
        {"id": "heavy",    "label": {"en": "Heavy Build", "si": "බර සිරුර",     "ta": "கனமான உடல்"}, "icon": "🏃"},
    ],
    "neutral": [
        {"id": "slim",      "label": {"en": "Slim",      "si": "සිහින්",       "ta": "மெலிந்த"},      "icon": "🧍"},
        {"id": "average",   "label": {"en": "Average",   "si": "සාමාන්‍ය",     "ta": "சராசரி"},       "icon": "🚶"},
        {"id": "athletic",  "label": {"en": "Athletic",  "si": "ක්‍රීඩාශීලී",  "ta": "தடகள"},         "icon": "🏋️"},
        {"id": "plus_size", "label": {"en": "Plus Size", "si": "විශාල",        "ta": "பெரிய அளவு"},  "icon": "🤸"},
    ],
}

# ── Adult: Hair Styles ────────────────────────────────────────────────────────

HAIR_STYLES = {
    "feminine": [
        {"id": "long_straight",  "label": {"en": "Long Straight", "si": "දිගු සෘජු",    "ta": "நீண்ட நேரான"},   "icon": "💇‍♀️"},
        {"id": "long_wavy",      "label": {"en": "Long Wavy",     "si": "දිගු රැළි",     "ta": "நீண்ட அலை"},     "icon": "🌊"},
        {"id": "medium_layered", "label": {"en": "Med Layered",   "si": "මධ්‍යම ස්ථර",   "ta": "நடுத்தர அடுக்கு"},"icon": "✂️"},
        {"id": "short_bob",      "label": {"en": "Short Bob",     "si": "කෙටි බොබ්",     "ta": "குறுகிய பாப்"},   "icon": "👩"},
        {"id": "curly",          "label": {"en": "Curly",         "si": "රැලි සහිත",     "ta": "சுருட்டை"},       "icon": "🌀"},
        {"id": "braided",        "label": {"en": "Braided",       "si": "ගෙතූ",          "ta": "பின்னல்"},        "icon": "🎀"},
        {"id": "bun",            "label": {"en": "Bun/Updo",      "si": "කොණ්ඩය",        "ta": "முடிச்சு"},       "icon": "💆‍♀️"},
    ],
    "masculine": [
        {"id": "short_crop",   "label": {"en": "Short Crop",   "si": "කෙටි කපා",    "ta": "குறுகிய வெட்டு"},          "icon": "💇‍♂️"},
        {"id": "side_part",    "label": {"en": "Side Part",    "si": "මධ්‍යම පැත්ත", "ta": "நடுத்தர பக்க"},            "icon": "💈"},
        {"id": "slicked_back", "label": {"en": "Slicked Back", "si": "පිටුපසට",      "ta": "பின்னால் வழுவழுப்பான"},    "icon": "⬅️"},
        {"id": "curly_short",  "label": {"en": "Curly Short",  "si": "රැලි කෙටි",    "ta": "சுருட்டை குறுகிய"},         "icon": "🌀"},
        {"id": "buzz_cut",     "label": {"en": "Buzz Cut",     "si": "බස් කට්",      "ta": "பஸ் கட்"},                 "icon": "⚡"},
        {"id": "long",         "label": {"en": "Long",         "si": "දිගු",          "ta": "நீண்ட"},                   "icon": "🎸"},
    ],
    "neutral": [
        {"id": "short_straight", "label": {"en": "Short",         "si": "කෙටි",          "ta": "குறுகிய"},     "icon": "✂️"},
        {"id": "medium_length",  "label": {"en": "Medium",        "si": "මධ්‍යම",         "ta": "நடுத்தர"},     "icon": "💁"},
        {"id": "long_straight",  "label": {"en": "Long Straight", "si": "දිගු සෘජු",     "ta": "நீண்ட நேரான"}, "icon": "💇"},
        {"id": "shaved",         "label": {"en": "Shaved",        "si": "බෝවූ",          "ta": "மொட்டை"},      "icon": "⚡"},
        {"id": "natural_curly",  "label": {"en": "Curly",         "si": "රැලි සහිත",     "ta": "சுருட்டை"},    "icon": "🌀"},
    ],
}

# ── Adult: Poses ──────────────────────────────────────────────────────────────

POSES = {
    "feminine": [
        {"id": "fashion_standing", "label": {"en": "Fashion Stand",  "si": "විලාසිතා ඉරියව්ව", "ta": "பேஷன் நிற்பது"}, "icon": "💃"},
        {"id": "casual_walking",   "label": {"en": "Casual Walk",    "si": "සාමාන්‍ය ඇවිදීම",   "ta": "சாதாரண நடை"},    "icon": "🚶‍♀️"},
        {"id": "seated_elegant",   "label": {"en": "Seated Elegant", "si": "අලංකාර වාඩිව",      "ta": "நேர்த்தியான அமர்வு"}, "icon": "🪑"},
        {"id": "hand_on_hip",      "label": {"en": "Hand on Hip",    "si": "ඉණ මත අත",          "ta": "இடுப்பில் கை"},  "icon": "🤳"},
    ],
    "masculine": [
        {"id": "standing_confident", "label": {"en": "Confident Stand",  "si": "විශ්වාසී ඉරියව්ව",   "ta": "நம்பிக்கையான நிற்பது"}, "icon": "🧍‍♂️"},
        {"id": "casual_walking",     "label": {"en": "Casual Walk",      "si": "සාමාන්‍ය ඇවිදීම",     "ta": "சாதாரண நடை"},          "icon": "🚶‍♂️"},
        {"id": "hands_in_pockets",   "label": {"en": "Hands in Pockets", "si": "සාක්කුවල අත්",        "ta": "சட்டைப் பையில் கைகள்"}, "icon": "🧑"},
        {"id": "seated_casual",      "label": {"en": "Seated Casual",    "si": "සාමාන්‍ය වාඩිව",      "ta": "சாதாரண அமர்வு"},       "icon": "🪑"},
    ],
    "neutral": [
        {"id": "front_standing", "label": {"en": "Fashion Stand", "si": "විලාසිතා ඉරියව්ව", "ta": "பேஷன் நிற்பது"}, "icon": "🧍"},
        {"id": "casual_walking", "label": {"en": "Casual Walk",   "si": "සාමාන්‍ය ඇවිදීම",   "ta": "சாதாரண நடை"},    "icon": "🚶"},
        {"id": "seated",         "label": {"en": "Seated",        "si": "වාඩිව",             "ta": "அமர்வு"},        "icon": "🪑"},
        {"id": "dynamic",        "label": {"en": "Dynamic",       "si": "ගතික",               "ta": "டைனமிக்"},      "icon": "💃"},
    ],
}

# ── Fit-on: Build ─────────────────────────────────────────────────────────────
# NOTE: uses hyphenated "plus-size" to match existing fiton buildToMeasurements

FITON_BUILD = {
    "female": [
        {"id": "slim",      "label": {"en": "Slim",      "si": "සිහින්",    "ta": "மெலிந்த"},      "desc": {"en": "Smaller frame",   "si": "කුඩා රාමුව",    "ta": "சிறிய உடல்"}},
        {"id": "medium",    "label": {"en": "Medium",    "si": "මධ්‍යම",     "ta": "நடுத்தர"},      "desc": {"en": "Average frame",   "si": "සාමාන්‍ය රාමුව", "ta": "சராசரி உடல்"}},
        {"id": "curvy",     "label": {"en": "Curvy",     "si": "වක්‍ර",      "ta": "வளைவான"},      "desc": {"en": "Fuller hips/bust","si": "පිරුණු ඉණ/ළය",   "ta": "நிரம்பிய இடுப்பு"}},
        {"id": "plus-size", "label": {"en": "Plus Size", "si": "විශාල",     "ta": "பெரிய அளவு"}, "desc": {"en": "Larger frame",    "si": "විශාල රාමුව",    "ta": "பெரிய உடல்"}},
    ],
    "male": [
        {"id": "slim",     "label": {"en": "Slim",        "si": "සිහින්",       "ta": "மெலிந்த"},      "desc": {"en": "Lean frame",      "si": "සිහින් රාමුව",    "ta": "மெல்லிய உடல்"}},
        {"id": "medium",   "label": {"en": "Medium",      "si": "මධ්‍යම",        "ta": "நடுத்தர"},      "desc": {"en": "Average frame",   "si": "සාමාන්‍ය රාමුව",  "ta": "சராசரி உடல்"}},
        {"id": "athletic", "label": {"en": "Athletic",    "si": "ක්‍රීඩාශීලී",  "ta": "தடகள"},         "desc": {"en": "Muscular frame",  "si": "මාංශ පේශි රාමුව", "ta": "தசை உடல்"}},
        {"id": "heavy",    "label": {"en": "Heavy Build", "si": "බර සිරුර",     "ta": "கனமான உடல்"},  "desc": {"en": "Broad frame",     "si": "පළල් රාමුව",     "ta": "அகலமான உடல்"}},
    ],
}

# ── Children: Hair (age × gender) ────────────────────────────────────────────
# Baby hair is gender-neutral (bonnet/cap/none); older ages are gender-filtered.

CHILDREN_HAIR = {
    "baby": {
        "girl":   [{"id": "none", "label": {"en": "None / Natural", "si": "ස්වාභාවික", "ta": "இயற்கை"}, "icon": "✨"},
                   {"id": "bonnet", "label": {"en": "Bonnet", "si": "බොනට්",  "ta": "தொப்பி"}, "icon": "🎀"},
                   {"id": "cap",    "label": {"en": "Cap",    "si": "තොප්පිය", "ta": "தொப்பி"}, "icon": "🧢"}],
        "boy":    [{"id": "none", "label": {"en": "None / Natural", "si": "ස්වාභාවික", "ta": "இயற்கை"}, "icon": "✨"},
                   {"id": "bonnet", "label": {"en": "Bonnet", "si": "බොනට්",  "ta": "தொப்பி"}, "icon": "🎀"},
                   {"id": "cap",    "label": {"en": "Cap",    "si": "තොප්පිය", "ta": "தொப்பி"}, "icon": "🧢"}],
        "unisex": [{"id": "none", "label": {"en": "None / Natural", "si": "ස්වාභාවික", "ta": "இயற்கை"}, "icon": "✨"},
                   {"id": "bonnet", "label": {"en": "Bonnet", "si": "බොනට්",  "ta": "தொப்பி"}, "icon": "🎀"},
                   {"id": "cap",    "label": {"en": "Cap",    "si": "තොප්පිය", "ta": "தொப்பி"}, "icon": "🧢"}],
    },
    "toddler": {
        "girl":   [{"id": "short",      "label": {"en": "Short",      "si": "කෙටි",       "ta": "குறுகிய"},  "icon": "✂️"},
                   {"id": "curly",      "label": {"en": "Curly",      "si": "රැලි සහිත",  "ta": "சுருட்டை"}, "icon": "🌀"},
                   {"id": "with_bow",   "label": {"en": "With Bow",   "si": "පීති සහිත",  "ta": "வில்லுடன்"}, "icon": "🎀"},
                   {"id": "with_clips", "label": {"en": "With Clips", "si": "ක්ලිප් සහිත","ta": "கிளிப்களுடன்"}, "icon": "📎"}],
        "boy":    [{"id": "short",      "label": {"en": "Short",      "si": "කෙටි",       "ta": "குறுகிய"},  "icon": "✂️"},
                   {"id": "curly",      "label": {"en": "Curly",      "si": "රැලි සහිත",  "ta": "சுருட்டை"}, "icon": "🌀"}],
        "unisex": [{"id": "short",      "label": {"en": "Short",      "si": "කෙටි",       "ta": "குறுகிய"},  "icon": "✂️"},
                   {"id": "curly",      "label": {"en": "Curly",      "si": "රැලි සහිත",  "ta": "சுருட்டை"}, "icon": "🌀"},
                   {"id": "with_bow",   "label": {"en": "With Bow",   "si": "පීති සහිත",  "ta": "வில்லுடன்"}, "icon": "🎀"},
                   {"id": "with_clips", "label": {"en": "With Clips", "si": "ක්ලිප් සහිත","ta": "கிளிப்களுடன்"}, "icon": "📎"}],
    },
    "kid": {
        "girl":   [{"id": "short",    "label": {"en": "Short",    "si": "කෙටි",       "ta": "குறுகிய"},  "icon": "✂️"},
                   {"id": "medium",   "label": {"en": "Medium",   "si": "මධ්‍යම",      "ta": "நடுத்தர"},  "icon": "💆"},
                   {"id": "long",     "label": {"en": "Long",     "si": "දිගු",        "ta": "நீண்ட"},    "icon": "💇"},
                   {"id": "ponytail", "label": {"en": "Ponytail", "si": "පෝනිටේල්",   "ta": "போனிடெயில்"}, "icon": "🐴"},
                   {"id": "braids",   "label": {"en": "Braids",   "si": "ගෙතූ",        "ta": "பின்னல்"},  "icon": "🧶"},
                   {"id": "curly",    "label": {"en": "Curly",    "si": "රැලි සහිත",   "ta": "சுருட்டை"}, "icon": "🌀"}],
        "boy":    [{"id": "short",      "label": {"en": "Short",      "si": "කෙටි",       "ta": "குறுகிய"},       "icon": "✂️"},
                   {"id": "buzz",       "label": {"en": "Buzz Cut",   "si": "බස් කට්",    "ta": "பஸ் கட்"},       "icon": "⚡"},
                   {"id": "curly",      "label": {"en": "Curly",      "si": "රැලි සහිත",  "ta": "சுருட்டை"},      "icon": "🌀"},
                   {"id": "side_part",  "label": {"en": "Side Part",  "si": "පැත්ත කොටස","ta": "பக்க வகுப்பு"},  "icon": "💈"}],
        "unisex": [{"id": "short",    "label": {"en": "Short",    "si": "කෙටි",       "ta": "குறுகிய"},  "icon": "✂️"},
                   {"id": "medium",   "label": {"en": "Medium",   "si": "මධ්‍යම",      "ta": "நடுத்தர"},  "icon": "💆"},
                   {"id": "long",     "label": {"en": "Long",     "si": "දිගු",        "ta": "நீண்ட"},    "icon": "💇"},
                   {"id": "ponytail", "label": {"en": "Ponytail", "si": "පෝනිටේල්",   "ta": "போனிடெயில்"}, "icon": "🐴"},
                   {"id": "braids",   "label": {"en": "Braids",   "si": "ගෙතූ",        "ta": "பின்னல்"},  "icon": "🧶"},
                   {"id": "curly",    "label": {"en": "Curly",    "si": "රැලි සහිත",   "ta": "சுருட்டை"}, "icon": "🌀"}],
    },
    "teen": {
        "girl":   [{"id": "short",    "label": {"en": "Short",    "si": "කෙටි",       "ta": "குறுகிய"},       "icon": "✂️"},
                   {"id": "medium",   "label": {"en": "Medium",   "si": "මධ්‍යම",      "ta": "நடுத்தர"},      "icon": "💆"},
                   {"id": "long",     "label": {"en": "Long",     "si": "දිගු",        "ta": "நீண்ட"},        "icon": "💇"},
                   {"id": "ponytail", "label": {"en": "Ponytail", "si": "පෝනිටේල්",   "ta": "போனிடெயில்"},   "icon": "🐴"},
                   {"id": "braids",   "label": {"en": "Braids",   "si": "ගෙතූ",        "ta": "பின்னல்"},     "icon": "🧶"},
                   {"id": "curly",    "label": {"en": "Curly",    "si": "රැලි සහිත",   "ta": "சுருட்டை"},    "icon": "🌀"},
                   {"id": "trending", "label": {"en": "Trending", "si": "ජනප්‍රිය",    "ta": "டிரெண்டிங்"},  "icon": "✨"}],
        "boy":    [{"id": "short",      "label": {"en": "Short",      "si": "කෙටි",       "ta": "குறுகிய"},       "icon": "✂️"},
                   {"id": "buzz",       "label": {"en": "Buzz Cut",   "si": "බස් කට්",    "ta": "பஸ் கட்"},       "icon": "⚡"},
                   {"id": "curly",      "label": {"en": "Curly",      "si": "රැලි සහිත",  "ta": "சுருட்டை"},      "icon": "🌀"},
                   {"id": "side_part",  "label": {"en": "Side Part",  "si": "පැත්ත කොටස","ta": "பக்க வகுப்பு"},  "icon": "💈"},
                   {"id": "trending",   "label": {"en": "Trending",   "si": "ජනප්‍රිය",   "ta": "டிரெண்டிங்"},   "icon": "✨"}],
        "unisex": [{"id": "short",    "label": {"en": "Short",    "si": "කෙටි",       "ta": "குறுகிய"},       "icon": "✂️"},
                   {"id": "medium",   "label": {"en": "Medium",   "si": "මධ්‍යම",      "ta": "நடுத்தர"},      "icon": "💆"},
                   {"id": "long",     "label": {"en": "Long",     "si": "දිගු",        "ta": "நீண்ட"},        "icon": "💇"},
                   {"id": "ponytail", "label": {"en": "Ponytail", "si": "පෝනිටේල්",   "ta": "போனிடெயில்"},   "icon": "🐴"},
                   {"id": "braids",   "label": {"en": "Braids",   "si": "ගෙතූ",        "ta": "பின்னல்"},     "icon": "🧶"},
                   {"id": "curly",    "label": {"en": "Curly",    "si": "රැලි සහිත",   "ta": "சுருட்டை"},    "icon": "🌀"},
                   {"id": "trending", "label": {"en": "Trending", "si": "ජනප්‍රිය",    "ta": "டிரெண்டிங்"},  "icon": "✨"}],
    },
}


def get_adult_options_json() -> str:
    """Return JSON string with BODY_TYPES, HAIR_STYLES, POSES for adult configure page."""
    import json
    return json.dumps({
        "BODY_TYPES": BODY_TYPES,
        "HAIR_STYLES": HAIR_STYLES,
        "POSES": POSES,
    }, ensure_ascii=False)


def get_children_hair_json() -> str:
    """Return JSON string with CHILDREN_HAIR for children configure page."""
    import json
    return json.dumps(CHILDREN_HAIR, ensure_ascii=False)


def get_fiton_build_json() -> str:
    """Return JSON string with FITON_BUILD for fiton customer details page."""
    import json
    return json.dumps(FITON_BUILD, ensure_ascii=False)
```

- [ ] **Step 2: Commit**

```bash
git add app/config/gender_options.py
git commit -m "feat: add centralized gender-aware options config"
```

---

### Task 2: Update adult `configure.js` — add body type + pose getters

**Files:**
- Modify: `app/static/js/configure.js`

- [ ] **Step 1: Replace hardcoded hairStyleOptions and add body type / pose options from injected config**

In `configure.js`, replace the entire `hairStyleOptions` block (lines 64-88) and add body type + pose option maps. Also add the three computed getters and update `sceneSummary`.

Replace lines 64-88 (the hardcoded `hairStyleOptions` object) with:

```javascript
        // Gender-aware options loaded from backend config
        hairStyleOptions:  (window.GENDER_OPTIONS && window.GENDER_OPTIONS.HAIR_STYLES) || {},
        bodyTypeOptions:   (window.GENDER_OPTIONS && window.GENDER_OPTIONS.BODY_TYPES)  || {},
        poseOptions:       (window.GENDER_OPTIONS && window.GENDER_OPTIONS.POSES)       || {},
```

- [ ] **Step 2: Add computed getters for body types and poses**

After the existing `currentHairStyles` getter (line 104-106), add:

```javascript
        get currentBodyTypes() {
            var opts = this.bodyTypeOptions[this.gender] || this.bodyTypeOptions.neutral || [];
            return opts.map(function(o) { return { value: o.id, label: o.label.en, icon: o.icon }; });
        },

        get currentPoses() {
            var opts = this.poseOptions[this.gender] || this.poseOptions.neutral || [];
            return opts.map(function(o) { return { value: o.id, label: o.label.en, icon: o.icon }; });
        },

        get measurementLabel() {
            return this.gender === 'masculine' ? 'Chest (cm)' : this.gender === 'feminine' ? 'Bust (cm)' : 'Chest / Bust (cm)';
        },
```

Also update `currentHairStyles` getter to use the same `.map()` transform:

```javascript
        get currentHairStyles() {
            var opts = this.hairStyleOptions[this.gender] || this.hairStyleOptions.neutral || [];
            return opts.map(function(o) { return { value: o.id, label: o.label.en, icon: o.icon }; });
        },
```

- [ ] **Step 3: Update `sceneSummary` poseMap (lines 143-148)**

Replace the existing `poseMap` in `sceneSummary` getter with an expanded version:

```javascript
            var poseMap = {
                front_standing:     'Standing',
                casual_walking:     'Walking',
                seated:             'Seated',
                dynamic:            'Dynamic',
                fashion_standing:   'Fashion Stand',
                seated_elegant:     'Seated Elegant',
                hand_on_hip:        'Hand on Hip',
                standing_confident: 'Confident Stand',
                hands_in_pockets:   'Hands in Pockets',
                seated_casual:      'Seated Casual',
            };
```

- [ ] **Step 4: Add validation in `init()` for body_type and pose_preset**

After the existing hair_style validation (lines 193-197), add:

```javascript
            // Validate body_type is valid for current gender
            var validBodyTypes = this.currentBodyTypes.map(function(b) { return b.value; });
            if (!validBodyTypes.includes(this.body_type)) {
                this.body_type = validBodyTypes[0] || 'average';
            }

            // Validate pose_preset is valid for current gender
            var validPoses = this.currentPoses.map(function(p) { return p.value; });
            if (!validPoses.includes(this.pose_preset)) {
                this.pose_preset = validPoses[0] || 'front_standing';
            }
```

- [ ] **Step 5: Commit**

```bash
git add app/static/js/configure.js
git commit -m "feat: add gender-aware body type, pose, hair getters to configure.js"
```

---

### Task 3: Update adult `configure.html` — dynamic body types + poses

**Files:**
- Modify: `app/templates/configure.html`

- [ ] **Step 1: Inject GENDER_OPTIONS JSON before the configure.js script tag**

At the bottom of the file, in the `{% block scripts %}` block (line 554-556), add the JSON injection BEFORE the configure.js include:

```html
{% block scripts %}
<script>
  window.GENDER_OPTIONS = {{ gender_options_json | safe }};
</script>
<script src="/static/js/configure.js"></script>
{% endblock %}
```

- [ ] **Step 2: Remove hardcoded body_types set (lines 16-21)**

Delete these lines:

```
{% set body_types = [
    {"value": "slim",     "label": "Slim",    "icon": "🧍"},
    {"value": "average",  "label": "Average", "icon": "🚶"},
    {"value": "athletic", "label": "Athletic","icon": "🏃"},
    {"value": "plus",     "label": "Plus",    "icon": "🤸"},
] %}
```

- [ ] **Step 3: Remove hardcoded poses set (lines 33-38)**

Delete these lines:

```
{% set poses = [
    {"value": "front_standing", "label": "Fashion Stand", "icon": "🧍"},
    {"value": "casual_walking", "label": "Casual Walk",   "icon": "🚶"},
    {"value": "seated",         "label": "Seated",        "icon": "🪑"},
    {"value": "dynamic",        "label": "Dynamic",       "icon": "💃"},
] %}
```

- [ ] **Step 4: Convert body type rendering (lines 164-180) from Jinja2 loop to Alpine x-for**

Replace the `{% for bt in body_types %}` block with:

```html
                    {# Body Type — gender-filtered cards #}
                    <div>
                        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Body Type</p>
                        <div class="grid grid-cols-4 gap-2">
                            <template x-for="bt in currentBodyTypes" :key="bt.value">
                                <label @click="body_type = bt.value" class="cursor-pointer">
                                    <div class="rounded-xl border-2 overflow-hidden transition-all text-center py-3 px-1"
                                         :class="body_type === bt.value
                                             ? 'border-primary bg-primary/5'
                                             : 'border-gray-200 hover:border-primary/30'">
                                        <p class="text-xl mb-0.5" x-text="bt.icon"></p>
                                        <p class="text-[10px] font-semibold text-dark" x-text="bt.label"></p>
                                    </div>
                                </label>
                            </template>
                        </div>
                    </div>
```

- [ ] **Step 5: Convert pose rendering (lines 289-305) from Jinja2 loop to Alpine x-for**

Replace the `{% for pose in poses %}` block with:

```html
                    {# Pose — gender-filtered cards #}
                    <div>
                        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Pose</p>
                        <div class="grid grid-cols-4 gap-2">
                            <template x-for="pose in currentPoses" :key="pose.value">
                                <label @click="pose_preset = pose.value" class="cursor-pointer">
                                    <div class="rounded-xl border-2 overflow-hidden transition-all text-center py-3 px-1"
                                         :class="pose_preset === pose.value
                                             ? 'border-primary bg-primary/5'
                                             : 'border-gray-200 hover:border-primary/30'">
                                        <p class="text-xl mb-0.5" x-text="pose.icon"></p>
                                        <p class="text-[10px] font-semibold text-dark leading-tight" x-text="pose.label"></p>
                                    </div>
                                </label>
                            </template>
                        </div>
                    </div>
```

- [ ] **Step 6: Update measurement label (line 468)**

Change the hardcoded `"Chest / Bust cm"` to use Alpine's `measurementLabel` getter:

Replace:
```html
                                ("m_chest_bust_cm","Chest / Bust cm", "e.g. 88"),
```

With the Chest/Bust field using Alpine binding instead of a Jinja2 loop. Since this field is inside a Jinja2 `{% for %}` loop along with Height/Waist/Hips, the cleanest approach is to render the measurement inputs individually and use `x-text` for the label on just the chest/bust field:

Replace the entire measurements grid (lines 465-480) with:

```html
                        <div class="grid grid-cols-2 gap-3">
                            <div>
                                <label class="block text-xs font-medium text-gray-600 mb-1">Height (cm)</label>
                                <input type="number" x-model="m_height_cm"
                                       inputmode="numeric" placeholder="e.g. 165"
                                       class="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm text-gray-900
                                              focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-colors">
                            </div>
                            <div>
                                <label class="block text-xs font-medium text-gray-600 mb-1" x-text="measurementLabel"></label>
                                <input type="number" x-model="m_chest_bust_cm"
                                       inputmode="numeric" placeholder="e.g. 88"
                                       class="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm text-gray-900
                                              focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-colors">
                            </div>
                            <div>
                                <label class="block text-xs font-medium text-gray-600 mb-1">Waist (cm)</label>
                                <input type="number" x-model="m_waist_cm"
                                       inputmode="numeric" placeholder="e.g. 68"
                                       class="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm text-gray-900
                                              focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-colors">
                            </div>
                            <div>
                                <label class="block text-xs font-medium text-gray-600 mb-1">Hips (cm)</label>
                                <input type="number" x-model="m_hips_cm"
                                       inputmode="numeric" placeholder="e.g. 94"
                                       class="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm text-gray-900
                                              focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-colors">
                            </div>
                        </div>
```

- [ ] **Step 7: Commit**

```bash
git add app/templates/configure.html
git commit -m "feat: use gender-filtered body types and poses in adult configure page"
```

---

### Task 4: Update route handler to pass gender options JSON

**Files:**
- Modify: `app/main.py:481-483`

- [ ] **Step 1: Update the `/configure` route**

Change from:
```python
@app.get("/configure")
async def configure_page(request: Request):
    return templates.TemplateResponse("configure.html", _ctx(request))
```

To:
```python
@app.get("/configure")
async def configure_page(request: Request):
    from app.config.gender_options import get_adult_options_json
    return templates.TemplateResponse(
        "configure.html",
        _ctx(request, gender_options_json=get_adult_options_json()),
    )
```

- [ ] **Step 2: Commit**

```bash
git add app/main.py
git commit -m "feat: pass gender options JSON to adult configure template"
```

---

### Task 5: Build, deploy, and manually test adult module

- [ ] **Step 1: Build and restart Docker containers**

```bash
docker compose -f "E:\AiGNITE\projects\DrapeStudio\docker-compose.yml" build api worker
docker compose -f "E:\AiGNITE\projects\DrapeStudio\docker-compose.yml" up -d api worker
```

- [ ] **Step 2: Manual testing**

Open `http://localhost:8888/upload`:
1. Select "Women" → go to Configure → verify: Slim/Average/Curvy/Plus Size body types, female hair styles, female poses
2. Go back, select "Men" → go to Configure → verify: Slim/Average/Athletic/Heavy Build body types, male hair styles, male poses
3. Go back, select "Unisex" → go to Configure → verify: Slim/Average/Athletic/Plus Size body types, neutral hair/poses
4. Verify sceneSummary displays correct pose labels
5. Verify measurement label shows "Bust (cm)" for Women, "Chest (cm)" for Men

- [ ] **Step 3: Push**

```bash
git push origin main
```

---

## Chunk 2: Children Module + Fit-On Module

### Task 6: Update children `children-config.js` — gender-filtered hair

**Files:**
- Modify: `app/static/js/children-config.js`

- [ ] **Step 1: Replace flat hairOptions with gender-keyed object from injected config**

Replace the `hairOptions` arrays in each AGE_CONFIG age group. Instead of hardcoded arrays, read from `window.CHILDREN_HAIR_OPTIONS`.

For each age group (baby, toddler, kid, teen), replace the `hairOptions` property with:

```javascript
            hairOptions: (window.CHILDREN_HAIR_OPTIONS && window.CHILDREN_HAIR_OPTIONS['baby']) || {
                girl:   [{ id: 'none', label: 'None / Natural', icon: '✨' }, ...],
                boy:    [...],
                unisex: [...],
            },
```

Actually, the cleanest approach: keep the AGE_CONFIG structure but override hairOptions at init time. After `var initial = AGE_CONFIG[initialAgeGroup] || AGE_CONFIG.kid;` (line 121), add:

```javascript
    // Override hairOptions with gender-keyed data from backend if available
    if (window.CHILDREN_HAIR_OPTIONS) {
        Object.keys(AGE_CONFIG).forEach(function(group) {
            if (window.CHILDREN_HAIR_OPTIONS[group]) {
                AGE_CONFIG[group].hairOptions = window.CHILDREN_HAIR_OPTIONS[group];
            }
        });
        initial = AGE_CONFIG[initialAgeGroup] || AGE_CONFIG.kid;
    }
```

- [ ] **Step 2: Add `currentHairOptions` computed getter**

In the returned state object, add after the `skinTones` array (after line 139):

```javascript
        get currentHairOptions() {
            var hairMap = this.config.hairOptions;
            // If gender-keyed (object with girl/boy/unisex keys), filter by gender
            if (hairMap && !Array.isArray(hairMap)) {
                var opts = hairMap[this.childGender] || hairMap.unisex || [];
                return opts.map(function(o) {
                    return { id: o.id, label: o.label ? o.label.en : o.id, icon: o.icon || '' };
                });
            }
            // Fallback: flat array (old format)
            return hairMap || [];
        },
```

- [ ] **Step 3: Update `initFromSession()` to validate selectedHair**

Update `initFromSession()` (lines 143-146):

```javascript
        initFromSession() {
            var cg = sessionStorage.getItem('childGender');
            if (cg) this.childGender = cg;
            // Validate selectedHair against gender-filtered options
            var validHair = this.currentHairOptions.map(function(h) { return h.id; });
            if (!validHair.includes(this.selectedHair)) {
                this.selectedHair = validHair[0] || '';
            }
        },
```

- [ ] **Step 4: Update `changeAgeGroup()` to validate hair after age change**

In `changeAgeGroup()` (line 155), replace `this.selectedHair = this.config.hairOptions[0].id;` with:

```javascript
            // Reset hair to first valid option for current gender
            var validHair = this.currentHairOptions;
            this.selectedHair = validHair.length > 0 ? validHair[0].id : '';
```

- [ ] **Step 5: Commit**

```bash
git add app/static/js/children-config.js
git commit -m "feat: add gender-filtered hair options to children config"
```

---

### Task 7: Update children `configure.html` and route handler

**Files:**
- Modify: `app/templates/children/configure.html`
- Modify: `app/main.py:637-645`

- [ ] **Step 1: Update children configure template — use `currentHairOptions` getter**

In `children/configure.html`, change the hair options x-for (around line 88-89):

From: `x-for="hair in config.hairOptions"`
To: `x-for="hair in currentHairOptions"`

- [ ] **Step 2: Inject CHILDREN_HAIR_OPTIONS JSON**

In the children configure template, add before the children-config.js script include:

```html
<script>
  window.CHILDREN_HAIR_OPTIONS = {{ children_hair_json | safe }};
</script>
```

- [ ] **Step 3: Update the `/children/configure` route in main.py**

Change from:
```python
@app.get("/children/configure")
async def children_configure_page(request: Request, age_group: str = "kid"):
    from app.children_config import AGE_GROUPS
    if age_group not in AGE_GROUPS:
        age_group = "kid"
    return templates.TemplateResponse(
        "children/configure.html",
        _ctx(request, age_group=age_group, age_groups=AGE_GROUPS),
    )
```

To:
```python
@app.get("/children/configure")
async def children_configure_page(request: Request, age_group: str = "kid"):
    from app.children_config import AGE_GROUPS
    from app.config.gender_options import get_children_hair_json
    if age_group not in AGE_GROUPS:
        age_group = "kid"
    return templates.TemplateResponse(
        "children/configure.html",
        _ctx(request, age_group=age_group, age_groups=AGE_GROUPS,
             children_hair_json=get_children_hair_json()),
    )
```

- [ ] **Step 4: Commit**

```bash
git add app/templates/children/configure.html app/main.py
git commit -m "feat: gender-filtered hair options in children configure page"
```

---

### Task 8: Update fit-on `customer_details.html` — gender-aware build

**Files:**
- Modify: `app/templates/fiton/customer_details.html`
- Modify: `app/main.py:704-706`

- [ ] **Step 1: Inject FITON_BUILD JSON and add x-effect watcher**

In the template, add before the main script block:
```html
<script>
  window.FITON_BUILD = {{ fiton_build_json | safe }};
</script>
```

- [ ] **Step 2: Add `currentBuildOptions` computed getter to the Alpine state**

In the Alpine `x-data` object, add:
```javascript
get currentBuildOptions() {
    var buildMap = window.FITON_BUILD || {};
    var opts = buildMap[this.customerGender] || buildMap.female || [];
    return opts.map(function(o) {
        return { id: o.id, label: o.label ? o.label.en : o.id, desc: o.desc ? o.desc.en : '' };
    });
},
```

- [ ] **Step 3: Add x-effect watcher to reset build on gender change**

Add this `x-effect` to the Alpine component:
```javascript
$watch('customerGender', function(val) {
    var validBuilds = this.currentBuildOptions.map(function(b) { return b.id; });
    if (!validBuilds.includes(this.customerBuild)) {
        this.customerBuild = validBuilds[0] || 'medium';
    }
}.bind(this));
```

Or use `x-init` to run once on load, and add the `$watch` in the init.

- [ ] **Step 4: Replace hardcoded build options (lines 302-323) with Alpine x-for**

Replace the `{% for val, label, desc in [...] %}` block with:

```html
                    {# Build selector — gender-filtered #}
                    <div>
                        <label class="block text-xs font-semibold text-gray-700 mb-2">Approximate Build</label>
                        <div class="grid grid-cols-2 gap-2">
                            <template x-for="opt in currentBuildOptions" :key="opt.id">
                                <label @click="customerBuild = opt.id" class="cursor-pointer">
                                    <div class="rounded-xl border-2 p-3 text-center transition-all select-none"
                                         :class="customerBuild === opt.id
                                             ? 'border-primary bg-primary/5'
                                             : 'border-gray-200 hover:border-primary/30'">
                                        <p class="text-xs font-bold text-dark" x-text="opt.label"></p>
                                        <p class="text-[10px] text-gray-400" x-text="opt.desc"></p>
                                    </div>
                                </label>
                            </template>
                        </div>
                    </div>
```

- [ ] **Step 5: Fix measurement label — gender-conditional**

Find `"Bust / Chest (cm)"` label (around line 166) and replace with:
```html
<label class="block text-xs font-semibold text-gray-700 mb-1.5"
       x-text="customerGender === 'male' ? 'Chest (cm)' : 'Bust (cm)'"></label>
```

- [ ] **Step 6: Fix quick mode gender bug (line 619)**

Change:
```javascript
                        gender:     'female',
```
To:
```javascript
                        gender:     alpineData.customerGender,
```

- [ ] **Step 7: Add male buildToMeasurements and use gender-aware map (lines 604-610)**

Replace:
```javascript
                var buildToMeasurements = {
                    'slim':      { bust_cm: 82, waist_cm: 64, hips_cm: 88 },
                    'medium':    { bust_cm: 89, waist_cm: 71, hips_cm: 95 },
                    'curvy':     { bust_cm: 96, waist_cm: 78, hips_cm: 104 },
                    'plus-size': { bust_cm: 108, waist_cm: 92, hips_cm: 116 },
                };
                var buildMeas = buildToMeasurements[alpineData.customerBuild] || buildToMeasurements['medium'];
```

With:
```javascript
                var femaleBuildToMeasurements = {
                    'slim':      { bust_cm: 82, waist_cm: 64, hips_cm: 88 },
                    'medium':    { bust_cm: 89, waist_cm: 71, hips_cm: 95 },
                    'curvy':     { bust_cm: 96, waist_cm: 78, hips_cm: 104 },
                    'plus-size': { bust_cm: 108, waist_cm: 92, hips_cm: 116 },
                };
                var maleBuildToMeasurements = {
                    'slim':     { bust_cm: 88, waist_cm: 72, hips_cm: 84 },
                    'medium':   { bust_cm: 96, waist_cm: 82, hips_cm: 92 },
                    'athletic': { bust_cm: 100, waist_cm: 78, hips_cm: 94 },
                    'heavy':    { bust_cm: 112, waist_cm: 98, hips_cm: 106 },
                };
                var buildMap = alpineData.customerGender === 'male' ? maleBuildToMeasurements : femaleBuildToMeasurements;
                var buildMeas = buildMap[alpineData.customerBuild] || buildMap['medium'];
```

- [ ] **Step 8: Update the `/fiton/customer` route in main.py**

Change from:
```python
@app.get("/fiton/customer")
async def fiton_customer_page(request: Request):
    return templates.TemplateResponse("fiton/customer_details.html", _ctx(request))
```

To:
```python
@app.get("/fiton/customer")
async def fiton_customer_page(request: Request):
    from app.config.gender_options import get_fiton_build_json
    return templates.TemplateResponse(
        "fiton/customer_details.html",
        _ctx(request, fiton_build_json=get_fiton_build_json()),
    )
```

- [ ] **Step 9: Commit**

```bash
git add app/templates/fiton/customer_details.html app/main.py
git commit -m "feat: gender-aware build options and measurement labels in fit-on"
```

---

### Task 9: Build, deploy, and test children + fit-on

- [ ] **Step 1: Build and restart Docker containers**

```bash
docker compose -f "E:\AiGNITE\projects\DrapeStudio\docker-compose.yml" build api worker
docker compose -f "E:\AiGNITE\projects\DrapeStudio\docker-compose.yml" up -d api worker
```

- [ ] **Step 2: Test children module**

1. Go to `/children/upload`, select "Boy" → go to Configure → verify boy-appropriate hair (Short, Buzz Cut, Curly, Side Part for kid age)
2. Select "Girl" → verify girl hair (Short, Medium, Long, Ponytail, Braids, Curly)
3. Switch age group → verify hair resets and stays gender-appropriate

- [ ] **Step 3: Test fit-on module**

1. Go to `/fiton/upload` → upload garment → go to customer details
2. Select "Male" → verify build: Slim/Medium/Athletic/Heavy (no Curvy)
3. Select "Female" → verify: Slim/Medium/Curvy/Plus Size
4. Verify "Chest (cm)" for male, "Bust (cm)" for female
5. Switch gender → verify build resets if current is invalid

- [ ] **Step 4: Push**

```bash
git push origin main
```

---

## Chunk 3: Prompt Assembly + Review Page + YAML

### Task 10: Update `prompts/v0_1.yaml` — add new hair style + pose descriptions

**Files:**
- Modify: `prompts/v0_1.yaml`

- [ ] **Step 1: Add new hair style descriptions**

After line 51 (`natural_curly: "natural curly hair"`), add:

```yaml
  bun: "hair styled in a neat bun or updo"
  side_part: "medium-length hair with a clean side part"
```

- [ ] **Step 2: Add casual_walking alias and new gender-specific poses**

Replace the entire `poses:` section (lines 71-75) with:

```yaml
poses:
  front_standing: "standing facing camera, arms relaxed at sides, weight evenly balanced"
  walking: "mid-stride walking pose, natural movement, slight body angle to camera"
  casual_walking: "mid-stride walking pose, natural movement, slight body angle to camera"
  three_quarter: "45-degree body turn toward camera, one shoulder forward, natural stance"
  seated: "seated naturally on a stool or bench, upright posture, feet flat"
  dynamic: "dynamic fashion pose with natural movement and energy"
  fashion_standing: "elegant standing pose, one foot slightly forward, confident fashion stance"
  seated_elegant: "seated elegantly, legs crossed or angled, poised upright posture"
  hand_on_hip: "standing with one hand resting on hip, confident and stylish"
  standing_confident: "standing tall with confident posture, shoulders back, relaxed arms"
  hands_in_pockets: "standing casually with hands in pockets, relaxed confident stance"
  seated_casual: "seated in a relaxed casual pose, one ankle on knee or leaning slightly"
```

- [ ] **Step 3: Commit**

```bash
git add prompts/v0_1.yaml
git commit -m "feat: add gender-specific pose and hair style descriptions to prompt template"
```

---

### Task 11: Update `app/services/prompt.py` — gender-appropriate body type terms

**Files:**
- Modify: `app/services/prompt.py:154-156`

- [ ] **Step 1: Add BODY_TYPE_DESCRIPTIONS mapping**

Before the `assemble_prompt()` function (before line 91), add:

```python
# Human-readable body type descriptions for prompt generation.
# Maps option IDs → natural-language descriptions used in the prompt.
BODY_TYPE_DESCRIPTIONS = {
    "slim": "slim build",
    "average": "average build",
    "curvy": "curvy, fuller figure",
    "plus_size": "plus-size, fuller figure",
    "athletic": "athletic, muscular build",
    "heavy": "heavy, broad muscular build",
    "plus": "plus-size build",  # legacy value from older sessions
}
```

- [ ] **Step 2: Use the mapping in the prompt (line 156)**

Replace line 156:
```python
            f"Fitzpatrick skin tone {skin_tone}, {body_type} body type"
```

With:
```python
            f"Fitzpatrick skin tone {skin_tone}, "
            f"{BODY_TYPE_DESCRIPTIONS.get(body_type, body_type + ' build')}"
```

- [ ] **Step 3: Commit**

```bash
git add app/services/prompt.py
git commit -m "feat: use gender-appropriate body type descriptions in prompts"
```

---

### Task 12: Update `app/services/fiton_prompt.py` — gender-aware build terms

**Files:**
- Modify: `app/services/fiton_prompt.py:146-175`

- [ ] **Step 1: Add gender-aware build term mapping in `_build_customer_description()`**

After the existing build inference (lines 159-167), add gender-aware mapping:

Replace lines 159-167:
```python
        waist_cm = measurements.get("waist_cm", 72.0)
        if waist_cm < 66:
            build = "slim"
        elif waist_cm < 78:
            build = "medium"
        elif waist_cm < 90:
            build = "curvy"
        else:
            build = "plus-size"
```

With:
```python
        waist_cm = measurements.get("waist_cm", 72.0)
        gender = measurements.get("gender", "female")

        if waist_cm < 66:
            build = "slim"
        elif waist_cm < 78:
            build = "medium"
        elif waist_cm < 90:
            build = "curvy" if gender == "female" else "athletic"
        else:
            build = "plus-size" if gender == "female" else "heavy build"
```

- [ ] **Step 2: Commit**

```bash
git add app/services/fiton_prompt.py
git commit -m "feat: use gender-appropriate build terms in fiton prompts"
```

---

### Task 13: Update `review.html` — add VALUE_LABELS for new option IDs

**Files:**
- Modify: `app/templates/review.html:171-220`

- [ ] **Step 1: Add new body type labels**

After line 175 (`plus_size: 'Plus Size',`), add:

```javascript
        curvy:              'Curvy',
        heavy:              'Heavy Build',
```

- [ ] **Step 2: Add new hair style labels**

After line 182 (`braided: 'Braided',`), add:

```javascript
        bun:                'Bun / Updo',
```

- [ ] **Step 3: Add new pose labels**

After line 220 (`dynamic: 'Dynamic',`), add:

```javascript
        seated_elegant:     'Seated Elegant',
        hand_on_hip:        'Hand on Hip',
        standing_confident: 'Confident Stand',
        hands_in_pockets:   'Hands in Pockets',
        seated_casual:      'Seated Casual',
```

Note: `fashion_standing: 'Fashion'` already exists on line 239 for children. The adult version can coexist (it maps to the same label). If a distinct label is needed, the entry for children will match.

- [ ] **Step 4: Commit**

```bash
git add app/templates/review.html
git commit -m "feat: add VALUE_LABELS for gender-specific body types, hair, and poses"
```

---

### Task 14: Final build, deploy, and end-to-end testing

- [ ] **Step 1: Build and restart Docker containers**

```bash
docker compose -f "E:\AiGNITE\projects\DrapeStudio\docker-compose.yml" build api worker
docker compose -f "E:\AiGNITE\projects\DrapeStudio\docker-compose.yml" up -d api worker
```

- [ ] **Step 2: End-to-end testing checklist**

1. Adult: Women → Curvy/Plus Size body types, female hair, female poses
2. Adult: Men → Athletic/Heavy body types, male hair, male poses
3. Adult: Unisex → Athletic/Plus Size body types, neutral hair, neutral poses
4. Adult: sceneSummary shows correct pose labels
5. Adult: Measurement label: "Bust (cm)" for Women, "Chest (cm)" for Men
6. Adult: Review page shows correct labels for all new option IDs
7. Children: Boy → boy hair (Short, Buzz, Curly, Side Part)
8. Children: Girl → girl hair (includes Ponytail, Braids)
9. Fit-on: Male → Slim/Medium/Athletic/Heavy (no Curvy)
10. Fit-on: Female → Slim/Medium/Curvy/Plus Size
11. Fit-on: Chest vs Bust label
12. Fit-on: Quick mode sends actual gender (not hardcoded female)
13. Fit-on: Switching gender resets build
14. Submit a generation → verify prompt has gender-appropriate terms

- [ ] **Step 3: Push all changes**

```bash
git push origin main
```
