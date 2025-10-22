from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
import os
import traceback
import numpy as np
from werkzeug.utils import secure_filename
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import load_img, img_to_array
from app.models import load_assets
from app import mongo, bcrypt  # ✅ Make sure mongo & bcrypt are initialized in app/__init__.py

main = Blueprint("main", __name__, template_folder="templates")

# ---------- LOAD ASSETS ----------
hydro_model, label_encoder, df, disease_model = load_assets()
disease_labels = {0: 'Healthy', 1: 'Powdery', 2: 'Rust'}


# ---------- HELPER FUNCTIONS ----------
def get_plant_conditions(user_input):
    if not user_input:
        return None
    user_input = user_input.strip().lower()
    df['plant_clean'] = df['plant_name'].str.lower().str.strip()
    df['plant_clean_simple'] = df['plant_clean'].str.replace(r'\(.*\)', '', regex=True).str.strip()

    exact = df[df['plant_clean'] == user_input]
    if not exact.empty:
        return exact.iloc[0].to_dict()

    exact_simple = df[df['plant_clean_simple'] == user_input]
    if not exact_simple.empty:
        return exact_simple.iloc[0].to_dict()

    partial = df[df['plant_clean'].str.contains(user_input)]
    if not partial.empty:
        return partial.iloc[0].to_dict()

    partial_simple = df[df['plant_clean_simple'].str.contains(user_input)]
    if not partial_simple.empty:
        return partial_simple.iloc[0].to_dict()

    return None


def suggest_adjustments(user_input, optimal):
    suggestions = []
    try:
        diff_temp = round(user_input.get("temperature_c", 0) - float(optimal["optimal_temp_c"]), 1)
        if abs(diff_temp) > 0.5:
            suggestions.append(f"🌡️ {'Decrease' if diff_temp > 0 else 'Increase'} temperature by {abs(diff_temp)}°C")
    except:
        pass

    try:
        diff_ph = round(user_input.get("ph", 0) - float(optimal["optimal_ph"]), 2)
        if abs(diff_ph) > 0.1:
            suggestions.append(f"⚗️ {'Lower' if diff_ph > 0 else 'Raise'} pH by {abs(diff_ph)}")
    except:
        pass

    try:
        diff_hum = round(user_input.get("humidity_pct", 0) - float(optimal["optimal_humidity"]), 1)
        if abs(diff_hum) > 1:
            suggestions.append(f"💧 {'Reduce' if diff_hum > 0 else 'Increase'} humidity by {abs(diff_hum)}%")
    except:
        pass

    try:
        diff_nut = round(user_input.get("nutrient_ppm", 0) - float(optimal["optimal_nutrient_ppm"]), 1)
        if abs(diff_nut) > 20:
            suggestions.append(f"🥗 {'Dilute' if diff_nut > 0 else 'Increase'} nutrients by {abs(diff_nut)} ppm")
    except:
        pass

    if not suggestions:
        suggestions.append("✅ Conditions are optimal!")
    return suggestions


def predict_disease(image_path):
    try:
        img = load_img(image_path, target_size=(225, 225))
        x = img_to_array(img)
        x = x.astype('float32') / 255.
        x = np.expand_dims(x, axis=0)
        predictions = disease_model.predict(x)[0]
        label_idx = int(np.argmax(predictions))
        confidence = float(np.max(predictions) * 100)
        return {"disease": disease_labels[label_idx], "confidence": round(confidence, 2)}
    except Exception as e:
        return {"error": str(e)}


# ---------- SYMPTOM CHAT ----------
symptom_map = {
    "powdery mildew": ["powdery", "white powder", "mildew"],
    "rust": ["rust", "orange spots", "brown pustules"],
    "yellowing": ["yellow", "turning yellow", "chlorosis"],
    "spots": ["spots", "brown spots", "black spots", "leaf spots"],
    "leaf disease": ["disease", "ill", "sick", "leaf issue", "plant issue"]
}

disease_info = {
    "powdery mildew": "🌿 Powdery mildew is a fungal disease causing white powdery spots on leaves.",
    "rust": "🌿 Rust disease causes orange/brown pustules on leaves, reduces photosynthesis.",
    "yellowing": "🌿 Yellowing leaves may indicate nutrient deficiency or stress.",
    "spots": "🌿 Brown or black spots indicate fungal or bacterial infection.",
    "leaf disease": "🌿 General leaf disease detected. You can upload an image for precise prediction."
}


def detect_symptom(msg):
    msg_lower = msg.lower()
    for disease, keywords in symptom_map.items():
        for kw in keywords:
            if kw in msg_lower:
                return disease
    return None


# ---------- ROUTES ----------
@main.route("/")
def home():
    return render_template("index.html")


