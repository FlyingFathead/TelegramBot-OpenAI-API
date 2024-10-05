# token_usage_visualization.py

import matplotlib.pyplot as plt
import json

def generate_usage_chart(token_usage_file, output_image_file):
    try:
        with open(token_usage_file, 'r') as file:
            data = json.load(file)

        dates = list(data.keys())
        usage = list(data.values())

        plt.figure(figsize=(10, 6))
        plt.bar(dates, usage, color='blue')
        plt.xlabel('Date')
        plt.ylabel('Token Usage')
        plt.xticks(rotation=45)
        plt.title('Daily Token Usage')
        plt.tight_layout()
        plt.savefig(output_image_file)

    except Exception as e:
        print(f"Error generating usage chart: {e}")
        return None
