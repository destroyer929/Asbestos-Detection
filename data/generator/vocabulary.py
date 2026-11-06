"""
Architectural vocabulary and domain phrases for synthetic blueprint generation.
Contains Japanese and English building terms, finish schedule terminology,
room names, dimension patterns, and material specification modifiers.
"""

# Japanese Room Names common in industrial, commercial and residential blueprints
ROOM_NAMES_JA = [
    "機械室",          # Machinery Room (Often Level 1 spray / Level 2 pipe insulation)
    "ボイラー室",       # Boiler Room (Frequent Level 1 / Level 2)
    "電気室",          # Electrical Room
    "事務室 (A)",       # Office Room A (Common Level 3 vinyl tile / acoustic ceiling)
    "事務室 (B)",       # Office Room B
    "会議室 (1)",       # Conference Room 1
    "会議室 (2)",       # Conference Room 2
    "給湯室",          # Kitchenette / Hot water room (CalSil board)
    "女子便所",        # Women's Restroom
    "男子便所",        # Men's Restroom
    "湯沸室",          # Pantry / Water heater room
    "倉庫 (1)",        # Warehouse / Storage (Slate sheets / rockwool)
    "倉庫 (2)",        # Warehouse 2
    "廊下・ホール",     # Corridor / Hallway
    "階段室",          # Stairwell
    "エントランスホール", # Entrance Hall
    "風除室",          # Windbreak room / Vestibule
    "配管シャフト (PS)", # Pipe Shaft (Level 2 pipe insulation)
    "空調機械室"        # HVAC Machinery Room
]

ROOM_NAMES_EN = [
    "Machine Room",
    "Boiler Room",
    "Electrical Room",
    "Office Area A",
    "Office Area B",
    "Meeting Room",
    "Kitchenette",
    "Storage Room",
    "Main Corridor",
    "Staircase 1",
    "Entrance Lobby",
    "Pipe Shaft"
]

# Table Header Labels for Finish Schedule (仕上表)
FINISH_SCHEDULE_HEADERS = [
    "室名",       # Room Name
    "床",         # Floor
    "巾木",       # Baseboard
    "壁",         # Wall
    "天井",       # Ceiling
    "下地",       # Substrate
    "備考"        # Remarks
]

# Non-material annotations (noise to test OCR filtering and region classification)
DIMENSION_STRINGS = [
    "3,600",
    "7,200",
    "1,800",
    "900",
    "4,500",
    "6,000",
    "2,700",
    "FL ±0",
    "FL +150",
    "1SL +3,200",
    "2SL +6,400",
    "CH = 2,700",
    "CH = 2,500",
    "CH = 3,000",
    "RFL +9,600",
    "GL ±0",
    "W=900 H=2,100",
    "W=1,800 H=1,200",
    "100 x 50 x 20",
    "H-300x150x6.5x9"
]

# General architectural notes & drawing block labels
DRAWING_BLOCK_LABELS = [
    "設計: アルフレッド建築設計事務所",
    "工事名称: 浜松事業所改修工事",
    "図面名称: 各階平面詳細図・特記仕上表",
    "縮尺: 1/100 (A1) 1/200 (A3)",
    "図面番号: A-102",
    "作成年月日: 昭和56年4月 (1981)",
    "承認",
    "担当",
    "特記事項: 既存仕上材解体時は石綿飛散防止対策を講ずること",
    "凡例: (E)既存撤去 (N)新設"
]

# Typical thickness specifications
THICKNESS_MODIFIERS = [
    "t=6", "t=8", "t=9.5", "t=12", "t=15", "t=20", "t=25", "t=30", "t=50",
    "25mm", "50mm", "100mm", "厚25", "厚15"
]

# Finish modifiers
FINISH_MODIFIERS = [
    "EP塗装",          # Emulsion paint
    "OP塗装",          # Oil paint
    "AEP塗装",         # Acrylic emulsion paint
    "目透かし張り",     # Butt joint / reveal joint
    "下地共",          # Including substrate
    "耐火被覆2時間",    # 2-hour fireproof coating
    "防湿シート貼",     # Moisture proof sheet
    "金ゴテ押え",       # Steel trowel finish
    "寒冷紗補強"       # Scrim reinforcement
]

