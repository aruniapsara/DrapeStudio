# Gender-Aware Style Options — Design Spec

**Date:** 2026-03-12
**Status:** Reviewed
**Scope:** Make all style/appearance options (body type, hair style, pose, build) gender-aware across adult, children, and fit-on modules.

---

## Problem

Body types like "Curvy" show for male selections. Hair styles are partially filtered (adult only). Poses are identical across genders. Fit-on build options ignore gender. Children's hair options ignore gender entirely. Measurement labels use a combined "Bust / Chest" instead of gender-specific terms. Quick mode hardcodes `gender: 'female'` regardless of selection.

## Solution

Centralized Python config (`app/config/gender_options.py`) as the single source of truth for all gender-keyed option maps. Options are injected into templates via Jinja2 context and filtered reactively with Alpine.js computed getters.

---

## 1. Centralized Config — `app/config/gender_options.py`

New file. Contains all option maps keyed by gender. Each option has `id`, `label` (multilingual: en/si/ta), and optionally `icon` and `description`.

### Gender Key Mapping (preserves existing values — no migration)

| Module | Gender Values | Source |
|--------|--------------|--------|
| Adult | `feminine`, `masculine`, `neutral` | sessionStorage `genderPresentation` |
| Children | `girl`, `boy`, `unisex` | sessionStorage `childGender` |
| Fit-on | `female`, `male` | Alpine state `customerGender` |

### Option Maps

**BODY_TYPES** — keyed by `feminine`/`masculine`/`neutral`:
- `feminine`: slim, average, curvy, plus_size
- `masculine`: slim, average, athletic, heavy
- `neutral`: slim, average, athletic, plus_size

> **Legacy compatibility:** The current codebase uses `"plus"` as the body type value (configure.html line 20). The new config uses `"plus_size"`. The prompt assembly layer (Section 5) maps both `"plus"` and `"plus_size"` to the same description. The `review.html` VALUE_LABELS already has `plus_size: 'Plus Size'` and a fallback `val.replace(/_/g, ' ')` handles the old `"plus"` value gracefully. No DB migration needed — old records with `"plus"` continue to work.

**HAIR_STYLES** — keyed by `feminine`/`masculine`/`neutral`:
- `feminine`: long_straight, long_wavy, medium_layered, short_bob, curly, braided, bun
- `masculine`: short_crop, side_part, slicked_back, curly_short, buzz_cut, long
- `neutral`: short_straight, medium_length, long_straight, shaved, natural_curly

> **ID reconciliation:** The spec uses `side_part` (matching existing configure.js line 75), NOT `medium_side`. The `bun` style is new and must be added to `prompts/v0_1.yaml` hair_styles section (see Section 5).

**POSES** — keyed by `feminine`/`masculine`/`neutral`:
- `feminine`: fashion_standing, casual_walking, seated_elegant, hand_on_hip
- `masculine`: standing_confident, casual_walking, hands_in_pockets, seated_casual
- `neutral`: front_standing, casual_walking, seated, dynamic (current defaults)

**FITON_BUILD** — keyed by `female`/`male`:
- `female`: slim, medium, curvy, plus-size
- `male`: slim, medium, athletic, heavy

> **Value format:** Fiton build uses hyphenated `"plus-size"` (matching existing `buildToMeasurements` map on customer_details.html line 608). This is different from adult body type `"plus_size"` (underscored). Each module keeps its existing convention.

**CHILDREN_HAIR** — keyed by `girl`/`boy`/`unisex`, nested inside each age group:

For age groups `toddler`, `kid`, `teen`:
- `girl`: short, medium, long, ponytail, braids, curly (age-appropriate subset)
- `boy`: short, buzz, curly, side_part (age-appropriate subset)
- `unisex`: union of both with duplicates removed

For `baby`: same for all genders (none, bonnet, cap) — no filtering needed.

All option labels include `en`, `si`, `ta` translations as specified in the user's requirements.

---

## 2. Adult Configure — Template + JS Changes

### Files: `configure.html`, `configure.js`

**Current state:**
- Body types: hardcoded in Jinja2 `{% set body_types %}` (4 options, same for all)
- Hair styles: gender-filtered via JS `hairStyleOptions` map + `currentHairStyles` getter
- Poses: hardcoded in Jinja2 `{% set poses %}` (4 options, same for all)

**Changes:**

### configure.html
1. Remove the `{% set body_types %}` and `{% set poses %}` Jinja2 blocks (lines 16-21, 33-38)
2. Add a `<script>` block that injects the gender options from the backend:
   ```html
   <script>
     window.GENDER_OPTIONS = {{ gender_options_json | safe }};
   </script>
   ```
