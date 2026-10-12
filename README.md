# Yuz nazorati

Rasm, jonli kamera va video orqali yuzlarni ro‘yxatga olish hamda tanish uchun veb ilova. Boshqaruv paneli React’da, API FastAPI’da yozilgan. Yuzni aniqlash va embedding olish uchun InsightFace, embeddinglarni saqlash va qidirish uchun Qdrant ishlatiladi.

## Nimalar qilish mumkin?

| Bo‘lim | Vazifasi |
| --- | --- |
| **Foydalanuvchilar** | Ro‘yxatni ko‘rish, qidirish va foydalanuvchini o‘chirish |
| **Qo‘shish** | Tayyor rasm faylini yuklash yoki kameradan yuzni ro‘yxatga olish |
| **Tekshirish** | Kameradagi yuzlarni jonli aniqlash va bazadagi foydalanuvchilar bilan solishtirish |
| **Video** | Video fayldagi odamlarni topish, rasmlarini va ko‘ringan vaqtlarini chiqarish |

## Tez ishga tushirish

**Talablar:** Docker va Docker Compose. Birinchi build va model yuklanishi uchun internet kerak bo‘lishi mumkin.

1. Loyiha katalogida namuna sozlamalarni `.env` ga ko‘chiring:

   ```powershell
   Copy-Item .env.example .env
   ```

   Linux yoki macOS’da: `cp .env.example .env`.

2. Ilovani ishga tushiring:

   ```bash
   docker compose up --build -d
   ```

3. Ilova tayyor bo‘lishini tekshiring:

   ```bash
   docker compose ps
   docker compose logs -f app
   ```

4. Brauzerda **http://127.0.0.1:8080** manzilini oching.

| Manzil | Nima ochiladi? |
| --- | --- |
| `http://127.0.0.1:8080/` | Boshqaruv paneli |
| `http://127.0.0.1:8080/docs` | Interaktiv API hujjatlari |
| `http://127.0.0.1:8080/api/health` | Ilova holati |

To‘xtatish: `docker compose down`. Bu buyruq saqlangan yuzlar va Qdrant ma’lumotlari joylashgan Docker volume’larini o‘chirmaydi.

### Model yuklanmasa

