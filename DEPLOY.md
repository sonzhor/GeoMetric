# Деплой и тест с телефона

## Самый простой бесплатный путь: Render

1. Залей проект на **GitHub** (см. ниже).
2. Зайди на https://render.com → Sign up (через GitHub).
3. **New +** → **Web Service** → подключи репозиторий.
4. Настройки:
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance type:** Free
5. Create Web Service → жди 3–7 минут.
6. Открой выданный URL, например:
   `https://geo-intelligence-api-xxxx.onrender.com`

На **телефоне** просто открой этот URL в браузере — сайт и API работают.

> Бесплатный план Render «засыпает» после ~15 мин без запросов.  
> Первый заход после сна может занять 30–60 сек — это нормально.

### Или через Blueprint
Если в репо есть `render.yaml`:
- New → **Blueprint** → выбери репозиторий → Apply.

---

## Альтернатива: Railway

1. https://railway.app → Login with GitHub  
2. **New Project** → **Deploy from GitHub repo**  
3. Выбери репо — подхватится `Dockerfile`  
4. Settings → Networking → **Generate Domain**  
5. Открой домен с телефона.

Railway иногда даёт trial-кредиты; условия бесплатности меняются — смотри актуальный billing.

---

## Залить на GitHub (обязательно перед деплоем)

```bash
cd geo_intelligence_api
git init
git add .
git commit -m "Geo Intelligence API"
```

На github.com создай пустой репозиторий, затем:

```bash
git remote add origin https://github.com/ТВОЙ_ЛОГИН/geo-intelligence-api.git
git branch -M main
git push -u origin main
```

---

## Тест с телефона

### После деплоя (интернет)
Просто открой в браузере телефона:
```
https://ТВОЙ-СЕРВИС.onrender.com/
```
- Город / координаты / карта / сравнение — всё там же  
- API docs: `https://.../docs`

### Без деплоя (домашний Wi‑Fi)
1. На компе:
```bash
python run.py
```
2. Узнай IP компа в Wi‑Fi (`ipconfig` / `ip a`), например `192.168.1.10`
3. На телефоне (тот же Wi‑Fi):
```
http://192.168.1.10:8000/
```

---

## Проверка после деплоя

```text
GET https://ТВОЙ-URL/health
→ {"status":"ok","model_version":"2.1"}

GET https://ТВОЙ-URL/analyze?city=Москва
→ JSON с development_score
```

С телефона удобно открыть `/docs` и жать Try it out.
