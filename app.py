from flask import Flask, request, jsonify
import pandas as pd
from fuzzywuzzy import process

app = Flask(__name__)

# Giải mã dữ liệu
codes_hardi = {4: "Beginner", 3: "Easy", 2: "Medium", 1: "Difficult"}
codes_avail = {4: "Very common", 3: "Common", 2: "Rare", 1: "Very rare"}
codes_behave = {3: "Schooling", 2: "Social", 1: "Solitary"}
codes_agres = {3: "Aggressive", 2: "Mostly peaceful", 1: "Peaceful"}
codes_breed = {4: "No record", 3: "Hard", 2: "Medium", 1: "Easy"}

# Load dữ liệu
df = pd.read_csv("./dataset/fish_data.csv")

# Hàm tìm thông tin cá
def get_fish_info(fish_name):
    fish_names = df['name_english'].dropna().tolist()
    result = process.extractOne(fish_name, fish_names)

    if not result:
        return {"error": "Không tìm thấy cá phù hợp."}

    best_match, score = result
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

# Route test
@app.route("/")
def home():
    return "🐠 Fish Info API is running!"

# Route xử lý API
@app.route("/fish-search", methods=["POST"])
def fish():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.get_json()
    fish_name = data.get("name", "")

    if not fish_name:
        return jsonify({"error": "Missing 'name' field in JSON."}), 400

    info = get_fish_info(fish_name)
    return jsonify(info)

# Chạy server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
