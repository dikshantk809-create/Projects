"""What to do about what the camera found, for vegetable crops.

This is a lookup table, not a brain. The rover detects a condition, looks it up
here, and tells you what it plans to do. It is written for the vegetables most
people grow in a kitchen plot: tomato, brinjal, chilli, okra, cabbage,
cauliflower, cucumber, bean and potato.

READ THIS BEFORE YOU LET IT SPRAY ANYTHING
  - These are common recommendations, not a prescription. Rules about which
    products may be used, at what dose, and how long before you can pick the
    crop, are different in every country and change every year.
  - Always read the label on the bottle you actually have. The label wins.
  - "phi_days" below is the pre harvest interval: the number of days you must
    wait after spraying before the vegetable is safe to pick. Respect it.
  - Start with the non chemical option where there is one. Most early problems
    on a small plot are fixed by removing the affected leaf and watering
    differently.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Treatment:
    label: str
    common_name: str
    kind: str                 # fungal | bacterial | viral | pest | deficiency | weed | ok
    severity_hint: str
    first_try: str            # what to do before reaching for a bottle
    product: str              # the usual chemical, if one is needed
    dose: str
    dose_ml_per_plant: float  # what the rover will actually squirt
    phi_days: int             # wait this long before you pick the crop
    spray_ok: bool            # may the rover apply this on its own
    note: str


# label strings must match the model's labels.txt
TREATMENTS: Dict[str, Treatment] = {
    "healthy": Treatment(
        "healthy", "Healthy plant", "ok", "none",
        "Nothing to do. Keep watering evenly.",
        "", "", 0.0, 0, False,
        "Logged so you can see the plant was checked."),

    "tomato_early_blight": Treatment(
        "tomato_early_blight", "Tomato early blight", "fungal", "spreads slowly",
        "Pick off the spotted lower leaves and bin them. Do not wet the leaves "
        "when you water. Mulch the soil.",
        "Mancozeb 75% WP", "2 g per litre of water", 12.0, 5, True,
        "Dark rings on the older leaves near the ground. Very common in "
        "warm humid weather."),

    "tomato_late_blight": Treatment(
        "tomato_late_blight", "Tomato late blight", "fungal", "spreads fast",
        "Remove and burn the affected plant parts today, not tomorrow. "
        "Improve air flow between plants.",
        "Metalaxyl + Mancozeb", "2 g per litre of water", 15.0, 7, True,
        "Greasy grey green patches that go brown fast. This one can take the "
        "whole plot in a week if it is wet."),

    "tomato_leaf_mold": Treatment(
        "tomato_leaf_mold", "Tomato leaf mould", "fungal", "spreads slowly",
        "Open up the plant, cut off the worst leaves, water the soil not "
        "the leaves.",
        "Chlorothalonil", "2 ml per litre of water", 12.0, 7, True,
        "Yellow patches on top, olive fuzz underneath. Usually means the air "
        "is not moving."),

    "tomato_septoria": Treatment(
        "tomato_septoria", "Septoria leaf spot", "fungal", "spreads slowly",
        "Strip the lower leaves. Mulch so rain does not splash soil up.",
        "Mancozeb 75% WP", "2 g per litre of water", 12.0, 5, True,
        "Many small round spots with pale centres."),

    "tomato_bacterial_spot": Treatment(
        "tomato_bacterial_spot", "Bacterial spot", "bacterial", "spreads fast",
        "Remove the affected plants. Do not work in the plot while it is wet, "
        "that is how it travels.",
        "Copper oxychloride 50% WP", "3 g per litre of water", 15.0, 5, True,
        "Chemicals only slow bacteria down. Hygiene does more."),

    "tomato_mosaic_virus": Treatment(
        "tomato_mosaic_virus", "Mosaic virus", "viral", "no cure",
        "Pull the plant out and bin it. Wash your hands and tools before "
        "touching a healthy plant.",
        "", "no spray will cure a virus", 0.0, 0, False,
        "Mottled light and dark green, crinkled leaves. The rover will not "
        "spray this. It will ask you to remove the plant."),

    "tomato_leaf_curl_virus": Treatment(
        "tomato_leaf_curl_virus", "Leaf curl virus", "viral", "no cure",
        "Remove the plant. Control the whitefly that carries it, with sticky "
        "yellow traps first.",
        "", "treat the whitefly, not the virus", 0.0, 0, False,
        "Carried by whitefly. Killing the virus is not possible."),

    "spider_mite": Treatment(
        "spider_mite", "Two spotted spider mite", "pest", "spreads fast in dry heat",
        "Spray the underside of the leaves with plain water first. They hate "
        "humidity.",
        "Neem oil 1500 ppm", "5 ml per litre of water", 15.0, 1, True,
        "Fine webbing and speckled leaves. Neem first, it is kinder to the "
        "ladybirds that eat them."),

    "aphid": Treatment(
        "aphid", "Aphids", "pest", "spreads fast",
        "Wash them off with a jet of water. Leave the ladybirds alone.",
        "Neem oil 1500 ppm", "5 ml per litre of water", 12.0, 1, True,
        "Clusters on the soft new tips."),

    "whitefly": Treatment(
        "whitefly", "Whitefly", "pest", "spreads fast",
        "Put up yellow sticky traps. They catch a surprising number.",
        "Neem oil 1500 ppm", "5 ml per litre of water", 12.0, 1, True,
        "Worth acting on early because they carry leaf curl virus."),

    "powdery_mildew": Treatment(
        "powdery_mildew", "Powdery mildew", "fungal", "spreads slowly",
        "Cut off the worst leaves. Give the plants more room and more sun.",
        "Wettable sulphur 80% WP", "2 g per litre of water", 12.0, 3, True,
        "White powder on the leaf top. Common on cucumber, pumpkin and okra. "
        "Do not use sulphur when it is above 32 C, it will burn the leaf."),

    "downy_mildew": Treatment(
        "downy_mildew", "Downy mildew", "fungal", "spreads fast",
        "Improve drainage and air flow. Water in the morning only.",
        "Metalaxyl + Mancozeb", "2 g per litre of water", 15.0, 7, True,
        "Angular yellow patches bounded by the leaf veins."),

    "cabbage_leaf_miner": Treatment(
        "cabbage_leaf_miner", "Leaf miner", "pest", "spreads slowly",
        "Pick off and destroy the mined leaves. That alone usually does it.",
        "Neem oil 1500 ppm", "5 ml per litre of water", 10.0, 1, True,
        "Pale winding tunnels inside the leaf."),

    "nitrogen_deficiency": Treatment(
        "nitrogen_deficiency", "Nitrogen shortage", "deficiency", "not contagious",
        "Feed it. Compost or well rotted manure around the base works.",
        "Urea spray", "10 g per litre, as a foliar feed", 15.0, 0, True,
        "Older lower leaves go evenly pale yellow while the tips stay green."),

    "water_stress": Treatment(
        "water_stress", "Short of water", "deficiency", "not contagious",
        "Water it. Check the soil reading the rover took before you do more.",
        "", "no chemical needed", 0.0, 0, False,
        "The rover cross checks this against the soil probe before it says so."),

    "weed": Treatment(
        "weed", "Weed between the plants", "weed", "not a disease",
        "Pull it out by hand. The AR-750 has a boom, not a gripper, and "
        "spraying between vegetables hits the vegetables too.",
        "", "no chemical on a kitchen plot", 0.0, 0, False,
        "Pulling beats spraying this close to food."),

    "unknown": Treatment(
        "unknown", "Not sure", "unknown", "unknown",
        "The rover is not confident. It has saved a photo for you to look at.",
        "", "", 0.0, 0, False,
        "Anything below the confidence threshold ends up here on purpose."),

    "not_checked": Treatment(
        "not_checked", "Not checked", "unknown", "unknown",
        "There is no AI model loaded, so the rover did not look at the leaf. "
        "It saved a photo. Look at it yourself.",
        "", "", 0.0, 0, False,
        "Install the model file and this goes away. The rover will never "
        "guess a disease it did not actually see."),
}


def severity_from_confidence(conf: float, kind: str) -> str:
    if kind in ("ok", "weed"):
        return "none"
    if kind == "unknown":
        return "unknown"
    if conf >= 0.90:
        return "severe"
    if conf >= 0.78:
        return "moderate"
    return "mild"


def lookup(label: str) -> Treatment:
    return TREATMENTS.get(label, TREATMENTS["unknown"])


def plan(label: str, confidence: float, soil_pct: Optional[float] = None,
         auto_spray_conf: float = 0.85) -> Dict[str, object]:
    """Decide what the rover should do about one plant.

    Returns a plain dict the mission loop and the website both understand.
    """
    t = lookup(label)

    # the soil probe gets a veto on "short of water"
    if label == "water_stress" and soil_pct is not None and soil_pct > 45:
        t = TREATMENTS["healthy"]
        return dict(label="healthy", common_name="Healthy plant", kind="ok",
                    severity="none", healthy=True, action="none",
                    advice="Leaves looked limp but the soil is at %.0f%%, so it is "
                           "not thirsty. Probably just midday wilt." % soil_pct,
                    product="", dose="", dose_ml=0.0, phi_days=0,
                    spray_allowed=False, needs_you=False)

    healthy = t.kind == "ok"
    sev = severity_from_confidence(confidence, t.kind)

    needs_you = False
    action = "none"
    if t.kind == "unknown":
        # never pretend. An unseen plant is not a healthy plant.
        action = "needs_you"
        needs_you = True
    elif t.kind == "viral":
        action = "needs_you"
        needs_you = True
    elif t.kind == "weed":
        # the AR-750 has no gripper. The mission logs it and asks YOU to pull
        # it; the boom can only put chemical on it, which on a kitchen plot is
        # usually the wrong answer for one weed between two vegetables.
        action = "weed_pull"
    elif not healthy and t.spray_ok:
        action = "spray" if confidence >= auto_spray_conf else "needs_you"
        needs_you = action == "needs_you"

    advice = t.first_try
    if action == "spray":
        advice = "%s  If it does not clear up: %s" % (t.first_try, t.note)

    return dict(
        label=t.label,
        common_name=t.common_name,
        kind=t.kind,
        severity=sev,
        healthy=healthy,
        action=action,
        advice=advice,
        product=t.product,
        dose=t.dose,
        # the dose it would use. It is quoted in the question it asks you even
        # when it is not allowed to spray on its own, so you can say yes to it.
        dose_ml=(t.dose_ml_per_plant
                 if action in ("spray", "needs_you") and t.spray_ok else 0.0),
        phi_days=t.phi_days,
        spray_allowed=t.spray_ok,
        needs_you=needs_you,
        note=t.note,
    )


def label_list() -> List[str]:
    return list(TREATMENTS.keys())
