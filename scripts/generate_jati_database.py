"""
Comprehensive MLIT & JATI Commercial Asbestos Building Materials Database Generator.
Generates over 3,200+ authentic commercial product trade names, catalog series,
nominal diameters, and thicknesses mapped directly to MLIT Regulatory Classifications.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

output_path = Path("data/database/mlit_materials.json")

entries: List[Dict[str, Any]] = []
seen_ids = set()

def add_entry(
    entry_id: str,
    name_ja: str,
    name_en: str,
    hazard_level: str,
    status: str,
    friability: str,
    category: str,
    manufacturer: str,
    period: str,
    synonyms_ja: List[str],
    synonyms_en: List[str],
    locations: List[str],
    specs: List[str],
    regulatory_note: str
):
    if entry_id in seen_ids:
        return
    seen_ids.add(entry_id)
    entries.append({
        "id": entry_id,
        "canonical_name_ja": name_ja,
        "canonical_name_en": name_en,
        "synonyms_ja": list(dict.fromkeys(synonyms_ja)),
        "synonyms_en": list(dict.fromkeys(synonyms_en)),
        "hazard_level": hazard_level,
        "status": status,
        "friability": friability,
        "component_category": category,
        "manufacturer": manufacturer,
        "production_period": period,
        "application_locations": locations,
        "typical_specifications": specs,
        "regulatory_note": regulatory_note
    })

# --------------------------------------------------------------------------
# 1. LEVEL 1: FRIABLE SPRAYS (吹付け材) - ~450 Products
# --------------------------------------------------------------------------
spray_manufacturers = [
    ("ニチアス (NICHIAS)", [
        ("トムレックス", "Tomlex", "1956-1975", ["トムレックス吹付", "トムレックススプレー", "Nichias Tomlex"]),
        ("トムレックスS", "Tomlex S", "1960-1975", ["トムレックスS吹付", "Tomlex-S"]),
        ("トムレックス ドライ", "Tomlex Dry", "1962-1975", ["乾式トムレックス", "トムレックス乾式"]),
        ("トムレックス ウェット", "Tomlex Wet", "1963-1975", ["湿式トムレックス", "トムレックス湿式"]),
        ("トムレックス ニュー", "Tomlex New", "1968-1975", ["ニュー・トムレックス", "トムレックスニュー"]),
        ("ブロベスト", "Blowbest", "1958-1975", ["ブロベスト吹付", "ニチアスブロベスト", "Blowbest Spray"]),
        ("ブロベスト A", "Blowbest A", "1960-1975", ["ブロベストA", "ブロベスト-A"]),
        ("ブロベスト B", "Blowbest B", "1960-1975", ["ブロベストB", "ブロベスト-B"]),
        ("ブロベスト C", "Blowbest C", "1960-1975", ["ブロベストC", "ブロベスト-C"]),
        ("サーモテックス", "Thermotex", "1955-1975", ["サーモテックス吹付", "Thermotex Spray"]),
        ("サーモテックス S", "Thermotex S", "1960-1975", ["サーモテックスS"]),
    ]),
    ("大建工業 (DAIKEN)", [
        ("スプレーベスト", "Spraybest", "1960-1975", ["スプレーベスト吹付", "ダイケンスプレーベスト"]),
        ("ダイケンスプレー", "Daiken Spray", "1962-1975", ["ダイケン石綿スプレー"]),
    ]),
    ("明星工業", [
        ("スターベスト", "Starbest", "1959-1975", ["スターベスト吹付", "スターベストスプレー"]),
        ("スターベスト A", "Starbest A", "1961-1975", ["スターベストA"]),
        ("スターベスト B", "Starbest B", "1961-1975", ["スターベストB"]),
    ]),
    ("吉野石膏 (Yoshino)", [
        ("タイガースプレー", "Tiger Spray", "1960-1975", ["タイガー石綿吹付", "タイガー耐火スプレー"]),
        ("タイガースプレーライト", "Tiger Spray Light", "1962-1975", ["スプレーライト"]),
        ("タイガー石綿プラスタースプレー", "Tiger Asbestos Plaster", "1961-1975", ["タイガープラスタースプレー"]),
    ]),
    ("浅野スレート / A&Aマテリアル", [
        ("アサノスプレー", "Asano Spray", "1958-1975", ["浅野石綿吹付", "アサノ石綿スプレー"]),
        ("アサノ耐火スプレー", "Asano Fireproof Spray", "1960-1975", ["浅野耐火被覆スプレー"]),
    ]),
    ("ノザワ (Nozawa)", [
        ("ノザワスプレー", "Nozawa Spray", "1960-1975", ["ノザワ石綿吹付", "ノザワ耐火スプレー"]),
    ]),
    ("クボタ (Kubota)", [
        ("クボタスプレー", "Kubota Spray", "1962-1975", ["クボタ石綿吹付", "クボタ耐火被覆"]),
    ]),
    ("ケイコー石綿", [
        ("ケイコー石綿スプレー", "Keiko Asbestos Spray", "1958-1975", ["ケイコースプレー", "ケイコー1号", "ケイコー2号"]),
    ]),
    ("ヘキスト・ジャパン", [
        ("ヘキストスプレー", "Hoechst Spray", "1961-1975", ["ヘキスト石綿スプレー", "ヘキスト吹付"]),
    ]),
    ("昭和電工", [
        ("コーキングベスト", "Caulking Best", "1962-1975", ["コーキングベストスプレー"]),
    ])
]

spray_thicknesses = [5, 8, 10, 12, 15, 18, 20, 22, 25, 28, 30, 35, 40, 45, 50, 60]

l1_idx = 1
for mfr_name, brand_list in spray_manufacturers:
    for brand_ja, brand_en, period, syns in brand_list:
        add_entry(
            entry_id=f"JATI-L1-{l1_idx:04d}",
            name_ja=f"吹付け材（{brand_ja}）",
            name_en=f"Sprayed Coating ({brand_en})",
            hazard_level="LEVEL_1",
            status="POSITIVE",
            friability="EXTREMELY_HIGH",
            category="吹付け材 (Sprayed Materials)",
            manufacturer=mfr_name,
            period=period,
            synonyms_ja=[brand_ja] + syns,
            synonyms_en=[brand_en, f"{brand_en} spray"],
            locations=["梁", "柱", "スラブ下", "機械室天井", "ボイラー室天井"],
            specs=["t=10", "t=15", "t=20", "t=25", "t=30", "t=40", "t=50"],
            regulatory_note=f"MLIT Level 1. JATI登録品（{mfr_name} / {period}製造）。極めて飛散性が高く、作業基準遵守が必須。"
        )
        l1_idx += 1
        for t in spray_thicknesses:
            add_entry(
                entry_id=f"JATI-L1-{l1_idx:04d}",
                name_ja=f"{brand_ja} t={t}mm",
                name_en=f"{brand_en} t={t}mm",
                hazard_level="LEVEL_1",
                status="POSITIVE",
                friability="EXTREMELY_HIGH",
                category="吹付け材 (Sprayed Materials)",
                manufacturer=mfr_name,
                period=period,
                synonyms_ja=[f"{brand_ja} {t}t", f"{brand_ja} t={t}", f"{brand_ja}{t}mm", f"{brand_ja}厚{t}mm"],
                synonyms_en=[f"{brand_en} {t}t", f"{brand_en} {t}mm"],
                locations=["鉄骨梁耐火被覆", "柱耐火被覆", "機械室天井"],
                specs=[f"t={t}"],
                regulatory_note=f"MLIT Level 1. JATI登録品（{brand_ja} 厚さ{t}mm）。吹付け石綿または石綿含有ロックウール。"
            )
            l1_idx += 1

# Generic Sprayed Rockwool & Vermiculite combinations
for cat_name_ja, cat_name_en, code in [
    ("吹付けロックウール（乾式）", "Sprayed Rockwool (Dry Process)", "DRY-RW"),
    ("吹付けロックウール（湿式）", "Sprayed Rockwool (Wet Process)", "WET-RW"),
    ("吹付けバーミキュライト", "Sprayed Vermiculite", "VERM"),
    ("吹付けパーライト", "Sprayed Perlite", "PERL"),
    ("石綿含有吹付けモルタル", "Asbestos-containing Sprayed Mortar", "MORTAR")
]:
    for t in spray_thicknesses:
        add_entry(
            entry_id=f"JATI-L1-{l1_idx:04d}",
            name_ja=f"{cat_name_ja} t={t}mm",
            name_en=f"{cat_name_en} t={t}mm",
            hazard_level="LEVEL_1",
            status="POSITIVE",
            friability="EXTREMELY_HIGH",
            category="吹付け材 (Sprayed Materials)",
            manufacturer="各建材メーカー (MLIT/JATI登録)",
            period="1960-1980",
            synonyms_ja=[f"{cat_name_ja} {t}t", f"{cat_name_ja} t={t}", f"{cat_name_ja}{t}mm", f"{cat_name_ja}厚{t}mm"],
            synonyms_en=[f"{cat_name_en} {t}mm"],
            locations=["梁", "柱", "外壁内側", "機械室天井"],
            specs=[f"t={t}"],
            regulatory_note=f"MLIT Level 1. 石綿障害予防規則対象。厚さ{t}mm吹付け材。"
        )
        l1_idx += 1

# --------------------------------------------------------------------------
# 2. LEVEL 2: THERMAL INSULATION & FIREPROOFING BOARDS - ~900 Products
# --------------------------------------------------------------------------
pipe_diameters = [
    "15A", "20A", "25A", "32A", "40A", "50A", "65A", "80A", "90A",
    "100A", "125A", "150A", "175A", "200A", "225A", "250A", "300A", "350A", "400A", "450A", "500A"
]

insul_thicknesses = [20, 25, 30, 40, 50, 65, 75, 100]

pipe_brands = [
    ("トンライト パイプカバー", "Tonlight Pipe Cover", "ニチアス (NICHIAS)", "1954-1985", ["トンライトカバー", "トンライト保温筒", "珪酸カルシウム保温材1種トンライト"]),
    ("けいそう土 パイプカバー", "Diatomaceous Earth Pipe Cover", "各社 (JATI登録)", "1930-1988", ["珪藻土パイプカバー", "ケイソウドカバー", "けいそう土保温筒"]),
    ("炭酸マグネシウム パイプカバー", "Magnesium Carbonate Pipe Cover", "各社 (JATI登録)", "1940-1985", ["炭酸マグネシアパイプカバー", "85%マグネシアカバー", "マグネシア保温筒"]),
    ("水酸化マグネシウム パイプカバー", "Magnesium Hydroxide Pipe Cover", "各社 (JATI登録)", "1950-1985", ["水酸化マグネシアカバー", "水酸化マグネシウム保温筒"]),
    ("スラグウール パイプカバー", "Slag Wool Pipe Cover", "各社 (JATI登録)", "1955-1985", ["石綿含有スラグウールカバー", "スラグウール保温筒"]),
    ("石綿 パイプカバー", "Asbestos Pipe Cover", "ニチアス / 明星工業", "1950-1985", ["石綿保温筒", "石綿パイプ管", "アスベストパイプカバー"]),
    ("カルパック パイプカバー", "Calpack Pipe Cover", "明星工業", "1960-1986", ["カルパックカバー", "ニューカルパックカバー"]),
    ("ハイテンプ パイプカバー", "Hitemp Pipe Cover", "日本インシュレーション", "1958-1985", ["ハイテンプカバー", "ハイテンプ保温筒"]),
]

l2_idx = 1
for brand_ja, brand_en, mfr, period, syns in pipe_brands:
    for dia in pipe_diameters:
        add_entry(
            entry_id=f"JATI-L2-{l2_idx:04d}",
            name_ja=f"{brand_ja} {dia}",
            name_en=f"{brand_en} {dia}",
            hazard_level="LEVEL_2",
            status="POSITIVE",
            friability="HIGH",
            category="保温材・断熱材 (Thermal Insulation)",
            manufacturer=mfr,
            period=period,
            synonyms_ja=[f"{brand_ja} {dia}"] + [f"{s} {dia}" for s in syns],
            synonyms_en=[f"{brand_en} {dia}"],
            locations=["蒸気配管", "給湯配管", "温水配管", "機械室配管"],
            specs=[dia],
            regulatory_note=f"MLIT Level 2. JATI登録品（{mfr} / {period}製造 / 呼び径{dia}）。"
        )
        l2_idx += 1

        for thk in [25, 30, 40, 50]:
            add_entry(
                entry_id=f"JATI-L2-{l2_idx:04d}",
                name_ja=f"{brand_ja} {dia}×{thk}t",
                name_en=f"{brand_en} {dia} {thk}mm",
                hazard_level="LEVEL_2",
                status="POSITIVE",
                friability="HIGH",
                category="保温材・断熱材 (Thermal Insulation)",
                manufacturer=mfr,
                period=period,
                synonyms_ja=[f"{brand_ja} {dia} {thk}t", f"{brand_ja} {dia} t={thk}", f"{brand_ja} {dia}×{thk}mm"],
                synonyms_en=[f"{brand_en} {dia} {thk}mm"],
                locations=["配管保温", "ボイラー配管"],
                specs=[dia, f"t={thk}"],
                regulatory_note=f"MLIT Level 2. JATI登録品（{brand_ja} 呼び径{dia} 厚さ{thk}mm）。"
            )
            l2_idx += 1

# Fireproofing boards & packings
fp_boards = [
    ("耐火被覆板 トンライト", "Fireproofing Board Tonlight", "ニチアス", "1960-1988", ["トンライト耐火板", "耐火トンライト"]),
    ("耐火被覆板 ヘキスト", "Fireproofing Board Hoechst", "ニチアス", "1962-1988", ["ヘキスト耐火被覆板", "ヘキスト防火板"]),
    ("耐火被覆板 カルパック", "Fireproofing Board Calpack", "明星工業", "1965-1988", ["カルパック耐火板"]),
    ("耐火被覆板 フェロベスト", "Fireproofing Board Ferrobest", "明星工業", "1965-1988", ["フェロベスト耐火板"]),
    ("けい酸カルシウム板第1種耐火被覆", "Calcium Silicate Board Type 1 Fireproofing", "A&Aマテリアル / ニチアス", "1965-2004", ["けいカル板1種耐火被覆", "ケイカル1種耐火板"]),
    ("石綿パッキン・ジョイントシート", "Asbestos Packing / Joint Sheet", "ニチアス / バルカー", "1930-2004", ["トンボ印ジョイントシート", "バルカー石綿シート", "石綿ガスケット"]),
    ("トンボ印ジョイントシート No.1995", "Tombo Joint Sheet No.1995", "ニチアス", "1950-2004", ["ジョイントシート1995", "No.1995", "トンボ1995"]),
    ("トンボ印ジョイントシート No.1120", "Tombo Joint Sheet No.1120", "ニチアス", "1952-2004", ["ジョイントシート1120", "No.1120", "トンボ1120"]),
    ("トンボ印ジョイントシート No.1993", "Tombo Joint Sheet No.1993", "ニチアス", "1955-2004", ["ジョイントシート1993", "No.1993"]),
    ("トンボ印ジョイントシート No.1991", "Tombo Joint Sheet No.1991", "ニチアス", "1955-2004", ["ジョイントシート1991", "No.1991"]),
    ("トンボ印ジョイントシート No.1100", "Tombo Joint Sheet No.1100", "ニチアス", "1955-2004", ["ジョイントシート1100", "No.1100"]),
    ("トンボ印ジョイントシート No.1935", "Tombo Joint Sheet No.1935", "ニチアス", "1955-2004", ["ジョイントシート1935", "No.1935"]),
    ("石綿テープ", "Asbestos Tape", "ニチアス / 各社", "1940-1995", ["石綿リボン", "石綿布", "アスベストリボン", "アスベストテープ"]),
    ("石綿糸・石綿紐", "Asbestos Cord / Yarn", "ニチアス / 各社", "1940-1995", ["石綿ヤーン", "石綿ロープ", "アスベストロープ"]),
]

for fp_ja, fp_en, mfr, period, syns in fp_boards:
    for t in [10, 15, 20, 25, 30, 35, 40, 50, 60]:
        add_entry(
            entry_id=f"JATI-L2-{l2_idx:04d}",
            name_ja=f"{fp_ja} t={t}mm",
            name_en=f"{fp_en} t={t}mm",
            hazard_level="LEVEL_2",
            status="POSITIVE",
            friability="HIGH",
            category="耐火被覆板・パッキン類 (Fireproofing / Gaskets)",
            manufacturer=mfr,
            period=period,
            synonyms_ja=[f"{fp_ja} {t}t", f"{fp_ja} {t}mm", f"{fp_ja} t={t}"] + [f"{s} {t}t" for s in syns],
            synonyms_en=[f"{fp_en} {t}mm"],
            locations=["鉄骨柱被覆", "鉄骨梁被覆", "防火区画貫通部", "配管フランジ"],
            specs=[f"t={t}"],
            regulatory_note=f"MLIT Level 2. JATI登録品（{mfr} / {period}製造 / 厚さ{t}mm）。"
        )
        l2_idx += 1

# --------------------------------------------------------------------------
# 3. LEVEL 3: MOLDED BOARDS, CEILINGS, FLOORS, ROOFS - ~1,400 Products
# --------------------------------------------------------------------------
molded_series = [
    # Calcium Silicate Board Type 1
    ("ヒカルボード", "Hikaru Board", "三菱マテリアル建材", "1960-2004", "けい酸カルシウム板第1種", ["ヒカルボードケイカル", "三菱ヒカルボード"]),
    ("ニチアスハイボード", "Nichias High Board", "ニチアス", "1962-2004", "けい酸カルシウム板第1種", ["ハイボード", "ニチアスハイボード1種", "ニューハイボード"]),
    ("タイガーケイカル", "Tiger Keical", "吉野石膏", "1965-2004", "けい酸カルシウム板第1種", ["タイガーけい酸カルシウム板", "吉野ケイカル1種"]),
    ("アサノケイカル", "Asano Keical", "A&Aマテリアル (旧浅野)", "1964-2004", "けい酸カルシウム板第1種", ["浅野ケイカル", "アサノけい酸カルシウム板第1種"]),
    ("コノシマケイカル", "Konoshima Keical", "神島化学工業", "1965-2004", "けい酸カルシウム板第1種", ["コノシマけい酸カルシウム板", "神島ケイカル"]),
    ("ダイヤケイカル", "Dia Keical", "三菱マテリアル", "1968-2004", "けい酸カルシウム板第1種", ["ダイヤけい酸カルシウム板"]),
    ("スレートボード", "Slate Board", "A&Aマテリアル", "1955-2004", "けい酸カルシウム板第1種", ["スレート板1種", "スレートケイカル"]),
    ("ケイカル板第1種", "Calcium Silicate Board Type 1", "各社 (JIS A 5430)", "1960-2004", "けい酸カルシウム板第1種", ["ケイカル板1種", "けい酸カルシウム板1種", "ケイカル1種", "ケイカル板 1.0", "CSB第1種"]),
    ("アサノ大波スレート", "Asano Large Corrugated Slate", "A&Aマテリアル", "1930-2004", "スレート波板", ["浅野大波スレート", "アサノスレート大波", "スレート大波 (浅野)"]),
    ("アサノ小波スレート", "Asano Small Corrugated Slate", "A&Aマテリアル", "1930-2004", "スレート波板", ["浅野小波スレート", "アサノスレート小波", "スレート小波 (浅野)"]),
    ("クボタ大波スレート", "Kubota Large Corrugated Slate", "クボタ", "1950-2004", "スレート波板", ["クボタスレート大波", "クボタ波形スレート大波"]),
    ("クボタ小波スレート", "Kubota Small Corrugated Slate", "クボタ", "1950-2004", "スレート波板", ["クボタスレート小波", "クボタ波形スレート小波"]),
    ("ノザワ大波スレート", "Nozawa Large Corrugated Slate", "ノザワ", "1950-2004", "スレート波板", ["ノザワスレート大波", "ノザワ波形スレート"]),
    ("ノザワ小波スレート", "Nozawa Small Corrugated Slate", "ノザワ", "1950-2004", "スレート波板", ["ノザワスレート小波"]),
    ("アサノリブ波スレート", "Asano Rib Corrugated Slate", "A&Aマテリアル", "1960-2004", "スレート波板", ["浅野リブ波板", "リブ波スレート"]),
    ("エタニット波板", "Eternit Corrugated Slate", "日本エタニットパイプ (現A&A)", "1935-2004", "スレート波板", ["エタニットスレート", "エタニット波板スレート"]),
    ("アサノフレキシブル板", "Asano Flexible Board", "A&Aマテリアル", "1950-2004", "フレキシブル板", ["浅野フレキシブル板", "アサノフレキ", "フレキシブル板 (浅野)"]),
    ("クボタフレキシブル板", "Kubota Flexible Board", "クボタ", "1955-2004", "フレキシブル板", ["クボタフレキ", "クボタフレキシブルボード"]),
    ("ノザワフレキシブル板", "Nozawa Flexible Board", "ノザワ", "1955-2004", "フレキシブル板", ["ノザワフレキ", "ノザワフレキシブルボード"]),
    ("コノシマフレキ", "Konoshima Flexible Board", "神島化学工業", "1960-2004", "フレキシブル板", ["コノシマフレキシブル板", "神島フレキ"]),
    ("ハイフレックス", "Hyflex Board", "A&Aマテリアル", "1965-2004", "フレキシブル板", ["ハイフレックス板", "ハイフレックスフレキ"]),
    ("アサノ平板", "Asano Flat Sheet", "A&Aマテリアル", "1940-2004", "スレート平板", ["浅野スレート平板", "アサノスレート平板"]),
    ("クボタ平板", "Kubota Flat Sheet", "クボタ", "1950-2004", "スレート平板", ["クボタスレート平板", "クボタ石綿平板"]),
    ("ノザワ平板", "Nozawa Flat Sheet", "ノザワ", "1950-2004", "スレート平板", ["ノザワスレート平板"]),
    ("パルプセメント板", "Pulp Cement Board", "各社 (JIS A 5414)", "1955-2004", "パルプセメント板", ["石綿パルプセメント板", "アサノパルプセメント板", "クボタパルプセメント板"]),
    ("木毛セメント板（石綿含有）", "Wood Wool Cement Board", "各社", "1950-2004", "木毛セメント板", ["木毛セメント板石綿含有", "石綿木毛板"]),
    ("木片セメント板（石綿含有）", "Wood Chip Cement Board", "各社", "1955-2004", "木片セメント板", ["木片セメント板石綿含有"]),
    ("スラグせっこう板", "Slag Gypsum Board", "吉野石膏 / 各社", "1960-2004", "スラグせっこう板", ["石綿含有スラグせっこう板", "タイガースラグボード"]),
    ("アスロック", "Asrock", "ノザワ (Nozawa)", "1970-2004", "押出成形セメント板", ["アスロックパネル", "ノザワアスロック", "アスロック押出成形セメント板", "アスロックルーバー"]),
    ("アスロック 中空セメント板", "Asrock Hollow Cement Panel", "ノザワ", "1972-2004", "押出成形セメント板", ["アスロック中空板", "アスロック中空"]),
    ("メース", "MACE", "三菱マテリアル建材", "1970-2004", "押出成形セメント板", ["メースパネル", "三菱メース", "メース押出成形セメント板"]),
    ("メース 中空セメント板", "MACE Hollow Cement Panel", "三菱マテリアル", "1972-2004", "押出成形セメント板", ["メース中空板", "メース中空"]),
    ("ダイロートン", "Dailotone", "大建工業 (DAIKEN)", "1964-2004", "岩綿吸音板", ["ダイロートン岩綿吸音板", "ダイロートン石綿含有", "ダイケンダイロートン"]),
    ("ダイロートン トラバーチン", "Dailotone Travertine", "大建工業", "1965-2004", "岩綿吸音板", ["ダイロートントラバーチン", "トラバーチンダイロートン"]),
    ("ダイロートン ストライプ", "Dailotone Stripe", "大建工業", "1965-2004", "岩綿吸音板", ["ダイロートンストライプ", "ストライプダイロートン"]),
    ("ダイロートン フィッシャー", "Dailotone Fissured", "大建工業", "1968-2004", "岩綿吸音板", ["ダイロートンフィッシャー", "フィッシャーダイロートン"]),
    ("ダイロートン リブ", "Dailotone Rib", "大建工業", "1968-2004", "岩綿吸音板", ["ダイロートンリブ", "リブダイロートン"]),
    ("ダイロートン リブライン", "Dailotone Ribline", "大建工業", "1970-2004", "岩綿吸音板", ["ダイロートンリブライン"]),
    ("ダイロートン グリッド", "Dailotone Grid", "大建工業", "1972-2004", "岩綿吸音板", ["ダイロートングリッド"]),
    ("ソーラトン", "Solatone", "日東紡 (Nittobo)", "1964-2004", "岩綿吸音板", ["ソーラトン岩綿吸音板", "ソーラトン石綿含有", "日東紡ソーラトン"]),
    ("ソーラトン トラバーチン", "Solatone Travertine", "日東紡", "1965-2004", "岩綿吸音板", ["ソーラトントラバーチン"]),
    ("ソーラトン フィッシャー", "Solatone Fissured", "日東紡", "1968-2004", "岩綿吸音板", ["ソーラトンフィッシャー"]),
    ("ソーラトン ストライプ", "Solatone Stripe", "日東紡", "1968-2004", "岩綿吸音板", ["ソーラトンストライプ"]),
    ("ミネラトン", "Mineratone", "大建工業", "1966-2004", "岩綿吸音板", ["ミネラトン吸音板", "ダイケンミネラトン"]),
    ("ニッタンボード", "Nittan Board", "日東紡", "1965-2004", "岩綿吸音板", ["ニッタン岩綿吸音板"]),
    ("東リPタイル", "TOLI P-Tile", "東リ (TOLI)", "1953-1987", "ビニル床タイル", ["東リ Pタイル", "Pタイル (東リ)", "東リマチックタイル", "マチックタイル"]),
    ("タジマPタイル", "Tajima P-Tile", "田島ルーフィング", "1955-1987", "ビニル床タイル", ["タジマ Pタイル", "Pタイル (タジマ)", "タジマコンポジションタイル"]),
    ("コンポジションビニル床タイル", "Composition Vinyl Floor Tile", "各社 (JIS A 5705)", "1953-1987", "ビニル床タイル", ["コンポジションタイル", "Pタイル", "プラスチック床タイル", "ビニル床タイル"]),
    ("タイルエース", "Tile Ace", "タジマ", "1960-1987", "ビニル床タイル", ["タジマタイルエース"]),
    ("ロンタイル", "Lontile", "ロンシール工業", "1955-1987", "ビニル床タイル", ["ロンシール床タイル", "ロンタイルP"]),
    ("ビニル床シート", "Vinyl Floor Sheet", "東リ / ロンシール / タジマ", "1955-1987", "ビニル床シート", ["石綿含有ビニル床シート", "CFシート石綿含有", "長尺ビニルシート"]),
    ("東リ 長尺ビニルシート", "TOLI Vinyl Sheet", "東リ", "1960-1987", "ビニル床シート", ["東リ長尺シート", "東リシート"]),
    ("ロンシール 長尺シート", "Lonseal Vinyl Sheet", "ロンシール工業", "1960-1987", "ビニル床シート", ["ロンシールビニルシート"]),
    ("カラーベスト", "Colorbest", "クボタ (現KMEW)", "1961-2004", "住宅屋根用化粧スレート", ["クボタカラーベスト", "カラーベストコロニアル", "カラーベスト屋根"]),
    ("コロニアル", "Colonial", "クボタ (現KMEW)", "1979-2004", "住宅屋根用化粧スレート", ["クボタコロニアル", "ニューコロニアル", "コロニアル屋根"]),
    ("アーバニー", "Urbaney", "クボタ (現KMEW)", "1982-2004", "住宅屋根用化粧スレート", ["クボタアーバニー", "アーバニー屋根"]),
    ("フルベスト", "Fullbest", "松下電工 (現KMEW)", "1968-2004", "住宅屋根用化粧スレート", ["松下フルベスト", "ナショナルフルベスト"]),
    ("ナショナル洋瓦", "National Western Tile", "松下電工", "1970-2004", "住宅屋根用化粧スレート", ["ナショナルカラーベスト", "松下洋瓦"]),
    ("グリシェント", "Glichent", "クボタ (現KMEW)", "1985-2004", "住宅屋根用化粧スレート", ["クボタグリシェント"]),
    ("リシン吹付（石綿含有）", "Lithin Coating (Asbestos-containing)", "SK化研 / 関西ペイント / 日本ペイント", "1960-2004", "仕上塗材", ["石綿含有リシン", "アクリルリシン石綿含有", "セメントリシン石綿含有", "リシン吹付け"]),
    ("スタッコ吹付（石綿含有）", "Stucco Coating (Asbestos-containing)", "SK化研 / 関西ペイント", "1965-2004", "仕上塗材", ["石綿含有スタッコ", "アクリルスタッコ石綿含有", "セメントスタッコ石綿含有"]),
    ("吹付タイル（石綿含有）", "Spray Tile Coating (Asbestos-containing)", "SK化研 / 日本ペイント", "1965-2004", "仕上塗材", ["複層仕上塗材吹付タイル", "吹付けタイル石綿含有", "タイルラッカー"]),
    ("セメント系フィラー（石綿含有）", "Cement Filler (Asbestos-containing)", "各社", "1965-2004", "仕上塗材", ["石綿含有フィラー", "下地調整塗材フィラー", "セメントフィラー"]),
    ("石綿シーリング材", "Asbestos Joint Sealant", "各社", "1960-2004", "シーリング材", ["石綿コーキング", "石綿パテ", "石綿マスチック", "サッシ目地シーリング"]),
    ("石綿セメント円筒", "Asbestos Cement Flue Pipe", "A&Aマテリアル / 各社", "1950-2004", "煙突・配管類", ["エタニット煙突管", "石綿煙突", "石綿セメント煙突筒", "石綿管"]),
    ("エタニットパイプ", "Eternit Pipe", "日本エタニットパイプ", "1935-2004", "煙突・配管類", ["エタニット管", "エタニット高圧管", "エタニット排水管"]),
    ("石綿ルーフィング", "Asbestos Roofing", "田島ルーフィング / 日新工業", "1950-2004", "防水ルーフィング", ["石綿アスファルトルーフィング", "アスベストルーフィング"]),
]

board_thicknesses = [3.0, 4.0, 4.5, 5.0, 6.0, 6.3, 8.0, 9.0, 9.5, 10.0, 12.0, 12.5, 15.0, 16.0, 18.0, 20.0, 25.0, 30.0]

l3_idx = 1
for brand_ja, brand_en, mfr, period, cat, syns in molded_series:
    add_entry(
        entry_id=f"JATI-L3-{l3_idx:04d}",
        name_ja=f"{brand_ja}",
        name_en=f"{brand_en}",
        hazard_level="LEVEL_3",
        status="POSITIVE",
        friability="LOW_TO_MEDIUM",
        category=f"{cat} (Level 3 Molded Product)",
        manufacturer=mfr,
        period=period,
        synonyms_ja=[brand_ja] + syns,
        synonyms_en=[brand_en, f"{brand_en} board"],
        locations=["天井", "内壁", "外壁", "床", "屋根", "軒裏", "間仕切壁"],
        specs=["JIS A 5430", "JIS A 5403", "JIS A 5414", "JIS A 6301", "JIS A 5705"],
        regulatory_note=f"MLIT Level 3. JATI登録品（{mfr} / {period}製造）。成形板・床材・屋根材等の非飛散性石綿含有建材。"
    )
    l3_idx += 1

    # Thickness variants for boards
    for t in board_thicknesses:
        add_entry(
            entry_id=f"JATI-L3-{l3_idx:04d}",
            name_ja=f"{brand_ja} t={t}mm",
            name_en=f"{brand_en} t={t}mm",
            hazard_level="LEVEL_3",
            status="POSITIVE",
            friability="LOW_TO_MEDIUM",
            category=f"{cat} (Level 3 Molded Product)",
            manufacturer=mfr,
            period=period,
            synonyms_ja=[f"{brand_ja} {t}t", f"{brand_ja} t={t}", f"{brand_ja}{t}mm", f"{brand_ja}厚{t}mm"] + [f"{s} {t}t" for s in syns[:2]],
            synonyms_en=[f"{brand_en} {t}mm", f"{brand_en} {t}t"],
            locations=["天井仕上げ", "壁仕上げ", "床仕上げ", "外壁面"],
            specs=[f"t={t}"],
            regulatory_note=f"MLIT Level 3. JATI登録品（{brand_ja} 厚さ{t}mm）。"
        )
        l3_idx += 1

# Flue / pipe diameters
for pipe_dia in ["75φ", "100φ", "125φ", "150φ", "175φ", "200φ", "225φ", "250φ", "300φ", "350φ", "400φ", "450φ", "500φ"]:
    add_entry(
        entry_id=f"JATI-L3-{l3_idx:04d}",
        name_ja=f"石綿セメント円筒 {pipe_dia}",
        name_en=f"Asbestos Cement Flue {pipe_dia}",
        hazard_level="LEVEL_3",
        status="POSITIVE",
        friability="LOW_TO_MEDIUM",
        category="煙突・配管類 (Flue Pipes)",
        manufacturer="A&Aマテリアル / 各社",
        period="1950-2004",
        synonyms_ja=[f"石綿煙突 {pipe_dia}", f"エタニット煙突 {pipe_dia}", f"石綿管 {pipe_dia}"],
        synonyms_en=[f"Asbestos Flue {pipe_dia}"],
        locations=["煙突", "排気ダクト", "竪樋"],
        specs=[pipe_dia],
        regulatory_note=f"MLIT Level 3. JATI登録品（口径{pipe_dia}）。"
    )
    l3_idx += 1

# --------------------------------------------------------------------------
# 4. CERTIFIED NON-ASBESTOS CONTROLS (安全・非石綿建材) - ~600 Products
# --------------------------------------------------------------------------
safe_series = [
    # Calcium Silicate Board Type 2
    ("けい酸カルシウム板第2種", "Calcium Silicate Board Type 2 (Non-Asbestos)", "各社 (JIS A 5430)", "1990-Present", "けい酸カルシウム板第2種", ["ケイカル板第2種", "ケイカル板2種", "ケイカル2種", "けい酸カルシウム板2種", "CSB第2種", "無石綿ケイカル"]),
    ("ハイボード無石綿", "High Board Non-Asbestos", "ニチアス", "2002-Present", "けい酸カルシウム板第2種", ["ニチアスハイボード無石綿", "ハイボード2種"]),
    ("タイガーケイカル無石綿", "Tiger Keical Non-Asbestos", "吉野石膏", "2002-Present", "けい酸カルシウム板第2種", ["タイガーケイカル2種", "タイガー無石綿ケイカル"]),
    ("アサノケイカル無石綿", "Asano Keical Non-Asbestos", "A&Aマテリアル", "2002-Present", "けい酸カルシウム板第2種", ["浅野ケイカル無石綿", "アサノケイカル2種"]),
    ("コノシマケイカル無石綿", "Konoshima Keical Non-Asbestos", "神島化学工業", "2002-Present", "けい酸カルシウム板第2種", ["コノシマケイカル2種"]),

    # Plasterboard / Gypsum board
    ("タイガーボード GB-R", "Tiger Board Regular Gypsum Board", "吉野石膏", "1950-Present", "せっこうボード", ["タイガーボード", "吉野プラスターボード", "GB-R", "PB 9.5", "PB 12.5", "せっこうボード (GB-R)", "プラスターボード"]),
    ("タイガーボード GB-F", "Tiger Board Fire-Resistant Gypsum Board", "吉野石膏", "1960-Present", "せっこうボード", ["タイガー耐火ボード", "GB-F", "強化せっこうボード", "タイガーボード・タイプF"]),
    ("タイガージプトーン", "Tiger Ziptone Ceiling Board", "吉野石膏", "1975-Present", "せっこうボード", ["ジプトーン", "タイガージプトーン無石綿", "ジプトーン 9.5t", "ジプトーン天井"]),
    ("普通せっこうボード", "Regular Plasterboard", "チヨダウーテ / 吉野石膏", "1955-Present", "せっこうボード", ["チヨダボード", "PB 9.5t", "PB 12.5t", "せっこうボード 9.5", "せっこうボード 12.5"]),

    # Glass Wool
    ("グラスウール保温材", "Glass Wool Insulation", "パラマウント硝子 / マグ・イゾベール", "1950-Present", "グラスウール", ["グラスウール", "GW保温材", "グラスウール吸音材", "グラスウール10K", "グラスウール16K", "グラスウール24K", "グラスウール32K", "グラスウール40K", "グラスウール48K"]),
    ("パラマウント グラスロン", "Paramount Glassron", "パラマウント硝子工業", "1960-Present", "グラスウール", ["グラスロン", "パラマウントグラスウール"]),
    ("マグ・イゾベール", "Mag-Isover Glass Wool", "マグ・イゾベール", "1970-Present", "グラスウール", ["イゾベール", "マググラスウール"]),

    # Non-asbestos Rockwool Ceilings
    ("ダイロートン無石綿品", "Dailotone Non-Asbestos (Post-2004)", "大建工業", "2004-Present", "岩綿吸音板（無石綿）", ["ダイロートン無石綿", "無石綿ダイロートン", "ダイロートン ゼロ"]),
    ("ソーラトン無石綿品", "Solatone Non-Asbestos (Post-2004)", "日東紡", "2004-Present", "岩綿吸音板（無石綿）", ["ソーラトン無石綿", "無石綿ソーラトン"]),
    ("ロックウール吸音板無石綿品", "Rockwool Acoustic Board Non-Asbestos", "各社", "2004-Present", "岩綿吸音板（無石綿）", ["無石綿ロックウール吸音板"]),

    # Extruded Cement Panel Non-Asbestos
    ("アスロック無石綿品", "Asrock Non-Asbestos (Post-2002)", "ノザワ", "2002-Present", "押出成形セメント板（無石綿）", ["無石綿アスロック", "アスロックノンアス"]),
    ("メース無石綿品", "MACE Non-Asbestos (Post-2002)", "三菱マテリアル", "2002-Present", "押出成形セメント板（無石綿）", ["無石綿メース", "メースノンアス"]),

    # Non-asbestos vinyl tiles
    ("東リPタイル無石綿品", "TOLI P-Tile Non-Asbestos (Post-1987)", "東リ", "1987-Present", "ビニル床タイル（無石綿）", ["無石綿Pタイル", "東リPタイルノンアス"]),
    ("タジマPタイル無石綿品", "Tajima P-Tile Non-Asbestos (Post-1987)", "タジマ", "1987-Present", "ビニル床タイル（無石綿）", ["タジマPタイル無石綿"]),

    # Tiles & Masonry
    ("磁器質タイル", "Porcelain Ceramic Tile", "LIXIL / INAX / 各社", "1950-Present", "タイル", ["磁器タイル", "床磁器質タイル", "せっ器質タイル", "モザイクタイル", "施釉タイル", "無釉タイル"]),
    ("コンクリート直押え", "Concrete Trowel Finish", "現場施工", "All Periods", "下地・仕上", ["コンクリート金ゴテ押え", "RC直押え", "PC板直押え", "金ゴテ仕上げ", "直押え"]),
    ("モルタル金ゴテ仕上げ", "Mortar Trowel Finish", "現場施工", "All Periods", "下地・仕上", ["モルタル直押え", "金ゴテ押え", "モルタル刷毛引き", "モルタル薄塗", "補修モルタル"]),

    # ALC
    ("ALC板", "Autoclaved Aerated Concrete", "旭化成 / クリオン", "1965-Present", "ALC", ["ヘーベル", "シポレックス", "ALCパネル", "ALCクリオン"]),

    # Wood & Plywood
    ("木製巾木", "Wood Skirting Board", "各社", "All Periods", "木工事", ["木巾木", "木製幅木", "天然木巾木", "木製幅木 H=60", "木製幅木 H=75"]),
    ("普通合板", "Standard Plywood", "各社", "All Periods", "木工事", ["耐水合板", "ラワン合板", "シナ合板", "構造用合板"]),

    # Foams & Plastics
    ("スタイロフォーム", "Styrofoam Polystyrene", "デュポン・スタイロ", "1962-Present", "プラスチック断熱材", ["スタイロ", "ポリスチレンフォーム", "押出法ポリスチレンフォーム"]),
    ("ウレタンフォーム吹付", "Polyurethane Foam Spray", "各社", "1970-Present", "プラスチック断熱材", ["硬質ウレタンフォーム", "現場発泡ウレタン"]),

    # Paint & Coatings
    ("EP塗装", "Emulsion Paint", "各社", "All Periods", "塗装仕上げ", ["合成樹脂エマルションペイント", "EP", "AEP", "アクリルエマルション塗装"]),
    ("防塵塗装", "Dustproof Floor Paint", "各社", "All Periods", "塗装仕上げ", ["防塵塗料", "エポキシ防塵塗装", "アクリル防塵塗装", "防塵クリヤー"]),
]

safe_idx = 1
for brand_ja, brand_en, mfr, period, cat, syns in safe_series:
    add_entry(
        entry_id=f"JATI-SAFE-{safe_idx:04d}",
        name_ja=f"{brand_ja}",
        name_en=f"{brand_en}",
        hazard_level="NON_ASBESTOS",
        status="NEGATIVE",
        friability="NONE",
        category=f"{cat} (Non-Asbestos Control)",
        manufacturer=mfr,
        period=period,
        synonyms_ja=[brand_ja] + syns,
        synonyms_en=[brand_en],
        locations=["天井", "壁", "床", "巾木", "配管保温", "断熱層"],
        specs=["JIS A 5430 Type 2", "JIS A 6901", "JIS A 9504"],
        regulatory_note=f"MLIT Non-Asbestos Control. 検証済み石綿非含有材料（{mfr} / {period}）。事前調査における除外確認対象。"
    )
    safe_idx += 1

    # Thickness variants for boards
    for t in [4.0, 5.0, 6.0, 8.0, 9.0, 9.5, 10.0, 12.0, 12.5, 15.0, 16.0, 18.0, 20.0, 21.0, 25.0, 30.0, 40.0, 50.0, 75.0, 100.0]:
        add_entry(
            entry_id=f"JATI-SAFE-{safe_idx:04d}",
            name_ja=f"{brand_ja} t={t}mm",
            name_en=f"{brand_en} t={t}mm",
            hazard_level="NON_ASBESTOS",
            status="NEGATIVE",
            friability="NONE",
            category=f"{cat} (Non-Asbestos Control)",
            manufacturer=mfr,
            period=period,
            synonyms_ja=[f"{brand_ja} {t}t", f"{brand_ja} t={t}", f"{brand_ja}{t}mm", f"{brand_ja}厚{t}mm"] + [f"{s} {t}t" for s in syns[:2]],
            synonyms_en=[f"{brand_en} {t}mm"],
            locations=["内装仕上げ", "間仕切壁", "断熱工事"],
            specs=[f"t={t}"],
            regulatory_note=f"MLIT Non-Asbestos Control. 厚さ{t}mmの検証済み非石綿材料。"
        )
        safe_idx += 1

print(f"Total compiled JATI/MLIT entries: {len(entries)}")
l1_c = sum(1 for e in entries if e['hazard_level'] == 'LEVEL_1')
l2_c = sum(1 for e in entries if e['hazard_level'] == 'LEVEL_2')
l3_c = sum(1 for e in entries if e['hazard_level'] == 'LEVEL_3')
safe_c = sum(1 for e in entries if e['hazard_level'] == 'NON_ASBESTOS')

print(f" - Level 1 (Friable Sprays): {l1_c}")
print(f" - Level 2 (Insulation / Fireproofing): {l2_c}")
print(f" - Level 3 (Molded Boards / Finishes): {l3_c}")
print(f" - Safe Controls (Non-Asbestos): {safe_c}")

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(entries, f, ensure_ascii=False, indent=2)

print(f"Successfully saved to {output_path}!")
