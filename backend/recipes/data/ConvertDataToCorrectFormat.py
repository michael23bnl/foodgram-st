import json
import os

current_dir = os.path.dirname(os.path.abspath(__file__))

input_file_path = os.path.join(current_dir, "../../../data/ingredients.json")

with open(input_file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

formatted_data = [
    {"model": "recipes.ingredient", "pk": i + 1, "fields": item}
    for i, item in enumerate(data)
]

output_file_path = os.path.join(
    current_dir, "../../../backend/recipes/data/ingredients.json")

with open(output_file_path, "w", encoding="utf-8") as f:
    json.dump(formatted_data, f, ensure_ascii=False, indent=4)
