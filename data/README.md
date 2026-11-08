# data/

| Файл | Формат | Описание |
|------|--------|----------|
| `cities.json` | JSON | Справочник городов (name, lat, lon). Используется геокодером и `GET /cities`. |
| `sample_response.json` | JSON | Пример ответа API для Москвы. |
| `training_samples.csv` | CSV | 8000 строк синтетического датасета для обучения модели. |

Обновить CSV и модель:

```bash
python ml/train_model.py
```
