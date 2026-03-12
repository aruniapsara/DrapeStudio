"""
Gender-aware option definitions for all DrapeStudio modules.

Single source of truth for body types, hair styles, poses, and build options
filtered by gender. Injected into templates as JSON via Jinja2 context.

Gender key mapping (preserves existing values -- no migration):
  Adult:    feminine / masculine / neutral   (sessionStorage genderPresentation)
  Children: girl / boy / unisex              (sessionStorage childGender)
  Fit-on:   female / male                    (Alpine state customerGender)
"""

import json

# -- Adult: Body Types -----------------------------------------------------

BODY_TYPES = {
    "feminine": [
        {"id": "slim",      "label": {"en": "Slim",      "si": "\u0dc3\u0dd2\u0dc4\u0dd2\u0db1\u0dca",    "ta": "\u0bae\u0bc6\u0bb2\u0bbf\u0ba8\u0bcd\u0ba4"},      "icon": "\U0001f9cd"},
        {"id": "average",   "label": {"en": "Average",   "si": "\u0dc3\u0dcf\u0db8\u0dcf\u0db1\u0dca\u200d\u0dba",  "ta": "\u0b9a\u0bb0\u0bbe\u0b9a\u0bb0\u0bbf"},       "icon": "\U0001f6b6"},
        {"id": "curvy",     "label": {"en": "Curvy",     "si": "\u0dc0\u0d9a\u0dca\u200d\u0dbb",      "ta": "\u0bb5\u0bb3\u0bc8\u0bb5\u0bbe\u0ba9"},      "icon": "\U0001f483"},
        {"id": "plus_size", "label": {"en": "Plus Size", "si": "\u0dc0\u0dd2\u0dc1\u0dcf\u0dbd",     "ta": "\u0baa\u0bc6\u0bb0\u0bbf\u0baf \u0b85\u0bb3\u0bb5\u0bc1"}, "icon": "\U0001f938"},
    ],
    "masculine": [
        {"id": "slim",     "label": {"en": "Slim",        "si": "\u0dc3\u0dd2\u0dc4\u0dd2\u0db1\u0dca",       "ta": "\u0bae\u0bc6\u0bb2\u0bbf\u0ba8\u0bcd\u0ba4"},    "icon": "\U0001f9cd"},
        {"id": "average",  "label": {"en": "Average",     "si": "\u0dc3\u0dcf\u0db8\u0dcf\u0db1\u0dca\u200d\u0dba",     "ta": "\u0b9a\u0bb0\u0bbe\u0b9a\u0bb0\u0bbf"},     "icon": "\U0001f6b6"},
        {"id": "athletic", "label": {"en": "Athletic",    "si": "\u0d9a\u0dca\u200d\u0dbb\u0dd3\u0da9\u0dcf\u0dc1\u0dd3\u0dbd\u0dd3",  "ta": "\u0ba4\u0b9f\u0b95\u0bb3"},       "icon": "\U0001f3cb\ufe0f"},
        {"id": "heavy",    "label": {"en": "Heavy Build", "si": "\u0db6\u0dbb \u0dc3\u0dd2\u0dbb\u0dd4\u0dbb",     "ta": "\u0b95\u0ba9\u0bae\u0bbe\u0ba9 \u0b89\u0b9f\u0bb2\u0bcd"}, "icon": "\U0001f3c3"},
    ],
    "neutral": [
        {"id": "slim",      "label": {"en": "Slim",      "si": "\u0dc3\u0dd2\u0dc4\u0dd2\u0db1\u0dca",       "ta": "\u0bae\u0bc6\u0bb2\u0bbf\u0ba8\u0bcd\u0ba4"},      "icon": "\U0001f9cd"},
        {"id": "average",   "label": {"en": "Average",   "si": "\u0dc3\u0dcf\u0db8\u0dcf\u0db1\u0dca\u200d\u0dba",     "ta": "\u0b9a\u0bb0\u0bbe\u0b9a\u0bb0\u0bbf"},       "icon": "\U0001f6b6"},
        {"id": "athletic",  "label": {"en": "Athletic",  "si": "\u0d9a\u0dca\u200d\u0dbb\u0dd3\u0da9\u0dcf\u0dc1\u0dd3\u0dbd\u0dd3",  "ta": "\u0ba4\u0b9f\u0b95\u0bb3"},         "icon": "\U0001f3cb\ufe0f"},
        {"id": "plus_size", "label": {"en": "Plus Size", "si": "\u0dc0\u0dd2\u0dc1\u0dcf\u0dbd",        "ta": "\u0baa\u0bc6\u0bb0\u0bbf\u0baf \u0b85\u0bb3\u0bb5\u0bc1"},  "icon": "\U0001f938"},
    ],
}

# -- Adult: Hair Styles ----------------------------------------------------

