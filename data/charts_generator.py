import json
from urllib.parse import quote


def generate_chart_url(user_data):
    limits = user_data.get('limits', {})
    if not limits:
        return None

    labels = []
    spent_values = []
    background_colors = [
        'rgba(255, 99, 132, 0.7)',
        'rgba(54, 162, 235, 0.7)',
        'rgba(255, 206, 86, 0.7)',
        'rgba(75, 192, 192, 0.7)',
        'rgba(153, 102, 255, 0.7)'
    ]

    for category, data in limits.items():
        labels.append(category)
        spent_values.append(float(data['spent']))

    chart_config = {
        "type": "pie",
        "data": {
            "labels": labels,
            "datasets": [{
                "data": spent_values,
                "backgroundColor": background_colors[:len(labels)]
            }]
        },
        "options": {
            "plugins": {
                "title": {
                    "display": True,
                    "text": "Ваши расходы по категориям",
                    "font": {"size": 16}
                },
                "legend": {
                    "position": "right",
                    "labels": {"font": {"size": 12}}
                }
            }
        }
    }

    try:
        json_config = json.dumps(chart_config, ensure_ascii=False)
        base_url = "https://quickchart.io/chart"
        return f"{base_url}?c={quote(json_config)}"
    except Exception as e:
        print(f"Ошибка при генерации URL графика: {e}")
        return None