3. Convert body type rendering from `{% for bt in body_types %}` to Alpine `x-for="bt in currentBodyTypes"` (mirrors hair style pattern)
4. Convert pose rendering from `{% for pose in poses %}` to Alpine `x-for="pose in currentPoses"`
5. Update measurement label: conditionally show "Chest" for masculine, "Bust" for feminine, "Chest / Bust" for neutral

### configure.js
1. Remove hardcoded `hairStyleOptions` object — use `window.GENDER_OPTIONS.HAIR_STYLES` instead
2. Add `bodyTypeOptions` sourced from `window.GENDER_OPTIONS.BODY_TYPES`
3. Add `poseOptions` sourced from `window.GENDER_OPTIONS.POSES`
4. Add computed getters:
   ```javascript
   get currentBodyTypes() {
       return this.bodyTypeOptions[this.gender] || this.bodyTypeOptions.neutral;
   },
   get currentPoses() {
       return this.poseOptions[this.gender] || this.poseOptions.neutral;
   },
   ```
5. In `init()`: validate `body_type` and `pose_preset` against current gender options (same pattern as existing hair_style validation)
6. Label helper: `get measurementLabel() { return this.gender === 'masculine' ? 'Chest' : this.gender === 'feminine' ? 'Bust' : 'Chest / Bust'; }`
7. **Update `sceneSummary` getter** (lines 133-152): The existing `poseMap` has only 4 entries (`front_standing`, `casual_walking`, `seated`, `dynamic`). Add entries for all new pose IDs: `fashion_standing: 'Fashion Stand'`, `seated_elegant: 'Seated Elegant'`, `hand_on_hip: 'Hand on Hip'`, `standing_confident: 'Confident Stand'`, `hands_in_pockets: 'Hands in Pockets'`, `seated_casual: 'Seated Casual'`.

### Route handler
The route that renders `configure.html` must pass `gender_options_json` in the template context. This is a JSON serialization of the relevant maps from `gender_options.py`.

---

## 3. Children Configure — Template + JS Changes

### Files: `children/configure.html`, `children-config.js`

**Current state:**
- Hair options: per-age-group arrays in `AGE_CONFIG`, not gender-filtered
- Poses: per-age-group arrays, not gender-filtered (poses stay gender-neutral for children)
- Gender is set on the upload page and stored in sessionStorage as `childGender` — there is NO gender selector on the configure page

**Changes:**

### children-config.js
1. Restructure `AGE_CONFIG[group].hairOptions` from a flat array to a gender-keyed object:
   ```javascript
   hairOptions: {
       girl: [...],
       boy: [...],
       unisex: [...]
   }
   ```
   Data sourced from `window.GENDER_OPTIONS.CHILDREN_HAIR[ageGroup]`
2. Add computed getter:
   ```javascript
   get currentHairOptions() {
       var hairMap = this.config.hairOptions;
       return hairMap[this.childGender] || hairMap.unisex || Object.values(hairMap)[0];
   }
   ```
3. In `changeAgeGroup()`: after switching config, validate `selectedHair` against new gender-filtered options
4. In `init()`: read `childGender` from sessionStorage and validate `selectedHair` against gender-filtered options

> **No runtime gender change on this page.** Gender is read-only from the upload step (same pattern as adult). No `changeGender()` method needed on the configure page. If user wants to change gender, they go back to upload.

### children/configure.html
1. Change `x-for="hair in config.hairOptions"` to `x-for="hair in currentHairOptions"`
2. Inject gender options JSON from backend context (same pattern as adult)
3. Children's poses remain gender-neutral (no change needed — poses like "standing", "sitting", "playing" are appropriate for all children)

### Route handler
Pass `children_gender_options_json` in template context.

---

## 4. Fit-On Customer Details — Template Changes

### File: `fiton/customer_details.html`

**Current state:**
- Build options: hardcoded 4 options (slim, medium, curvy, plus-size) for all genders
- Measurement label: "Bust / Chest (cm)" — combined
- Quick mode hardcodes `gender: 'female'` (line 619) regardless of `customerGender` selection

**Changes:**

1. Inject `FITON_BUILD` options from backend as JSON
2. Add computed getter:
   ```javascript
   get currentBuildOptions() {
       return FITON_BUILD[this.customerGender] || FITON_BUILD.female;
   }
   ```
