from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
from fuzzywuzzy import process
import json
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

app = Flask(__name__)
CORS(app)

# === Bảng mã giải mã ===
codes_hardi = {4: "Beginner", 3: "Easy", 2: "Medium", 1: "Difficult"}
codes_avail = {4: "Very common", 3: "Common", 2: "Rare", 1: "Very rare"}
codes_behave = {3: "Schooling", 2: "Social", 1: "Solitary"}
codes_agres = {3: "Aggressive", 2: "Mostly peaceful", 1: "Peaceful"}
codes_breed = {4: "No record", 3: "Hard", 2: "Medium", 1: "Easy"}

# === Load dữ liệu cá ===
df = pd.read_csv("./dataset/fish_data.csv")

# === Chuẩn bị dữ liệu cho fish-rcm ===
df_reco = df.dropna(subset=['temperature_min', 'temperature_max', 'tank_size_liter', 'cm_max']).copy()
df_reco['temp'] = (df_reco['temperature_min'] + df_reco['temperature_max']) / 2

X = df_reco[['temp', 'tank_size_liter']]
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

knn = NearestNeighbors(n_neighbors=5)
knn.fit(X_scaled)

# === Hàm lấy thông tin cá ===
def get_fish_info(fish_name):
    fish_names = df['name_english'].dropna().tolist()
    best_match, score = process.extractOne(fish_name, fish_names)

    if score < 60:
        return {"error": f"⚠️ Không tìm thấy cá có tên '{fish_name}', thử lại với tên khác."}

    index = fish_names.index(best_match)
    fish = df.iloc[index]

    return {
        "Fish Name": best_match,
        "Minimum Tank Size": f"{fish['tank_size_liter']} L",
        "Temperature": f"{fish['temperature_min']} - {fish['temperature_max']}℃",
        "pH Range": f"{fish['phmin']} - {fish['phmax']}",
        "Max Size": f"{fish['cm_max']} cm",
        "Difficulty": codes_hardi.get(fish['uncare'], "Unknown"),
        "Availability": codes_avail.get(fish['availability'], "Unknown"),
        "Behavior": codes_behave.get(fish['school'], "Unknown"),
        "Aggression": codes_agres.get(fish['agression'], "Unknown"),
        "Breeding Difficulty": codes_breed.get(fish['breeding_difficulty'], "Unknown"),
    }

# === Gợi ý môi trường chung ===
def recommend_environment(fish_list):
    fish_data = []

    for fish_name in fish_list:
        fish_names = df['name_english'].dropna().tolist()
        best_match, score = process.extractOne(fish_name, fish_names)

        if score >= 60:
            index = fish_names.index(best_match)
            fish_data.append(df.iloc[index])

    if not fish_data:
        return json.dumps({"error": "⚠️ No matching fish found in the list."}, ensure_ascii=False)

    selected_df = pd.DataFrame(fish_data)
    selected_df["tank_size_liter"] = pd.to_numeric(selected_df["tank_size_liter"], errors='coerce')
    selected_df["temperature_min"] = pd.to_numeric(selected_df["temperature_min"], errors='coerce')
    selected_df["temperature_max"] = pd.to_numeric(selected_df["temperature_max"], errors='coerce')
    selected_df["phmin"] = pd.to_numeric(selected_df["phmin"], errors='coerce')
    selected_df["phmax"] = pd.to_numeric(selected_df["phmax"], errors='coerce')

    avg_tank_size = selected_df["tank_size_liter"].mean()
    avg_temp_min = selected_df["temperature_min"].mean()
    avg_temp_max = selected_df["temperature_max"].mean()
    avg_ph_min = selected_df["phmin"].mean()
    avg_ph_max = selected_df["phmax"].mean()

    environment = {
        "Recommended Tank Size": f"{avg_tank_size:.1f} L",
        "Recommended Temperature": f"{avg_temp_min:.1f} - {avg_temp_max:.1f}℃",
        "Recommended pH Range": f"{avg_ph_min:.1f} - {avg_ph_max:.1f}",
        "Included Fish": [fish["name_english"] for fish in fish_data]
    }

    return json.dumps(environment, ensure_ascii=False, indent=4)

