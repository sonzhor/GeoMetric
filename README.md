# Geo Intelligence API

REST API и веб-интерфейс для анализа территории и **ML-прогноза уровня развития района**.

Ввод: **город** или **координаты** → географические индикаторы → модель → **score 0–100** и категория развития.

| | |
|---|---|
| Стек | FastAPI · Pandas · Scikit-learn · Geopy · Leaflet |
| Версия | 2.1.0 (`config.json`) |
| UI | http://localhost:8000/ |
| Docs | http://localhost:8000/docs |

---

## Возможности

- Анализ по городу или координатам
- Клик по **карте** (Leaflet)
- **Сравнение** 2–5 локаций
- Индикаторы: плотность, зелень, инфраструктура, транспорт, экономика
- ML: GradientBoosting, R² ≈ 0.91
- UI адаптирован под телефон
- Готовые конфиги для Render / Railway

---

## Структура репозитория

```
geo_intelligence_api/
│
├── config.json                 # настройки приложения (JSON)
├── requirements.txt
├── run.py                      # точка входа
├── README.md
├── DEPLOY.md                   # деплой и тест с телефона
│
├── app/                        # backend + frontend
│   ├── main.py                 # FastAPI, эндпоинты
│   ├── geo_utils.py            # геокод, индикаторы
│   ├── predictor.py            # ML predict
│   └── static/                 # веб-UI
│       ├── index.html
│       ├── style.css
│       └── app.js
│
├── data/                       # данные (JSON + CSV)
│   ├── cities.json             # справочник городов
│   ├── sample_response.json    # пример ответа API
│   ├── training_samples.csv    # датасет обучения (8000 строк)
│   └── README.md
│
├── models/                     # обученная модель
│   ├── development_model.joblib
│   ├── feature_names.joblib
│   └── model_meta.json         # метрики модели (JSON)
│
├── ml/
│   └── train_model.py          # переобучение
│
├── Dockerfile
├── docker-compose.yml
├── Procfile
├── render.yaml
└── railway.toml
```

### JSON-файлы в проекте

| Файл | Описание |
|------|----------|
| `config.json` | Имя приложения, версия, пути к модели и данным |
| `data/cities.json` | Города и координаты для геокодирования |
| `data/sample_response.json` | Пример ответа `/analyze` |
| `models/model_meta.json` | Метрики и параметры обученной модели |

---

## Быстрый старт

```bash
git clone <your-repo-url>
cd geo_intelligence_api

python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

pip install -r requirements.txt
python run.py
```

Открыть: **http://localhost:8000/**

---

## API

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/` | Веб-интерфейс |
| GET | `/health` | Статус |
| GET | `/cities` | Список городов из `data/cities.json` |
| GET | `/analyze?city=Москва` | Анализ по городу |
| GET | `/analyze?lat=55.75&lon=37.62` | По координатам |
| POST | `/analyze/coords` | JSON `{"lat", "lon"}` |
| POST | `/analyze/city` | JSON `{"city"}` |
| POST | `/analyze/compare` | Сравнение локаций |
| GET | `/docs` | Swagger |

```bash
curl "http://localhost:8000/analyze?city=Москва"
curl "http://localhost:8000/cities"
curl "http://localhost:8000/health"
```

---

## Как устроен пайплайн

1. Город → координаты (`data/cities.json` или Nominatim)
2. По lat/lon считаются индикаторы (детерминированно + учёт крупных метро)
3. Feature engineering → модель из `models/`
4. Ответ: score, уровень, топ-факторы

Индикаторы сейчас **синтетические** (демо). В проде меняется только `generate_indicators()` в `geo_utils.py`.

Переобучение модели:

```bash
python ml/train_model.py
```

---

## Деплой и телефон

См. **[DEPLOY.md](DEPLOY.md)**.

Кратко (Render Free):

1. Push в GitHub  
2. render.com → Web Service → этот репо  
3. Build: `pip install -r requirements.txt`  
4. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`  
5. Открыть URL с телефона  

---

## Папка data/

Раньше могла казаться «пустой» в старых сборках: обучающая выборка жила только в RAM. Сейчас на диске:

- `cities.json` — справочник  
- `sample_response.json` — пример API  
- `training_samples.csv` — датасет для ML  

Подробнее: `data/README.md`.

---

## Ограничения

- Индикаторы не из официальной статистики — эвристики для демо и архитектуры  
- Nominatim нужен интернет и имеет лимиты  
- Free-хостинг может «засыпать» без трафика  

---

## Лицензия

Учебный / демонстрационный проект. Можно использовать в портфолио и обучении.
