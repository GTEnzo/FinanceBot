import json
from urllib.parse import quote  # для кодирования URL-адресов


# функция генерации URL для диаграммы расходов
def generate_chart_url(user_data):
    # получаем данные о лимитах из переданного словаря пользователя
    limits = user_data.get('limits', {})
    # если лимиты не заданы, возвращаем None
    if not limits:
        return None
    # инициализируем списки для данных диаграммы
    labels = []  # названия категорий
    spent_values = []  # потраченные суммы по категориям

    # цвета для секторов диаграммы
    background_colors = [
        'rgba(255, 99, 132, 0.7)',
        'rgba(54, 162, 235, 0.7)',
        'rgba(255, 206, 86, 0.7)',
        'rgba(75, 192, 192, 0.7)',
        'rgba(153, 102, 255, 0.7)'
    ]

    # Заполняем списки данными из лимитов пользователя
    for category, data in limits.items():
        labels.append(category)  # Добавляем название категории
        spent_values.append(float(data['spent']))  # Добавляем потраченную сумму

    # формируем конфигурацию диаграммы в формате Chart.js
    chart_config = {
        "type": "pie",  # mип диаграммы - круговая
        "data": {
            "labels": labels,  # подписи категорий
            "datasets": [{
                "data": spent_values,  # данные для отображения
                "backgroundColor": background_colors[:len(labels)]  # цвета секторов
            }]
        },
        "options": {
            "plugins": {
                "title": {
                    "display": True,  # показывать заголовок
                    "text": "Ваши расходы по категориям",  # текст заголовка
                    "font": {"size": 16}  # размер шрифта заголовка
                },
                "legend": {
                    "position": "right",  # позиция легенды
                    "labels": {"font": {"size": 12}}  # размер шрифта легенды
                }
            }
        }
    }

    # пытаемся сформировать URL для диаграммы
    try:
        # преобразуем конфигурацию в JSON-строку
        json_config = json.dumps(chart_config, ensure_ascii=False)
        # базовый URL сервиса QuickChart
        base_url = "https://quickchart.io/chart"
        # формируем полный URL с параметрами
        return f"{base_url}?c={quote(json_config)}"
    except Exception as e:
        # в случае ошибки выводим сообщение и возвращаем None
        print(f"Ошибка при генерации URL графика: {e}")
        return None