# === Phân tích điều kiện bể hiện tại ===
def analyze_tank_conditions(fish_list, current_temp, current_ph, current_turbidity, current_quality):
    recommended_json = recommend_environment(fish_list)
    recommended = json.loads(recommended_json)

    if "error" in recommended:
        return recommended_json

    recommended_temp_min, recommended_temp_max = map(float, recommended["Recommended Temperature"].replace("℃", "").split(" - "))
    recommended_ph_min, recommended_ph_max = map(float, recommended["Recommended pH Range"].split(" - "))

    recommendations = []

    if current_temp < recommended_temp_min:
        recommendations.append(f"The water temperature is too low ({current_temp}℃). It should be increased to around {recommended_temp_min}-{recommended_temp_max}℃.")
    elif current_temp > recommended_temp_max:
        recommendations.append(f"The water temperature is too high ({current_temp}℃). It should be decreased to around {recommended_temp_min}-{recommended_temp_max}℃.")

    if current_ph < recommended_ph_min:
        recommendations.append(f"The pH level is too low ({current_ph}). It should be adjusted to around {recommended_ph_min}-{recommended_ph_max}.")
    elif current_ph > recommended_ph_max:
        recommendations.append(f"The pH level is too high ({current_ph}). It should be adjusted to around {recommended_ph_min}-{recommended_ph_max}.")

    if current_turbidity > 50:
        recommendations.append(f"The water is too cloudy ({current_turbidity}/100). Consider changing the water or using a filter.")

    if current_quality < 50:
        recommendations.append(f"The water quality is poor ({current_quality}/100). Check the filter and change the water regularly.")

    if not recommendations:
        return json.dumps({"message": "🎉 The aquarium environment is currently ideal!"}, ensure_ascii=False, indent=4)

    return json.dumps({"recommendations": recommendations}, ensure_ascii=False, indent=4)

# === Gợi ý cá theo kích thước bể và nhiệt độ ===
def recommend_fish(length, width, height, temp_input):
    tank_size_input = (length * width * height) / 1000

    input_df = pd.DataFrame([[temp_input, tank_size_input]], columns=['temp', 'tank_size_liter'])
    input_scaled = scaler.transform(input_df)
    distances, indices = knn.kneighbors(input_scaled)

    recommendations = []
    for idx in indices[0]:
        fish = df_reco.iloc[idx]

        if length < fish['cm_max'] or width < fish['cm_max']:
            quantity = 0
        else:
            quantity_by_area = int((length * width) / 400)
            quantity_by_volume = int(tank_size_input / (20 * 20 / 1000))
            quantity = min(quantity_by_area, quantity_by_volume)

        recommendations.append({
            'Name': str(fish['name_english']),
            'Temp': float(fish['temp']),
            'Tank Size': float(fish['tank_size_liter']),
            'Max Size (cm)': float(fish['cm_max']),
            'Est. Quantity': quantity
        })

    return recommendations

# === API ROUTES ===
@app.route("/")
def home():
    return "🐠 Fish Info API is running!"

@app.route("/fish", methods=["POST"])
def fish():
    data = request.get_json()
    fish_name = data.get("name", "")
    return jsonify(get_fish_info(fish_name))

@app.route("/fish-recommend", methods=["POST"])
def fish_recommend():
    data = request.get_json()
    fish_list = data.get("fish_list", [])
    if not fish_list:
        return jsonify({"error": "Missing 'fish_list' in request."}), 400
    result_json = recommend_environment(fish_list)
    return jsonify(json.loads(result_json))

@app.route("/fish-compare", methods=["POST"])
def compare_fish_environment():
    data = request.get_json()
    fish_list = data.get("fish_list", [])
    current_temp = data.get("temperature")
    current_ph = data.get("ph")
    current_turbidity = data.get("turbidity")
    current_quality = data.get("quality")

    if not fish_list or current_temp is None or current_ph is None or current_turbidity is None or current_quality is None:
        return jsonify({"error": "Missing input data. Required: fish_list, temperature, ph, turbidity, quality"}), 400

    result_json = analyze_tank_conditions(fish_list, current_temp, current_ph, current_turbidity, current_quality)
    return jsonify(json.loads(result_json))

@app.route("/fish-rcm", methods=["POST"])
def fish_rcm():
    data = request.get_json()
    length = data.get("length")
    width = data.get("width")
    height = data.get("height")
    temp_input = data.get("temperature")

    if None in (length, width, height, temp_input):
        return jsonify({"error": "Missing required fields: length, width, height, temperature"}), 400

    try:
        recommendations = recommend_fish(length, width, height, temp_input)
        return jsonify(recommendations)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Run Server ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
