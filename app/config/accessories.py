"""Accessories module category configuration.

Defines 9 accessory subcategories, each with display-mode-specific
AI generation parameters (body area, framing, model requirements).
"""

ACCESSORY_CATEGORIES = {
    "necklace": {
        "label": "Necklaces / Chains",
        "on_model": {
            "body_area": "neck and upper chest",
            "framing": "close-up chest/neck",
            "model_needs": "decolletage visible",
        },
        "flat_lay": {
            "surface": "fabric or marble",
            "arrangement": "laid flat or draped",
        },
        "lifestyle": {
            "context": "model touching necklace, candid",
        },
        "ai_params": ["chain_length", "pendant_size"],
    },
    "earrings": {
        "label": "Earrings",
        "on_model": {
            "body_area": "ears, face profile",
            "framing": "head/face close-up",
            "model_needs": "hair pulled back, ears visible",
        },
        "flat_lay": {
            "surface": "display card or velvet",
            "arrangement": "paired on surface",
        },
        "lifestyle": {
            "context": "profile shot, natural pose",
        },
        "ai_params": ["earring_type", "drop_length"],
    },
    "bracelet": {
        "label": "Bracelets / Bangles",
        "on_model": {
            "body_area": "wrist and hand",
            "framing": "wrist close-up",
            "model_needs": "elegant hand pose",
        },
        "flat_lay": {
            "surface": "fabric or arm form",
            "arrangement": "stacked or single",
        },
        "lifestyle": {
            "context": "hand gesture, wrist visible",
        },
        "ai_params": ["stacking_count"],
    },
    "ring": {
        "label": "Rings",
        "on_model": {
            "body_area": "finger",
            "framing": "hand close-up",
            "model_needs": "hand posed elegantly",
        },
        "flat_lay": {
            "surface": "ring holder or fabric",
            "arrangement": "single or set",
        },
        "lifestyle": {
            "context": "hand in natural position",
        },
        "ai_params": ["finger_position"],
    },
    "handbag": {
        "label": "Handbags / Purses",
        "on_model": {
            "body_area": "full body with bag",
            "framing": "full body",
            "model_needs": "holding bag naturally",
        },
        "flat_lay": {
            "surface": "flat surface, styled",
            "arrangement": "open or closed, contents styled",
        },
        "lifestyle": {
            "context": "walking pose, bag as focal point",
        },
        "ai_params": ["carry_style", "bag_size"],
    },
    "hat": {
        "label": "Hats / Headwear",
        "on_model": {
            "body_area": "head and face",
            "framing": "upper body",
            "model_needs": "face visible under hat",
        },
        "flat_lay": {
            "surface": "display form or surface",
            "arrangement": "crown up or angled",
        },
        "lifestyle": {
            "context": "outdoor fashion context",
        },
        "ai_params": ["hat_style"],
    },
    "scarf": {
        "label": "Scarves / Shawls",
        "on_model": {
            "body_area": "shoulders and neck",
            "framing": "upper body",
            "model_needs": "draped on shoulders",
        },
        "flat_lay": {
            "surface": "folded or draped on surface",
            "arrangement": "showing pattern",
        },
        "lifestyle": {
            "context": "walking, flowing fabric",
        },
        "ai_params": ["draping_style"],
    },
    "crochet": {
        "label": "Crochet Items",
        "on_model": {
            "body_area": "depends on item",
            "framing": "varies",
            "model_needs": "worn or held as appropriate",
        },
        "flat_lay": {
            "surface": "textured surface",
            "arrangement": "texture visible, flat or folded",
        },
        "lifestyle": {
            "context": "cozy lifestyle setting",
        },
        "ai_params": ["crochet_item_type"],
    },
    "hair_accessory": {
        "label": "Hair Accessories",
        "on_model": {
            "body_area": "hair and head",
            "framing": "head close-up or profile",
            "model_needs": "accessory in styled hair",
        },
        "flat_lay": {
            "surface": "display surface",
            "arrangement": "single or grouped",
        },
        "lifestyle": {
            "context": "profile or back-of-head shot",
        },
        "ai_params": ["hair_type_for_display"],
    },
}

DISPLAY_MODES = ["on_model", "flat_lay", "lifestyle"]

BACKGROUND_SURFACES = {
    "flat_lay": [
        "white_marble",
        "wooden_table",
        "velvet_fabric",
        "linen_cloth",
        "concrete",
        "rose_petals",
    ],
    "lifestyle": [
        "cafe",
        "garden",
        "beach",
        "urban_street",
        "cozy_room",
        "office",
    ],
}

# Convenience sets for validation
VALID_ACCESSORY_CATEGORIES = set(ACCESSORY_CATEGORIES.keys())
VALID_DISPLAY_MODES = set(DISPLAY_MODES)
VALID_BACKGROUND_SURFACES_FLAT_LAY = set(BACKGROUND_SURFACES["flat_lay"])
VALID_BACKGROUND_SURFACES_LIFESTYLE = set(BACKGROUND_SURFACES["lifestyle"])