HAIR_STYLES = {
    "feminine": [
        {"id": "long_straight",  "label": {"en": "Long Straight", "si": "\u0daf\u0dd2\u0d9c\u0dd4 \u0dc3\u0dd8\u0da2\u0dd4",    "ta": "\u0ba8\u0bc0\u0ba3\u0bcd\u0b9f \u0ba8\u0bc7\u0bb0\u0bbe\u0ba9"},   "icon": "\U0001f487\u200d\u2640\ufe0f"},
        {"id": "long_wavy",      "label": {"en": "Long Wavy",     "si": "\u0daf\u0dd2\u0d9c\u0dd4 \u0dbb\u0dd1\u0dc5\u0dd2",     "ta": "\u0ba8\u0bc0\u0ba3\u0bcd\u0b9f \u0b85\u0bb2\u0bc8"},     "icon": "\U0001f30a"},
        {"id": "medium_layered", "label": {"en": "Med Layered",   "si": "\u0db8\u0db0\u0dca\u200d\u0dba\u0db8 \u0dc3\u0dca\u0dae\u0dbb",   "ta": "\u0ba8\u0b9f\u0bc1\u0ba4\u0bcd\u0ba4\u0bb0 \u0b85\u0b9f\u0bc1\u0b95\u0bcd\u0b95\u0bc1"}, "icon": "\u2702\ufe0f"},
        {"id": "short_bob",      "label": {"en": "Short Bob",     "si": "\u0d9a\u0dd9\u0da7\u0dd2 \u0db6\u0ddc\u0db6\u0dca",     "ta": "\u0b95\u0bc1\u0bb1\u0bc1\u0b95\u0bbf\u0baf \u0baa\u0bbe\u0baa\u0bcd"},   "icon": "\U0001f469"},
        {"id": "curly",          "label": {"en": "Curly",         "si": "\u0dbb\u0dd1\u0dbd\u0dd2 \u0dc3\u0dc4\u0dd2\u0dad",     "ta": "\u0b9a\u0bc1\u0bb0\u0bc1\u0b9f\u0bcd\u0b9f\u0bc8"},       "icon": "\U0001f300"},
        {"id": "braided",        "label": {"en": "Braided",       "si": "\u0d9c\u0dd9\u0dad\u0dd6",          "ta": "\u0baa\u0bbf\u0ba9\u0bcd\u0ba9\u0bb2\u0bcd"},        "icon": "\U0001f380"},
        {"id": "bun",            "label": {"en": "Bun/Updo",      "si": "\u0d9a\u0ddc\u0dab\u0dca\u0da9\u0dba",        "ta": "\u0bae\u0bc1\u0b9f\u0bbf\u0b9a\u0bcd\u0b9a\u0bc1"},       "icon": "\U0001f486\u200d\u2640\ufe0f"},
    ],
    "masculine": [
        {"id": "short_crop",   "label": {"en": "Short Crop",   "si": "\u0d9a\u0dd9\u0da7\u0dd2 \u0d9a\u0db4\u0dcf",    "ta": "\u0b95\u0bc1\u0bb1\u0bc1\u0b95\u0bbf\u0baf \u0bb5\u0bc6\u0b9f\u0bcd\u0b9f\u0bc1"},          "icon": "\U0001f487\u200d\u2642\ufe0f"},
        {"id": "side_part",    "label": {"en": "Side Part",    "si": "\u0db8\u0db0\u0dca\u200d\u0dba\u0db8 \u0db4\u0dd1\u0dad\u0dca\u0dad", "ta": "\u0ba8\u0b9f\u0bc1\u0ba4\u0bcd\u0ba4\u0bb0 \u0baa\u0b95\u0bcd\u0b95"},            "icon": "\U0001f488"},
        {"id": "slicked_back", "label": {"en": "Slicked Back", "si": "\u0db4\u0dd2\u0da7\u0dd4\u0db4\u0dc3\u0da7",      "ta": "\u0baa\u0bbf\u0ba9\u0bcd\u0ba9\u0bbe\u0bb2\u0bcd \u0bb5\u0bb4\u0bc1\u0bb5\u0bb4\u0bc1\u0baa\u0bcd\u0baa\u0bbe\u0ba9"},    "icon": "\u2b05\ufe0f"},
        {"id": "curly_short",  "label": {"en": "Curly Short",  "si": "\u0dbb\u0dd1\u0dbd\u0dd2 \u0d9a\u0dd9\u0da7\u0dd2",    "ta": "\u0b9a\u0bc1\u0bb0\u0bc1\u0b9f\u0bcd\u0b9f\u0bc8 \u0b95\u0bc1\u0bb1\u0bc1\u0b95\u0bbf\u0baf"},         "icon": "\U0001f300"},
        {"id": "buzz_cut",     "label": {"en": "Buzz Cut",     "si": "\u0db6\u0dc3\u0dca \u0d9a\u0da7\u0dca",      "ta": "\u0baa\u0bb8\u0bcd \u0b95\u0b9f\u0bcd"},                 "icon": "\u26a1"},
        {"id": "long",         "label": {"en": "Long",         "si": "\u0daf\u0dd2\u0d9c\u0dd4",          "ta": "\u0ba8\u0bc0\u0ba3\u0bcd\u0b9f"},                   "icon": "\U0001f3b8"},
    ],
    "neutral": [
        {"id": "short_straight", "label": {"en": "Short",         "si": "\u0d9a\u0dd9\u0da7\u0dd2",          "ta": "\u0b95\u0bc1\u0bb1\u0bc1\u0b95\u0bbf\u0baf"},     "icon": "\u2702\ufe0f"},
        {"id": "medium_length",  "label": {"en": "Medium",        "si": "\u0db8\u0db0\u0dca\u200d\u0dba\u0db8",         "ta": "\u0ba8\u0b9f\u0bc1\u0ba4\u0bcd\u0ba4\u0bb0"},     "icon": "\U0001f481"},
        {"id": "long_straight",  "label": {"en": "Long Straight", "si": "\u0daf\u0dd2\u0d9c\u0dd4 \u0dc3\u0dd8\u0da2\u0dd4",     "ta": "\u0ba8\u0bc0\u0ba3\u0bcd\u0b9f \u0ba8\u0bc7\u0bb0\u0bbe\u0ba9"}, "icon": "\U0001f487"},
        {"id": "shaved",         "label": {"en": "Shaved",        "si": "\u0db6\u0ddd\u0dc0\u0dd6",          "ta": "\u0bae\u0bca\u0b9f\u0bcd\u0b9f\u0bc8"},      "icon": "\u26a1"},
        {"id": "natural_curly",  "label": {"en": "Curly",         "si": "\u0dbb\u0dd1\u0dbd\u0dd2 \u0dc3\u0dc4\u0dd2\u0dad",     "ta": "\u0b9a\u0bc1\u0bb0\u0bc1\u0b9f\u0bcd\u0b9f\u0bc8"},    "icon": "\U0001f300"},
    ],
}