@main.route("/predict", methods=["POST", "GET"])
def predict():
    try:
        if request.method == "POST":
            if request.is_json:
                payload = request.get_json()
                plant_name = payload.get("plant_name")
                temp = payload.get("temperature_c")
                ph = payload.get("ph")
                humidity = payload.get("humidity_pct")
                nutrient = payload.get("nutrient_ppm")
            else:
                plant_name = request.form.get("plant_name")
                temp = request.form.get("temperature_c") or request.form.get("temperature")
                ph = request.form.get("ph")
                humidity = request.form.get("humidity_pct") or request.form.get("humidity")
                nutrient = request.form.get("nutrient_ppm") or request.form.get("nutrient")

            if not plant_name:
                return jsonify({"error": "Please enter a plant name."}), 400

            optimal = get_plant_conditions(plant_name)
            if optimal is None:
                return jsonify({"error": f"Plant '{plant_name}' not found."}), 404

            if not any([temp, ph, humidity, nutrient]):
                return jsonify({
                    "plant_name": plant_name,
                    "optimal": {
                        "optimal_temp_c": float(optimal["optimal_temp_c"]),
                        "optimal_ph": float(optimal["optimal_ph"]),
                        "optimal_humidity": float(optimal["optimal_humidity"]),
                        "optimal_nutrient_ppm": float(optimal["optimal_nutrient_ppm"])
                    }
                })

            user_input = {
                "temperature_c": float(temp) if temp else 0,
                "ph": float(ph) if ph else 0,
                "humidity_pct": float(humidity) if humidity else 0,
                "nutrient_ppm": float(nutrient) if nutrient else 0
            }

            suggestions = suggest_adjustments(user_input, optimal)
            return jsonify({
                "plant_name": plant_name,
                "optimal": {
                    "optimal_temp_c": float(optimal["optimal_temp_c"]),
                    "optimal_ph": float(optimal["optimal_ph"]),
                    "optimal_humidity": float(optimal["optimal_humidity"]),
                    "optimal_nutrient_ppm": float(optimal["optimal_nutrient_ppm"])
                },
                "suggestions": [{"message": s} for s in suggestions]
            })
        return render_template("predict.html")
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@main.route("/chat", methods=["POST", "GET"])
def chat():
    try:
        if request.method == "POST":
            data = request.get_json()
            msg = (data.get("message") or "").strip()
            response = "🤖 Sorry, I didn’t understand that."

            if any(g in msg.lower() for g in ["hi", "hello", "hey"]):
                response = "👋 Hello! I can help you find optimal hydroponic conditions for your plants."
            else:
                symptom = detect_symptom(msg)
                if symptom:
                    response = disease_info.get(symptom)
                else:
                    opt = get_plant_conditions(msg)
                    if opt:
                        response = (
                            f"🌿 Optimal conditions for {opt['plant_name']}:\n"
                            f"- Temperature: {opt['optimal_temp_c']}°C\n"
                            f"- pH: {opt['optimal_ph']}\n"
                            f"- Humidity: {opt['optimal_humidity']}%\n"
                            f"- Nutrients: {opt['optimal_nutrient_ppm']} ppm"
                        )
            return jsonify({"response": response, "reply": response})
        return render_template("chat.html")
    except Exception as e:
        traceback.print_exc()
        return jsonify({"response": f"Server error: {e}", "reply": f"Server error: {e}"}), 500


@main.route("/disease-predict", methods=["POST"])
def disease_predict():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        file = request.files['file']
        if file.filename == "":
            return jsonify({"error": "Empty filename"}), 400

        uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
        os.makedirs(uploads_dir, exist_ok=True)

        file_path = os.path.join(uploads_dir, secure_filename(file.filename))
        file.save(file_path)

        result = predict_disease(file_path)
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------- AUTH ROUTES (Login, Register, Logout) ----------
@main.route("/login", methods=["POST"])
def login():
    try:
        users = mongo.db.users
        data = request.get_json()  # Expect JSON from frontend
        username = data.get("email")  # matching your JS field
        password = data.get("password")

        user = users.find_one({"username": username})
        if user and bcrypt.check_password_hash(user["password"], password):
            session["username"] = username  # <-- fix here
            return jsonify({"message": "Login successful!"}), 200

        return jsonify({"error": "Invalid credentials!"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500




@main.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("main.login"))


@main.route("/register", methods=["POST"])
def register():
    try:
        users = mongo.db.users
        data = request.get_json()  # JSON from frontend
        username = data.get("email")
        password = data.get("password")
        name = data.get("name")

        if users.find_one({"username": username}):
            return jsonify({"error": "Username already exists!"}), 400

        # Use Flask-Bcrypt correctly
        hashpass = bcrypt.generate_password_hash(password).decode('utf-8')
        users.insert_one({"username": username, "password": hashpass, "name": name})

        return jsonify({"message": "Registration successful! Please login."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
