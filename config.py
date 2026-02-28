"""定数・4象限定義・モデル設定"""

QUADRANTS = [
    {
        "key": "medical_indications",
        "title_ja": "医学的適応",
        "title_en": "Medical Indications",
        "subtopics": [
            "診断と予後",
            "治療の目標",
            "治療の選択肢",
            "医学的無益性",
        ],
    },
    {
        "key": "patient_preferences",
        "title_ja": "患者の意向",
        "title_en": "Patient Preferences",
        "subtopics": [
            "患者の希望",
            "インフォームドコンセント",
            "判断能力",
            "代理決定者",
        ],
    },
    {
        "key": "qol",
        "title_ja": "QOL",
        "title_en": "Quality of Life",
        "subtopics": [
            "治療後のQOL見込み",
            "日常生活への影響",
            "QOL評価の主体",
            "偏見の排除",
        ],
    },
    {
        "key": "contextual_features",
        "title_ja": "周囲の状況",
        "title_en": "Contextual Features",
        "subtopics": [
            "家族の意向",
            "経済的問題",
            "法的問題",
            "施設の方針",
        ],
    },
]

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 2048
TEMPERATURE = 0.7

DISCLAIMER = "本ツールは意思決定支援であり、最終判断は医療チームに委ねられます。"