# -- Adult: Poses ----------------------------------------------------------

POSES = {
    "feminine": [
        {"id": "fashion_standing", "label": {"en": "Fashion Stand",  "si": "\u0dc0\u0dd2\u0dbd\u0dcf\u0dc3\u0dd2\u0dad\u0dcf \u0d89\u0dbb\u0dd2\u0dba\u0dc0\u0dca\u0dc0", "ta": "\u0baa\u0bc7\u0bb7\u0ba9\u0bcd \u0ba8\u0bbf\u0bb1\u0bcd\u0baa\u0ba4\u0bc1"}, "icon": "\U0001f483"},
        {"id": "casual_walking",   "label": {"en": "Casual Walk",    "si": "\u0dc3\u0dcf\u0db8\u0dcf\u0db1\u0dca\u200d\u0dba \u0d87\u0dc0\u0dd2\u0daf\u0dd3\u0db8",   "ta": "\u0b9a\u0bbe\u0ba4\u0bbe\u0bb0\u0ba3 \u0ba8\u0b9f\u0bc8"},    "icon": "\U0001f6b6\u200d\u2640\ufe0f"},
        {"id": "seated_elegant",   "label": {"en": "Seated Elegant", "si": "\u0d85\u0dbd\u0d82\u0d9a\u0dcf\u0dbb \u0dc0\u0dcf\u0da9\u0dd2\u0dc0",      "ta": "\u0ba8\u0bc7\u0bb0\u0bcd\u0ba4\u0bcd\u0ba4\u0bbf\u0baf\u0bbe\u0ba9 \u0b85\u0bae\u0bb0\u0bcd\u0bb5\u0bc1"}, "icon": "\U0001fa91"},
        {"id": "hand_on_hip",      "label": {"en": "Hand on Hip",    "si": "\u0d89\u0dab \u0db8\u0dad \u0d85\u0dad",          "ta": "\u0b87\u0b9f\u0bc1\u0baa\u0bcd\u0baa\u0bbf\u0bb2\u0bcd \u0b95\u0bc8"},  "icon": "\U0001f933"},
    ],
    "masculine": [
        {"id": "standing_confident", "label": {"en": "Confident Stand",  "si": "\u0dc0\u0dd2\u0dc1\u0dca\u0dc0\u0dcf\u0dc3\u0dd3 \u0d89\u0dbb\u0dd2\u0dba\u0dc0\u0dca\u0dc0",   "ta": "\u0ba8\u0bae\u0bcd\u0baa\u0bbf\u0b95\u0bcd\u0b95\u0bc8\u0baf\u0bbe\u0ba9 \u0ba8\u0bbf\u0bb1\u0bcd\u0baa\u0ba4\u0bc1"}, "icon": "\U0001f9cd\u200d\u2642\ufe0f"},
        {"id": "casual_walking",     "label": {"en": "Casual Walk",      "si": "\u0dc3\u0dcf\u0db8\u0dcf\u0db1\u0dca\u200d\u0dba \u0d87\u0dc0\u0dd2\u0daf\u0dd3\u0db8",     "ta": "\u0b9a\u0bbe\u0ba4\u0bbe\u0bb0\u0ba3 \u0ba8\u0b9f\u0bc8"},          "icon": "\U0001f6b6\u200d\u2642\ufe0f"},
        {"id": "hands_in_pockets",   "label": {"en": "Hands in Pockets", "si": "\u0dc3\u0dcf\u0d9a\u0dca\u0d9a\u0dd4\u0dc0\u0dbd \u0d85\u0dad\u0dca",        "ta": "\u0b9a\u0b9f\u0bcd\u0b9f\u0bc8\u0baa\u0bcd \u0baa\u0bc8\u0baf\u0bbf\u0bb2\u0bcd \u0b95\u0bc8\u0b95\u0bb3\u0bcd"}, "icon": "\U0001f9d1"},
        {"id": "seated_casual",      "label": {"en": "Seated Casual",    "si": "\u0dc3\u0dcf\u0db8\u0dcf\u0db1\u0dca\u200d\u0dba \u0dc0\u0dcf\u0da9\u0dd2\u0dc0",      "ta": "\u0b9a\u0bbe\u0ba4\u0bbe\u0bb0\u0ba3 \u0b85\u0bae\u0bb0\u0bcd\u0bb5\u0bc1"},       "icon": "\U0001fa91"},
    ],
    "neutral": [
        {"id": "front_standing", "label": {"en": "Fashion Stand", "si": "\u0dc0\u0dd2\u0dbd\u0dcf\u0dc3\u0dd2\u0dad\u0dcf \u0d89\u0dbb\u0dd2\u0dba\u0dc0\u0dca\u0dc0", "ta": "\u0baa\u0bc7\u0bb7\u0ba9\u0bcd \u0ba8\u0bbf\u0bb1\u0bcd\u0baa\u0ba4\u0bc1"}, "icon": "\U0001f9cd"},
        {"id": "casual_walking", "label": {"en": "Casual Walk",   "si": "\u0dc3\u0dcf\u0db8\u0dcf\u0db1\u0dca\u200d\u0dba \u0d87\u0dc0\u0dd2\u0daf\u0dd3\u0db8",   "ta": "\u0b9a\u0bbe\u0ba4\u0bbe\u0bb0\u0ba3 \u0ba8\u0b9f\u0bc8"},    "icon": "\U0001f6b6"},
        {"id": "seated",         "label": {"en": "Seated",        "si": "\u0dc0\u0dcf\u0da9\u0dd2\u0dc0",             "ta": "\u0b85\u0bae\u0bb0\u0bcd\u0bb5\u0bc1"},        "icon": "\U0001fa91"},
        {"id": "dynamic",        "label": {"en": "Dynamic",       "si": "\u0d9c\u0dad\u0dd2\u0d9a",               "ta": "\u0b9f\u0bc8\u0ba9\u0bae\u0bbf\u0b95\u0bcd"},      "icon": "\U0001f483"},
    ],
}

