# ShipType code to meaning mapping based on ITU/IMO standard
# This is a partial list for demo; extend as needed.
SHIPTYPE_MEANINGS = {
    0: "Not available (default)",
    20: "Wing in ground (WIG), all ships of this type",
    21: "WIG, Hazardous category A",
    22: "WIG, Hazardous category B",
    23: "WIG, Hazardous category C",
    24: "WIG, Hazardous category D",
    25: "WIG, Reserved for future use",
    26: "WIG, Reserved for future use",
    27: "WIG, Reserved for future use",
    28: "WIG, Reserved for future use",
    29: "WIG, Reserved for future use",
    30: "Fishing",
    31: "Towing",
    32: "Towing: length exceeds 200m or breadth exceeds 25m",
    33: "Dredging or underwater ops",
    34: "Diving ops",
    35: "Military ops",
    36: "Sailing",
    37: "Pleasure Craft",
    40: "High speed craft (HSC), all ships of this type",
    50: "Pilot vessel",
    51: "Search and rescue vessel",
    52: "Tug",
    53: "Port tender",
    54: "Anti-pollution equipment",
    55: "Law enforcement vessel",
    56: "Spare - Local Vessel",
    57: "Spare - Local Vessel",
    58: "Medical transport",
    59: "Noncombatant ship according to RR Resolution No. 18",
    60: "Passenger, all ships of this type",
    70: "Cargo, all ships of this type",
    80: "Tanker, all ships of this type",
    90: "Other type, all ships of this type"
    # ... (add more as needed)
}

def get_shiptype_meaning(shiptype):
    try:
        code = int(shiptype)
    except Exception:
        return str(shiptype)
    return SHIPTYPE_MEANINGS.get(code, str(shiptype))