Loyiha `antelopev2` model to‘plamidan foydalanadi. Backend avval `/root/.insightface/models/antelopev2` ichidagi ONNX fayllarini qidiradi; shu katalog bo‘lmasa, `antelopev2.zip` arxivini ochishga urinadi. Fayllar topilmasa, InsightFace modelni yuklab ko‘radi. Yuklash bajarilmasa, [InsightFace model ro‘yxati](https://github.com/deepinsight/insightface/blob/master/python-package/docs/model_zoo.md) orqali modelni olib, Docker’dagi `insightface_data` volume’ining `models/antelopev2/` katalogiga joylashtirish kerak. Xatoni `docker compose logs app` orqali ko‘ring.

## Tizim qanday ishlaydi?

```text
Brauzer
  ├─ rasm fayli ────────────────┐
  ├─ kamera (WebRTC) ────────────┼─ FastAPI ─ InsightFace ─ Qdrant
  └─ video fayli ────────────────┘               │
                                                 ├─ SCRFD: yuzni topish
                                                 └─ tanish modeli: embedding olish
```

1. **Yuzni topish.** SCRFD kadrdagi yuzning joyini (`bbox`) va aniqlash bahosini beradi.
2. **Yuzni tasvirlash.** InsightFace tanish modeli yuzdan sonlar vektori — **embedding** — oladi.
3. **Saqlash yoki qidirish.** Ro‘yxatga olishda embedding Qdrant’ga yoziladi. Tekshirishda esa yangi embedding bazadagi embeddinglar bilan solishtiriladi.
4. **Natija.** Topilgan foydalanuvchi yoki “noma’lum” holati frontendga qaytariladi.

### Ekrandagi foizlar nimani bildiradi?

| Ko‘rsatkich | Manbasi | Ma’nosi |
| --- | --- | --- |
| **Yuz aniqlash** | SCRFD detektori | Shu kadrdagi obyektni yuz sifatida aniqlash bali |
| **Moslik** | Qdrant’dagi vektor qidiruvi | Topilgan yuzning bazadagi foydalanuvchi embeddingiga o‘xshashligi |
| `_quality_score` | Ilova ichidagi hisob | Tiniqlik, yorug‘lik, o‘lcham va yuz holatiga qarab yaxshi kadrni tanlash |

**Yuz aniqlash** va **Moslik** foizlari model ballarining 100 ga ko‘paytirilgan ko‘rinishi. Masalan, `0.91` ekranda `91%` bo‘ladi; bu matematik kafolatlangan 91% ehtimollik degani emas. `_quality_score` foydalanuvchiga foiz sifatida ko‘rsatilmaydi.

## Foydalanuvchini qo‘shish

**Rasm fayli orqali:**

1. **Qo‘shish** sahifasiga o‘ting. U dastlab **Rasm faylini yuklash** usulida ochiladi.
2. Foydalanuvchi ID va to‘liq ismni kiriting.
3. Kompyuterdan JPEG, PNG yoki WebP faylni tanlang va yuboring.

Rasm **8 MB dan katta bo‘lmasligi**, unda **bitta yuz** bo‘lishi va yuzning kichik tomoni kamida **80 piksel** bo‘lishi kerak. Backend mavjud ID va o‘xshash yuzni qayta qo‘shishni tekshiradi.

**Kamera orqali:** shu sahifadagi **Kamera orqali** tanlovini bosing. Kamera bir nechta yuz namunalarini olib, mos keladiganlarini tanlaydi va foydalanuvchini ro‘yxatga qo‘shadi.

Rasm fayli yuboriladigan API:

```text
POST /api/v1/faces
Content-Type: multipart/form-data

user_id   = foydalanuvchi ID
full_name = to‘liq ism
image     = rasm faylining o‘zi
```

Masalan, terminalda:

```bash
curl -X POST http://127.0.0.1:8080/api/v1/faces \
  -F "user_id=8853120" \
  -F "full_name=Ism Familiya" \
  -F "image=@face.jpg"
```

PowerShell’da `curl.exe` ishlating va buyruqni bir qatorda yozing.

## Jonli tekshirish

**Tekshirish** sahifasi brauzer kamerasini WebRTC orqali backendga uzatadi. Backend yuzlarni kuzatadi, mos namunalarni yig‘adi va Qdrant’da qidiradi. Ekranda yuzning joyi, **Yuz aniqlash** bali va foydalanuvchi topilsa **Moslik** bali chiqadi. Noma’lum yuzlar ham ko‘rsatiladi.

Kamera ishlashi uchun brauzerga kamera ruxsatini berish kerak. WebRTC aloqa `POST /api/v1/detection/offer` orqali boshlanadi; kamera bilan ro‘yxatga olish uchun `POST /api/v1/faces/enroll/offer` ishlatiladi.

## Video tahlili

1. **Video** sahifasida MP4, MOV, AVI, WebM yoki MKV faylni tanlang.
2. **Tahlilni boshlash** tugmasini bosing. Maksimal fayl hajmi **500 MB**.
3. Jarayon tugagach, har bir topilgan odam uchun tanlangan yuz rasmi, **Yuz aniqlash** bali, bazada bo‘lsa **Moslik** bali va videoda ko‘ringan vaqtlar chiqadi.

Video qayta ishlashda kadrlar kuzatiladi va bir odamning takroriy ko‘rinishlari birlashtiriladi. `_quality_score` yaxshi rasmni tanlaydi; rasm yonidagi **Yuz aniqlash** foizi aynan o‘sha rasm kadridagi SCRFD bahosidir.

Video vazifalari backend jarayonining xotirasida turadi. Tayyor natija **10 daqiqa** saqlanadi va natija API’dan olingach o‘chiriladi. Backend qayta ishga tushsa, davom etayotgan vazifalar va xotiradagi natijalar yo‘qoladi. Yuklangan video fayli tahlil tugagach vaqtinchalik katalogdan o‘chiriladi.

## API qisqacha

Barcha endpointlarning batafsil so‘rov va javob shakllari `/docs` sahifasida mavjud.

| Usul | Endpoint | Vazifasi |
| --- | --- | --- |
| `GET` | `/api/v1/faces` | Foydalanuvchilar ro‘yxati |
| `POST` | `/api/v1/faces` | Rasm fayli orqali qo‘shish |
| `DELETE` | `/api/v1/faces/{user_id}` | Foydalanuvchini o‘chirish |
| `POST` | `/api/v1/faces/enroll/offer` | Kamera bilan ro‘yxatga olish |
| `POST` | `/api/v1/detection/offer` | Jonli tanish |
| `POST` | `/api/v1/video-analysis` | Videoni tahlilga yuborish; `file` maydoni |
| `GET` | `/api/v1/video-analysis/{job_id}` | Vazifa holati va progress |
| `GET` | `/api/v1/video-analysis/{job_id}/result` | Tayyor tahlil natijasi |

## Sozlamalar va saqlash

Namuna qiymatlar [`.env.example`](.env.example) da. Docker Compose `.env` faylidan foydalanadi.

| O‘zgaruvchi | Vazifasi | Standart namuna |
| --- | --- | --- |
| `CONTAINER_PREFIX` | Konteyner nomlari prefiksi | `face_detection` |
| `APP_BIND_IP` | Hostdagi tinglash manzili | `127.0.0.1` |
| `APP_PORT` | Hostdagi port | `8080` |
| `QDRANT_HOST`, `QDRANT_PORT` | Qdrant manzili | `qdrant`, `6333` |
| `QDRANT_API_KEY` | Qdrant kaliti, agar ishlatilsa | bo‘sh |
| `QDRANT_TIMEOUT` | Ulanish kutish vaqti, soniyada | `5` |
| `QDRANT_CONNECT_RETRIES` | Ulanishga urinishlar soni | `30` |
| `QDRANT_RETRY_DELAY` | Urinishlar oralig‘i, soniyada | `1` |
| `JWT_SECRET_KEY` | Loyihadagi JWT yordamchi moduli kaliti | `.env.example` dagi namuna |

| Docker volume | Saqlanadigan ma’lumot |
| --- | --- |
| `qdrant_data` | Yuz embeddinglari va foydalanuvchi ma’lumotlari |
| `face_images` | Ro‘yxatga olingan yuz rasmlari |
| `insightface_data` | InsightFace model fayllari |

Hozir model `CPUExecutionProvider` bilan ishlaydi. NVIDIA GPUga o‘tkazishda mos ONNX Runtime GPU paketi, CUDA/cuDNN muhiti va Docker’ga GPU ulash kerak bo‘ladi. Bundan tashqari, hozir backend **bitta worker** bilan ishlaydi, video tahlili esa bir vaqtda **bitta vazifa**ni bajaradi.

## Kod tuzilmasi

```text
app/
  api/                   yuzlar, jonli aniqlash va video API’lari
  config/                FastAPI, model va Qdrant sozlamalari
  resources/detection/   kamera oqimi va yuzni tanish
  resources/video_analysis/  video kadrlarini tahlil qilish
  resources/repositories/    Qdrant bilan ishlash
frontend/src/
  pages/                 boshqaruv paneli sahifalari
  lib/api.ts             frontenddan API so‘rovlari
docker/                  Docker image
requirements/            Python paketlari
scripts/                 serverni ishga tushirish
docker-compose.yml       ilova va Qdrant
```