# -- Fit-on: Build ---------------------------------------------------------
# NOTE: uses hyphenated "plus-size" to match existing fiton buildToMeasurements

FITON_BUILD = {
    "female": [
        {"id": "slim",      "label": {"en": "Slim",      "si": "\u0dc3\u0dd2\u0dc4\u0dd2\u0db1\u0dca",    "ta": "\u0bae\u0bc6\u0bb2\u0bbf\u0ba8\u0bcd\u0ba4"},      "desc": {"en": "Smaller frame",   "si": "\u0d9a\u0dd4\u0da9\u0dcf \u0dbb\u0dcf\u0db8\u0dd4\u0dc0",    "ta": "\u0b9a\u0bbf\u0bb1\u0bbf\u0baf \u0b89\u0b9f\u0bb2\u0bcd"}},
        {"id": "medium",    "label": {"en": "Medium",    "si": "\u0db8\u0db0\u0dca\u200d\u0dba\u0db8",     "ta": "\u0ba8\u0b9f\u0bc1\u0ba4\u0bcd\u0ba4\u0bb0"},      "desc": {"en": "Average frame",   "si": "\u0dc3\u0dcf\u0db8\u0dcf\u0db1\u0dca\u200d\u0dba \u0dbb\u0dcf\u0db8\u0dd4\u0dc0", "ta": "\u0b9a\u0bb0\u0bbe\u0b9a\u0bb0\u0bbf \u0b89\u0b9f\u0bb2\u0bcd"}},
        {"id": "curvy",     "label": {"en": "Curvy",     "si": "\u0dc0\u0d9a\u0dca\u200d\u0dbb",      "ta": "\u0bb5\u0bb3\u0bc8\u0bb5\u0bbe\u0ba9"},      "desc": {"en": "Fuller hips/bust", "si": "\u0db4\u0dd2\u0dbb\u0dd4\u0dab\u0dd4 \u0d89\u0dab/\u0dc5\u0dba",   "ta": "\u0ba8\u0bbf\u0bb0\u0bae\u0bcd\u0baa\u0bbf\u0baf \u0b87\u0b9f\u0bc1\u0baa\u0bcd\u0baa\u0bc1"}},
        {"id": "plus-size", "label": {"en": "Plus Size", "si": "\u0dc0\u0dd2\u0dc1\u0dcf\u0dbd",     "ta": "\u0baa\u0bc6\u0bb0\u0bbf\u0baf \u0b85\u0bb3\u0bb5\u0bc1"}, "desc": {"en": "Larger frame",    "si": "\u0dc0\u0dd2\u0dc1\u0dcf\u0dbd \u0dbb\u0dcf\u0db8\u0dd4\u0dc0",    "ta": "\u0baa\u0bc6\u0bb0\u0bbf\u0baf \u0b89\u0b9f\u0bb2\u0bcd"}},
    ],
    "male": [
        {"id": "slim",     "label": {"en": "Slim",        "si": "\u0dc3\u0dd2\u0dc4\u0dd2\u0db1\u0dca",       "ta": "\u0bae\u0bc6\u0bb2\u0bbf\u0ba8\u0bcd\u0ba4"},      "desc": {"en": "Lean frame",      "si": "\u0dc3\u0dd2\u0dc4\u0dd2\u0db1\u0dca \u0dbb\u0dcf\u0db8\u0dd4\u0dc0",    "ta": "\u0bae\u0bc6\u0bb2\u0bcd\u0bb2\u0bbf\u0baf \u0b89\u0b9f\u0bb2\u0bcd"}},
        {"id": "medium",   "label": {"en": "Medium",      "si": "\u0db8\u0db0\u0dca\u200d\u0dba\u0db8",        "ta": "\u0ba8\u0b9f\u0bc1\u0ba4\u0bcd\u0ba4\u0bb0"},      "desc": {"en": "Average frame",   "si": "\u0dc3\u0dcf\u0db8\u0dcf\u0db1\u0dca\u200d\u0dba \u0dbb\u0dcf\u0db8\u0dd4\u0dc0",  "ta": "\u0b9a\u0bb0\u0bbe\u0b9a\u0bb0\u0bbf \u0b89\u0b9f\u0bb2\u0bcd"}},
        {"id": "athletic", "label": {"en": "Athletic",    "si": "\u0d9a\u0dca\u200d\u0dbb\u0dd3\u0da9\u0dcf\u0dc1\u0dd3\u0dbd\u0dd3",  "ta": "\u0ba4\u0b9f\u0b95\u0bb3"},         "desc": {"en": "Muscular frame",  "si": "\u0db8\u0dcf\u0d82\u0dc1 \u0db4\u0dda\u0dc1\u0dd2 \u0dbb\u0dcf\u0db8\u0dd4\u0dc0", "ta": "\u0ba4\u0b9a\u0bc8 \u0b89\u0b9f\u0bb2\u0bcd"}},
        {"id": "heavy",    "label": {"en": "Heavy Build", "si": "\u0db6\u0dbb \u0dc3\u0dd2\u0dbb\u0dd4\u0dbb",     "ta": "\u0b95\u0ba9\u0bae\u0bbe\u0ba9 \u0b89\u0b9f\u0bb2\u0bcd"},  "desc": {"en": "Broad frame",     "si": "\u0db4\u0dc5\u0dbd\u0dca \u0dbb\u0dcf\u0db8\u0dd4\u0dc0",     "ta": "\u0b85\u0b95\u0bb2\u0bae\u0bbe\u0ba9 \u0b89\u0b9f\u0bb2\u0bcd"}},
    ],
}

