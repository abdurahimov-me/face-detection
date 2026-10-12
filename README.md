# Yuz nazorati

Yuzlarni ro‘yxatga olish, jonli kamerada tanish va yuklangan videoni tahlil qilish uchun veb ilova. Backend **FastAPI** va **InsightFace** bilan ishlaydi, yuz embeddinglari **Qdrant**da saqlanadi. Boshqaruv paneli **React** asosida qurilgan.

## Imkoniyatlar

- Foydalanuvchini **tayyor rasm fayli** (JPEG, PNG, WebP) yoki **kamera** orqali qo‘shish.
- Kameradagi yuzlarni WebRTC orqali jonli aniqlash.
- Video fayldagi odamlarni aniqlash va ko‘ringan vaqt oraliqlarini chiqarish.
- Foydalanuvchilar ro‘yxatini ko‘rish va foydalanuvchini o‘chirish.

## Tez boshlash

**Kerak bo‘ladi:** Docker va Docker Compose. Dastlabki ishga tushishda Docker image va InsightFace modeli yuklanishi sababli internet ham kerak bo‘lishi mumkin.

1. Namuna sozlamalarni ko‘chiring:

   ```bash
   cp .env.example .env
   ```

   Windows PowerShell uchun: `Copy-Item .env.example .env`.

2. Ilovani ishga tushiring:

   ```bash
   docker compose up --build -d
   ```

3. Brauzerda **http://127.0.0.1:8080** manzilini oching.

| Manzil | Vazifasi |
| --- | --- |
| `http://127.0.0.1:8080/` | Boshqaruv paneli |
| `http://127.0.0.1:8080/docs` | Swagger API hujjatlari |
| `http://127.0.0.1:8080/api/health` | Ilova holati |

Loglarni ko‘rish: `docker compose logs -f app`. To‘xtatish: `docker compose down`.

> Qdrant ma’lumotlari, InsightFace modeli va saqlangan yuz rasmlari Docker volume’larida turadi. Oddiy `docker compose down` ularni o‘chirmaydi.

## Sozlamalar

Asosiy qiymatlar [`.env.example`](.env.example) da berilgan. `.env` faylini o‘zingizning muhitingizga moslang.

| O‘zgaruvchi | Vazifasi | Namuna qiymat |
| --- | --- | --- |
| `APP_BIND_IP` | Ilova bog‘lanadigan host manzili | `127.0.0.1` |
| `APP_PORT` | Hostdagi port | `8080` |
| `QDRANT_HOST` | Qdrant manzili; Compose ichida servis nomi | `qdrant` |
| `QDRANT_PORT` | Qdrant porti | `6333` |
| `QDRANT_API_KEY` | Qdrant API kaliti, kerak bo‘lsa | bo‘sh |
| `QDRANT_CONNECT_RETRIES` | Ulanishga qayta urinishlar soni | `30` |

Standart `APP_BIND_IP=127.0.0.1` ilovani faqat shu kompyuterdan ochadi. Ilovani tarmoqqa chiqarishdan oldin API endpointlariga kirishni cheklash kerak: hozirgi yuz qo‘shish va o‘chirish endpointlarida autentifikatsiya yo‘q.

## Foydalanuvchi qo‘shish

Paneldagi **Qo‘shish** sahifasi rasm faylini tanlash usulida ochiladi. ID va to‘liq ismni kiriting, so‘ng JPEG, PNG yoki WebP faylni tanlab yuboring. Kamera orqali qo‘shish alohida tanlovda mavjud.

Rasm uchun cheklovlar: **8 MB gacha**, kadrda **bitta yuz**, yuz o‘lchami kamida **80 px**. Mavjud ID yoki avval ro‘yxatdan o‘tgan yuz qayta qo‘shilmaydi.

API orqali yuborish:

```bash
curl -X POST http://127.0.0.1:8080/api/v1/faces \
  -F "user_id=8853120" \
  -F "full_name=Ism Familiya" \
  -F "image=@/path/to/face.jpg"
```

PowerShell’da `curl` o‘rniga `curl.exe` ishlating va buyruqni bir qatorda yozing. Fayl `multipart/form-data` so‘rovidagi `image` maydonida yuboriladi.

## Asosiy API

| Usul | Endpoint | Vazifasi |
| --- | --- | --- |
| `GET` | `/api/v1/faces` | Ro‘yxatdan o‘tgan foydalanuvchilar |
| `POST` | `/api/v1/faces` | Rasm fayli orqali qo‘shish |
| `DELETE` | `/api/v1/faces/{user_id}` | Foydalanuvchini o‘chirish |
| `POST` | `/api/v1/faces/enroll/offer` | Kamera orqali qo‘shish uchun WebRTC offer |
| `POST` | `/api/v1/detection/offer` | Jonli tanish uchun WebRTC offer |
| `POST` | `/api/v1/video-analysis` | Video faylni tahlilga yuborish |
| `GET` | `/api/v1/video-analysis/{job_id}` | Tahlil holati va progress |
| `GET` | `/api/v1/video-analysis/{job_id}/result` | Tayyor natija |

Video yuklashda `file` nomli `multipart/form-data` maydonidan foydalaniladi. Qo‘llab-quvvatlanadigan formatlar: MP4, MOV, AVI, WebM va MKV; limit **500 MB**. Video natijasi server jarayoni xotirasida saqlanadi, **10 daqiqadan** keyin eskiradi va natija endpointidan olingach o‘chiriladi. Ilova jarayoni qayta ishga tushsa, kutilayotgan vazifalar va xotiradagi natijalar yo‘qoladi.

## Loyiha tuzilmasi

```text
app/
  api/              HTTP va WebRTC endpointlari
  config/           FastAPI va Qdrant sozlamalari
  resources/        yuzni tanish, video tahlili va repositorylar
frontend/
  src/pages/        boshqaruv paneli sahifalari
  src/lib/          API so‘rovlari va querylar
docker/             ilova Dockerfile’i
requirements/       Python paketlari
scripts/            ishga tushirish skriptlari
docker-compose.yml  ilova va Qdrant servislari
```

Docker build frontendni yig‘ib, backend bilan bitta ilova sifatida taqdim etadi. Backend ishga tushganda Qdrantga ulanadi, yuzlar kolleksiyasini tayyorlaydi va InsightFace modelini yuklaydi.