3. Convert build option rendering from `{% for val, label, desc %}` to Alpine `x-for="opt in currentBuildOptions"`
4. Add `x-effect` watcher: when `customerGender` changes, validate `customerBuild` against new options. If the current build value is not in the new list, reset to the first option.
5. Measurement label: `x-text="customerGender === 'male' ? 'Chest (cm)' : 'Bust (cm)'"` replaces static "Bust / Chest (cm)"
6. **Fix quick mode gender bug (line 619):** Change `gender: 'female'` to `gender: alpineData.customerGender` so the actual selected gender flows to the prompt builder
7. **Add male build-to-measurements map:** The existing `buildToMeasurements` (line 604-609) has female-appropriate values (slim/medium/curvy/plus-size). Add a parallel map for male builds:
   ```javascript
   var maleBuildToMeasurements = {
       'slim':     { bust_cm: 88, waist_cm: 72, hips_cm: 84 },
       'medium':   { bust_cm: 96, waist_cm: 82, hips_cm: 92 },
       'athletic': { bust_cm: 100, waist_cm: 78, hips_cm: 94 },
       'heavy':    { bust_cm: 112, waist_cm: 98, hips_cm: 106 },
   };
   ```
   Select the appropriate map based on `alpineData.customerGender`.

### Route handler
Pass `fiton_build_json` in template context.

---

## 5. Prompt Assembly — Gender-Appropriate Terms

### File: `app/services/prompt.py`

**Current state (line ~165):**
```python
model_desc = f"... {body_type} body type"
```
The raw body_type ID (e.g., "athletic", "curvy") is injected directly.

**Changes:**

Add a body type description mapping that produces gender-appropriate prompt text:

```python
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

Replace direct `{body_type} body type` with `BODY_TYPE_DESCRIPTIONS.get(body_type, body_type + " build")`.

### New hair style and pose descriptions in `prompts/v0_1.yaml`

**Hair styles — add these new entries:**
```yaml
hair_styles:
  # ... existing entries ...
  bun: "hair styled in a neat bun or updo"
  side_part: "medium-length hair with a clean side part"
```

> **ID reconciliation:** The existing YAML has `medium_textured` which maps to the old masculine hair. The new config uses `side_part` (matching existing configure.js). Both entries stay in the YAML for backward compatibility.

**Poses — fix existing key and add new entries:**
```yaml
poses:
  # Existing (fix: add casual_walking as alias for walking)
  front_standing: "standing facing camera, arms relaxed at sides, weight evenly balanced"
  walking: "mid-stride walking pose, natural movement, slight body angle to camera"
  casual_walking: "mid-stride walking pose, natural movement, slight body angle to camera"
  seated: "seated naturally on a stool or bench, upright posture, feet flat"
  dynamic: "dynamic fashion pose with natural movement and energy"
  # Female-specific
  fashion_standing: "elegant standing pose, one foot slightly forward, confident fashion stance"
  seated_elegant: "seated elegantly, legs crossed or angled, poised upright posture"
  hand_on_hip: "standing with one hand resting on hip, confident and stylish"
  # Male-specific
  standing_confident: "standing tall with confident posture, shoulders back, relaxed arms"
  hands_in_pockets: "standing casually with hands in pockets, relaxed confident stance"
  seated_casual: "seated in a relaxed casual pose, one ankle on knee or leaning slightly"
```

> **Key fix:** The existing YAML has `walking` but the frontend sends `casual_walking`. Adding `casual_walking` as a duplicate entry ensures prompt lookups work. The old `walking` key is kept for backward compatibility with any existing DB records.

### File: `app/services/fiton_prompt.py`

**Current state:** `_build_customer_description()` infers build from `waist_cm` using gender-neutral thresholds and terms ("slim", "medium", "curvy", "plus-size").

**Changes:**
1. Accept gender parameter to determine build vocabulary
2. When gender is male and inferred build would be "curvy", use "athletic" instead
3. When gender is male and inferred build would be "plus-size", use "heavy build" instead
4. The `build` value from quick mode already flows through `customer_measurements` → `waist_cm` inference. The `customerBuild` selection determines the synthetic measurements which then get inferred back. This indirection works because the `buildToMeasurements` map produces waist values that map back to the same build category.

---

## 6. Backend Route Changes

### Files affected: `app/main.py` or individual route handlers

Each configure page route must pass the relevant gender options as JSON in the template context:

- `GET /configure` → pass `BODY_TYPES`, `HAIR_STYLES`, `POSES` (adult keys)
- `GET /children/configure` → pass `CHILDREN_HAIR` (children keys)
- `GET /fiton/customer-details` → pass `FITON_BUILD` (fiton keys)

Implementation: import from `app.config.gender_options`, serialize with `json.dumps()`, pass as `gender_options_json` in the Jinja2 context dict.

---

## 7. Review Page — Display Label Updates

### File: `app/templates/review.html`

**Current state:** `VALUE_LABELS` map (lines 165-245) has labels for current body types, hair styles, poses. Missing entries for new gender-specific option IDs.

**Changes — add entries to `VALUE_LABELS`:**

```javascript
// Body types (new)
curvy:              'Curvy',
heavy:              'Heavy Build',
// Poses (new gender-specific)
fashion_standing:   'Fashion Stand',   // NOTE: already exists for children (line 239)
seated_elegant:     'Seated Elegant',
hand_on_hip:        'Hand on Hip',
standing_confident: 'Confident Stand',
hands_in_pockets:   'Hands in Pockets',
seated_casual:      'Seated Casual',
// Hair styles (new)
bun:                'Bun / Updo',
```

> **Note:** `fashion_standing` already exists in VALUE_LABELS (line 239) for children. `curly_short` is already handled by the fallback `val.replace(/_/g, ' ')` → "curly short" which is acceptable. The `plus` legacy value falls through to `"plus"` which is acceptable.

---

## 8. Validation & Reset Logic

When gender changes (or on page load), selected values must be validated:

```
For each gender-filtered option (body_type, hair_style, pose_preset, build):
  1. Get the valid option IDs for the current gender
  2. If the currently selected value is in the valid list → keep it
  3. If not → reset to the first option in the list