# -- Children: Hair (age x gender) -----------------------------------------

CHILDREN_HAIR = {
    "baby": {
        "girl":   [{"id": "none",   "label": {"en": "None / Natural", "si": "\u0dc3\u0dca\u0dc0\u0dcf\u0db7\u0dcf\u0dc0\u0dd2\u0d9a", "ta": "\u0b87\u0baf\u0bb1\u0bcd\u0b95\u0bc8"}, "icon": "\u2728"},
                   {"id": "bonnet", "label": {"en": "Bonnet",         "si": "\u0db6\u0ddc\u0db1\u0da7\u0dca",  "ta": "\u0ba4\u0bca\u0baa\u0bcd\u0baa\u0bbf"}, "icon": "\U0001f380"},
                   {"id": "cap",    "label": {"en": "Cap",            "si": "\u0dad\u0ddc\u0db4\u0dca\u0db4\u0dd2\u0dba", "ta": "\u0ba4\u0bca\u0baa\u0bcd\u0baa\u0bbf"}, "icon": "\U0001f9e2"}],
        "boy":    [{"id": "none",   "label": {"en": "None / Natural", "si": "\u0dc3\u0dca\u0dc0\u0dcf\u0db7\u0dcf\u0dc0\u0dd2\u0d9a", "ta": "\u0b87\u0baf\u0bb1\u0bcd\u0b95\u0bc8"}, "icon": "\u2728"},
                   {"id": "bonnet", "label": {"en": "Bonnet",         "si": "\u0db6\u0ddc\u0db1\u0da7\u0dca",  "ta": "\u0ba4\u0bca\u0baa\u0bcd\u0baa\u0bbf"}, "icon": "\U0001f380"},
                   {"id": "cap",    "label": {"en": "Cap",            "si": "\u0dad\u0ddc\u0db4\u0dca\u0db4\u0dd2\u0dba", "ta": "\u0ba4\u0bca\u0baa\u0bcd\u0baa\u0bbf"}, "icon": "\U0001f9e2"}],
        "unisex": [{"id": "none",   "label": {"en": "None / Natural", "si": "\u0dc3\u0dca\u0dc0\u0dcf\u0db7\u0dcf\u0dc0\u0dd2\u0d9a", "ta": "\u0b87\u0baf\u0bb1\u0bcd\u0b95\u0bc8"}, "icon": "\u2728"},
                   {"id": "bonnet", "label": {"en": "Bonnet",         "si": "\u0db6\u0ddc\u0db1\u0da7\u0dca",  "ta": "\u0ba4\u0bca\u0baa\u0bcd\u0baa\u0bbf"}, "icon": "\U0001f380"},
                   {"id": "cap",    "label": {"en": "Cap",            "si": "\u0dad\u0ddc\u0db4\u0dca\u0db4\u0dd2\u0dba", "ta": "\u0ba4\u0bca\u0baa\u0bcd\u0baa\u0bbf"}, "icon": "\U0001f9e2"}],
    },
    "toddler": {
        "girl":   [{"id": "short",      "label": {"en": "Short",      "si": "\u0d9a\u0dd9\u0da7\u0dd2",       "ta": "\u0b95\u0bc1\u0bb1\u0bc1\u0b95\u0bbf\u0baf"},  "icon": "\u2702\ufe0f"},
                   {"id": "curly",      "label": {"en": "Curly",      "si": "\u0dbb\u0dd1\u0dbd\u0dd2 \u0dc3\u0dc4\u0dd2\u0dad",  "ta": "\u0b9a\u0bc1\u0bb0\u0bc1\u0b9f\u0bcd\u0b9f\u0bc8"}, "icon": "\U0001f300"},
                   {"id": "with_bow",   "label": {"en": "With Bow",   "si": "\u0db4\u0dd3\u0dad\u0dd2 \u0dc3\u0dc4\u0dd2\u0dad",  "ta": "\u0bb5\u0bbf\u0bb2\u0bcd\u0bb2\u0bc1\u0b9f\u0ba9\u0bcd"}, "icon": "\U0001f380"},
                   {"id": "with_clips", "label": {"en": "With Clips", "si": "\u0d9a\u0dca\u0dbd\u0dd2\u0db4\u0dca \u0dc3\u0dc4\u0dd2\u0dad", "ta": "\u0b95\u0bbf\u0bb3\u0bbf\u0baa\u0bcd\u0b95\u0bb3\u0bc1\u0b9f\u0ba9\u0bcd"}, "icon": "\U0001f4ce"}],
        "boy":    [{"id": "short",      "label": {"en": "Short",      "si": "\u0d9a\u0dd9\u0da7\u0dd2",       "ta": "\u0b95\u0bc1\u0bb1\u0bc1\u0b95\u0bbf\u0baf"},  "icon": "\u2702\ufe0f"},
                   {"id": "curly",      "label": {"en": "Curly",      "si": "\u0dbb\u0dd1\u0dbd\u0dd2 \u0dc3\u0dc4\u0dd2\u0dad",  "ta": "\u0b9a\u0bc1\u0bb0\u0bc1\u0b9f\u0bcd\u0b9f\u0bc8"}, "icon": "\U0001f300"}],
        "unisex": [{"id": "short",      "label": {"en": "Short",      "si": "\u0d9a\u0dd9\u0da7\u0dd2",       "ta": "\u0b95\u0bc1\u0bb1\u0bc1\u0b95\u0bbf\u0baf"},  "icon": "\u2702\ufe0f"},
                   {"id": "curly",      "label": {"en": "Curly",      "si": "\u0dbb\u0dd1\u0dbd\u0dd2 \u0dc3\u0dc4\u0dd2\u0dad",  "ta": "\u0b9a\u0bc1\u0bb0\u0bc1\u0b9f\u0bcd\u0b9f\u0bc8"}, "icon": "\U0001f300"},
                   {"id": "with_bow",   "label": {"en": "With Bow",   "si": "\u0db4\u0dd3\u0dad\u0dd2 \u0dc3\u0dc4\u0dd2\u0dad",  "ta": "\u0bb5\u0bbf\u0bb2\u0bcd\u0bb2\u0bc1\u0b9f\u0ba9\u0bcd"}, "icon": "\U0001f380"},
                   {"id": "with_clips", "label": {"en": "With Clips", "si": "\u0d9a\u0dca\u0dbd\u0dd2\u0db4\u0dca \u0dc3\u0dc4\u0dd2\u0dad", "ta": "\u0b95\u0bbf\u0bb3\u0bbf\u0baa\u0bcd\u0b95\u0bb3\u0bc1\u0b9f\u0ba9\u0bcd"}, "icon": "\U0001f4ce"}],
    },
    "kid": {
        "girl":   [{"id": "short",    "label": {"en": "Short",    "si": "\u0d9a\u0dd9\u0da7\u0dd2",       "ta": "\u0b95\u0bc1\u0bb1\u0bc1\u0b95\u0bbf\u0baf"},  "icon": "\u2702\ufe0f"},
                   {"id": "medium",   "label": {"en": "Medium",   "si": "\u0db8\u0db0\u0dca\u200d\u0dba\u0db8",      "ta": "\u0ba8\u0b9f\u0bc1\u0ba4\u0bcd\u0ba4\u0bb0"},  "icon": "\U0001f486"},
                   {"id": "long",     "label": {"en": "Long",     "si": "\u0daf\u0dd2\u0d9c\u0dd4",        "ta": "\u0ba8\u0bc0\u0ba3\u0bcd\u0b9f"},    "icon": "\U0001f487"},
                   {"id": "ponytail", "label": {"en": "Ponytail", "si": "\u0db4\u0ddd\u0db1\u0dd2\u0da7\u0dda\u0dbd\u0dca",   "ta": "\u0baa\u0bcb\u0ba9\u0bbf\u0b9f\u0bc6\u0baf\u0bbf\u0bb2\u0bcd"}, "icon": "\U0001f434"},
                   {"id": "braids",   "label": {"en": "Braids",   "si": "\u0d9c\u0dd9\u0dad\u0dd6",        "ta": "\u0baa\u0bbf\u0ba9\u0bcd\u0ba9\u0bb2\u0bcd"},  "icon": "\U0001f9f6"},
                   {"id": "curly",    "label": {"en": "Curly",    "si": "\u0dbb\u0dd1\u0dbd\u0dd2 \u0dc3\u0dc4\u0dd2\u0dad",   "ta": "\u0b9a\u0bc1\u0bb0\u0bc1\u0b9f\u0bcd\u0b9f\u0bc8"}, "icon": "\U0001f300"}],
        "boy":    [{"id": "short",      "label": {"en": "Short",      "si": "\u0d9a\u0dd9\u0da7\u0dd2",       "ta": "\u0b95\u0bc1\u0bb1\u0bc1\u0b95\u0bbf\u0baf"},       "icon": "\u2702\ufe0f"},
                   {"id": "buzz",       "label": {"en": "Buzz Cut",   "si": "\u0db6\u0dc3\u0dca \u0d9a\u0da7\u0dca",    "ta": "\u0baa\u0bb8\u0bcd \u0b95\u0b9f\u0bcd"},       "icon": "\u26a1"},
                   {"id": "curly",      "label": {"en": "Curly",      "si": "\u0dbb\u0dd1\u0dbd\u0dd2 \u0dc3\u0dc4\u0dd2\u0dad",  "ta": "\u0b9a\u0bc1\u0bb0\u0bc1\u0b9f\u0bcd\u0b9f\u0bc8"},      "icon": "\U0001f300"},
                   {"id": "side_part",  "label": {"en": "Side Part",  "si": "\u0db4\u0dd1\u0dad\u0dca\u0dad \u0d9a\u0ddc\u0da7\u0dc3", "ta": "\u0baa\u0b95\u0bcd\u0b95 \u0bb5\u0b95\u0bc1\u0baa\u0bcd\u0baa\u0bc1"},  "icon": "\U0001f488"}],
        "unisex": [{"id": "short",    "label": {"en": "Short",    "si": "\u0d9a\u0dd9\u0da7\u0dd2",       "ta": "\u0b95\u0bc1\u0bb1\u0bc1\u0b95\u0bbf\u0baf"},  "icon": "\u2702\ufe0f"},
                   {"id": "medium",   "label": {"en": "Medium",   "si": "\u0db8\u0db0\u0dca\u200d\u0dba\u0db8",      "ta": "\u0ba8\u0b9f\u0bc1\u0ba4\u0bcd\u0ba4\u0bb0"},  "icon": "\U0001f486"},
                   {"id": "long",     "label": {"en": "Long",     "si": "\u0daf\u0dd2\u0d9c\u0dd4",        "ta": "\u0ba8\u0bc0\u0ba3\u0bcd\u0b9f"},    "icon": "\U0001f487"},
                   {"id": "ponytail", "label": {"en": "Ponytail", "si": "\u0db4\u0ddd\u0db1\u0dd2\u0da7\u0dda\u0dbd\u0dca",   "ta": "\u0baa\u0bcb\u0ba9\u0bbf\u0b9f\u0bc6\u0baf\u0bbf\u0bb2\u0bcd"}, "icon": "\U0001f434"},
                   {"id": "braids",   "label": {"en": "Braids",   "si": "\u0d9c\u0dd9\u0dad\u0dd6",        "ta": "\u0baa\u0bbf\u0ba9\u0bcd\u0ba9\u0bb2\u0bcd"},  "icon": "\U0001f9f6"},
                   {"id": "curly",    "label": {"en": "Curly",    "si": "\u0dbb\u0dd1\u0dbd\u0dd2 \u0dc3\u0dc4\u0dd2\u0dad",   "ta": "\u0b9a\u0bc1\u0bb0\u0bc1\u0b9f\u0bcd\u0b9f\u0bc8"}, "icon": "\U0001f300"}],
    },
    "teen": {
        "girl":   [{"id": "short",    "label": {"en": "Short",    "si": "\u0d9a\u0dd9\u0da7\u0dd2",       "ta": "\u0b95\u0bc1\u0bb1\u0bc1\u0b95\u0bbf\u0baf"},       "icon": "\u2702\ufe0f"},
                   {"id": "medium",   "label": {"en": "Medium",   "si": "\u0db8\u0db0\u0dca\u200d\u0dba\u0db8",      "ta": "\u0ba8\u0b9f\u0bc1\u0ba4\u0bcd\u0ba4\u0bb0"},      "icon": "\U0001f486"},
                   {"id": "long",     "label": {"en": "Long",     "si": "\u0daf\u0dd2\u0d9c\u0dd4",        "ta": "\u0ba8\u0bc0\u0ba3\u0bcd\u0b9f"},        "icon": "\U0001f487"},
                   {"id": "ponytail", "label": {"en": "Ponytail", "si": "\u0db4\u0ddd\u0db1\u0dd2\u0da7\u0dda\u0dbd\u0dca",   "ta": "\u0baa\u0bcb\u0ba9\u0bbf\u0b9f\u0bc6\u0baf\u0bbf\u0bb2\u0bcd"},   "icon": "\U0001f434"},
                   {"id": "braids",   "label": {"en": "Braids",   "si": "\u0d9c\u0dd9\u0dad\u0dd6",        "ta": "\u0baa\u0bbf\u0ba9\u0bcd\u0ba9\u0bb2\u0bcd"},     "icon": "\U0001f9f6"},
                   {"id": "curly",    "label": {"en": "Curly",    "si": "\u0dbb\u0dd1\u0dbd\u0dd2 \u0dc3\u0dc4\u0dd2\u0dad",   "ta": "\u0b9a\u0bc1\u0bb0\u0bc1\u0b9f\u0bcd\u0b9f\u0bc8"},    "icon": "\U0001f300"},
                   {"id": "trending", "label": {"en": "Trending", "si": "\u0da2\u0db1\u0db4\u0dca\u200d\u0dbb\u0dd2\u0dba",    "ta": "\u0b9f\u0bbf\u0bb0\u0bc6\u0ba3\u0bcd\u0b9f\u0bbf\u0b99\u0bcd"},  "icon": "\u2728"}],
        "boy":    [{"id": "short",      "label": {"en": "Short",      "si": "\u0d9a\u0dd9\u0da7\u0dd2",       "ta": "\u0b95\u0bc1\u0bb1\u0bc1\u0b95\u0bbf\u0baf"},       "icon": "\u2702\ufe0f"},
                   {"id": "buzz",       "label": {"en": "Buzz Cut",   "si": "\u0db6\u0dc3\u0dca \u0d9a\u0da7\u0dca",    "ta": "\u0baa\u0bb8\u0bcd \u0b95\u0b9f\u0bcd"},       "icon": "\u26a1"},
                   {"id": "curly",      "label": {"en": "Curly",      "si": "\u0dbb\u0dd1\u0dbd\u0dd2 \u0dc3\u0dc4\u0dd2\u0dad",  "ta": "\u0b9a\u0bc1\u0bb0\u0bc1\u0b9f\u0bcd\u0b9f\u0bc8"},      "icon": "\U0001f300"},
                   {"id": "side_part",  "label": {"en": "Side Part",  "si": "\u0db4\u0dd1\u0dad\u0dca\u0dad \u0d9a\u0ddc\u0da7\u0dc3", "ta": "\u0baa\u0b95\u0bcd\u0b95 \u0bb5\u0b95\u0bc1\u0baa\u0bcd\u0baa\u0bc1"},  "icon": "\U0001f488"},
                   {"id": "trending",   "label": {"en": "Trending",   "si": "\u0da2\u0db1\u0db4\u0dca\u200d\u0dbb\u0dd2\u0dba",   "ta": "\u0b9f\u0bbf\u0bb0\u0bc6\u0ba3\u0bcd\u0b9f\u0bbf\u0b99\u0bcd"},   "icon": "\u2728"}],
        "unisex": [{"id": "short",    "label": {"en": "Short",    "si": "\u0d9a\u0dd9\u0da7\u0dd2",       "ta": "\u0b95\u0bc1\u0bb1\u0bc1\u0b95\u0bbf\u0baf"},       "icon": "\u2702\ufe0f"},
                   {"id": "medium",   "label": {"en": "Medium",   "si": "\u0db8\u0db0\u0dca\u200d\u0dba\u0db8",      "ta": "\u0ba8\u0b9f\u0bc1\u0ba4\u0bcd\u0ba4\u0bb0"},      "icon": "\U0001f486"},
                   {"id": "long",     "label": {"en": "Long",     "si": "\u0daf\u0dd2\u0d9c\u0dd4",        "ta": "\u0ba8\u0bc0\u0ba3\u0bcd\u0b9f"},        "icon": "\U0001f487"},
                   {"id": "ponytail", "label": {"en": "Ponytail", "si": "\u0db4\u0ddd\u0db1\u0dd2\u0da7\u0dda\u0dbd\u0dca",   "ta": "\u0baa\u0bcb\u0ba9\u0bbf\u0b9f\u0bc6\u0baf\u0bbf\u0bb2\u0bcd"},   "icon": "\U0001f434"},
                   {"id": "braids",   "label": {"en": "Braids",   "si": "\u0d9c\u0dd9\u0dad\u0dd6",        "ta": "\u0baa\u0bbf\u0ba9\u0bcd\u0ba9\u0bb2\u0bcd"},     "icon": "\U0001f9f6"},
                   {"id": "curly",    "label": {"en": "Curly",    "si": "\u0dbb\u0dd1\u0dbd\u0dd2 \u0dc3\u0dc4\u0dd2\u0dad",   "ta": "\u0b9a\u0bc1\u0bb0\u0bc1\u0b9f\u0bcd\u0b9f\u0bc8"},    "icon": "\U0001f300"},
                   {"id": "trending", "label": {"en": "Trending", "si": "\u0da2\u0db1\u0db4\u0dca\u200d\u0dbb\u0dd2\u0dba",    "ta": "\u0b9f\u0bbf\u0bb0\u0bc6\u0ba3\u0bcd\u0b9f\u0bbf\u0b99\u0bcd"},  "icon": "\u2728"}],
    },
}


def get_adult_options_json() -> str:
    """Return JSON string with BODY_TYPES, HAIR_STYLES, POSES for adult configure page."""
    return json.dumps({
        "BODY_TYPES": BODY_TYPES,
        "HAIR_STYLES": HAIR_STYLES,
        "POSES": POSES,
    }, ensure_ascii=False)


def get_children_hair_json() -> str:
    """Return JSON string with CHILDREN_HAIR for children configure page."""
    return json.dumps(CHILDREN_HAIR, ensure_ascii=False)


def get_fiton_build_json() -> str:
    """Return JSON string with FITON_BUILD for fiton customer details page."""
    return json.dumps(FITON_BUILD, ensure_ascii=False)
