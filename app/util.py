def translate_message(msg, lang="en"):
    """
    Translate messages to Hindi or Telugu.
    lang: "en" (English), "hi" (Hindi), "te" (Telugu)
    """
    translations = {
        "en": msg,
        "hi": {
            "Invalid credentials": "अमान्य विवरण",
            "User already exists": "उपयोगकर्ता पहले से मौजूद है",
            "Please enter numeric values for all parameters.": "कृपया सभी मानों के लिए संख्यात्मक मान दर्ज करें।",
            "Conditions are optimal!": "परिस्थितियाँ आदर्श हैं!"
        },
        "te": {
            "Invalid credentials": "చెల్లని సమాచారం",
            "User already exists": "వాడుకరి ఇప్పటికే ఉంది",
            "Please enter numeric values for all parameters.": "అన్ని విలువలకు సంఖ్యా విలువలు ఇవ్వండి.",
            "Conditions are optimal!": "స్థితులు ఉత్తమంగా ఉన్నాయి!"
        }
    }

    if lang in ["hi", "te"]:
        return translations[lang].get(msg, msg)
    return msg