```

This applies to:
- `configure.js init()` — body_type, hair_style, pose_preset (gender is read-only from upload)
- `children-config.js init()` and `changeAgeGroup()` — selectedHair (gender is read-only from upload)
- `fiton/customer_details.html` — customerBuild (via x-effect watcher on customerGender, which CAN change at runtime)

---

## 9. Files Change Summary

| # | File | Action | What Changes |
|---|------|--------|-------------|
| 1 | `app/config/gender_options.py` | CREATE | All option maps with multilingual labels |
| 2 | `app/templates/configure.html` | MODIFY | Remove hardcoded body_types/poses; use x-for on getters; inject JSON; conditional measurement label |
| 3 | `app/static/js/configure.js` | MODIFY | Add body type/pose option maps from injected config; add getters; update sceneSummary poseMap; add validation |
| 4 | `app/templates/children/configure.html` | MODIFY | Hair options use computed getter |
| 5 | `app/static/js/children-config.js` | MODIFY | Gender-keyed hair options per age group; add getter; validation |
| 6 | `app/templates/fiton/customer_details.html` | MODIFY | Build options from getter; measurement label conditional; fix quick mode gender bug (line 619); add male buildToMeasurements |
| 7 | `app/services/prompt.py` | MODIFY | Body type description mapping; gender-appropriate terms |
| 8 | `app/services/fiton_prompt.py` | MODIFY | Gender-aware build terms in _build_customer_description() |
| 9 | `prompts/v0_1.yaml` | MODIFY | Add bun/side_part hair descriptions; add casual_walking alias; add gender-specific pose descriptions |
| 10 | `app/main.py` (or route handlers) | MODIFY | Pass gender_options JSON to template contexts |
| 11 | `app/templates/review.html` | MODIFY | Add VALUE_LABELS entries for new body types, poses, hair styles |

**No changes needed:**
- `app/api/generations.py` — already passes through model_params dict as-is
- `app/worker/jobs.py` — already reads model_params from DB and passes to prompt assembly
- `app/models/db.py` — model_params is a JSON column, stores whatever dict is provided
- `app/schemas/generation.py` — body_type/pose_preset are string fields, no enum validation to update

---

## 10. Testing Checklist

1. Adult flow: Select "Men" in upload → configure shows Athletic/Heavy (not Curvy), male hair styles, male poses
2. Adult flow: Select "Women" → Curvy/Plus Size appear, female hair/poses shown
3. Adult flow: Select "Unisex" → Athletic/Plus Size shown, neutral hair/poses
4. Adult flow: sceneSummary displays human-readable labels for all new poses
5. Fit-on: Select male customer → build options: Slim/Medium/Athletic/Heavy (no Curvy)
6. Fit-on: Select female → Slim/Medium/Curvy/Plus Size shown
7. Fit-on: Male shows "Chest (cm)", Female shows "Bust (cm)"
8. Fit-on: Quick mode sends actual selected gender (not hardcoded female)
9. Fit-on: Switching gender resets build to first option if current is invalid
10. Children: Select Boy → boy-appropriate hair styles (short, buzz, curly, side_part)
11. Children: Select Girl → girl hair styles (ponytail, braids, long, etc.)
12. Switching gender dynamically updates options without page reload
13. Previously selected options that don't exist in new gender reset to defaults
14. Generated prompts use gender-appropriate body descriptions
15. Review page shows human-readable labels for all new option IDs
16. All three languages (en/si/ta) render correctly in option labels
17. Old DB records with `body_type: "plus"` still display correctly on review page
