from flask import Flask, request, jsonify
import pandas as pd
from fuzzywuzzy import process
import json

app = Flask(__name__)

# Bảng mã giải mã
codes_hardi = {4: "Beginner", 3: "Easy", 2: "Medium", 1: "Difficult"}
codes_avail = {4: "Very common", 3: "Common", 2: "Rare", 1: "Very rare"}
codes_behave = {3: "Schooling", 2: "Social", 1: "Solitary"}
codes_agres = {3: "Aggressive", 2: "Mostly peaceful", 1: "Peaceful"}
codes_breed = {4: "No record", 3: "Hard", 2: "Medium", 1: "Easy"}

# Load CSV
df = pd.read_csv("./dataset/fish_data.csv")


def get_fish_info(fish_name):
    fish_names = df['name_english'].dropna().tolist()
    best_match, score = process.extractOne(fish_name, fish_names)
    index = fish_names.index(best_match)

    if score < 60:
        return {"error": f"⚠️ Không tìm thấy cá có tên '{fish_name}', thử lại với tên khác."}

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


# ✅ Hàm gợi ý môi trường cho danh sách cá
def recommend_environment(fish_list):
    fish_data = []

    for fish_name in fish_list:
        fish_names = df['name_english'].dropna().tolist()
        best_match, score = process.extractOne(fish_name, fish_names)
        if score >= 60:
            index = fish_names.index(best_match)
            fish_data.append(df.iloc[index])

    if not fish_data:
        return {"error": "⚠️ No matching fish found in the list."}

    selected_df = pd.DataFrame(fish_data)

    # Chuyển kiểu dữ liệu sang số
    for col in ["tank_size_liter", "temperature_min", "temperature_max", "phmin", "phmax"]:
        selected_df[col] = pd.to_numeric(selected_df[col], errors='coerce')

    # Tính trung bình
    avg_tank_size = selected_df["tank_size_liter"].mean()
    avg_temp_min = selected_df["temperature_min"].mean()
    avg_temp_max = selected_df["temperature_max"].mean()
    avg_ph_min = selected_df["phmin"].mean()
    avg_ph_max = selected_df["phmax"].mean()

    return {
        "Recommended Tank Size": f"{avg_tank_size:.1f} L",
        "Recommended Temperature": f"{avg_temp_min:.1f} - {avg_temp_max:.1f}℃",
        "Recommended pH Range": f"{avg_ph_min:.1f} - {avg_ph_max:.1f}",
        "Included Fish": [fish["name_english"] for fish in fish_data]
    }


@app.route("/")
def home():
    return "🐠 Fish Info API is running!"


@app.route("/fish", methods=["POST"])
def fish():
    data = request.get_json()
    fish_name = data.get("name", "")
    return jsonify(get_fish_info(fish_name))


# ✅ API mới: Gợi ý môi trường nuôi dựa trên danh sách cá
@app.route("/fish-recommend", methods=["POST"])
def fish_recommend():
    data = request.get_json()
    fish_list = data.get("fish_list", [])
    return jsonify(recommend_environment(fish_list))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
