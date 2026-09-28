# 🏫 Shanghai School — English Quiz Bot

**Shanghai School** o'quv markazi o'quvchilari uchun Telegram bot: **B2 darajadagi 500 ta inglizcha so'z** (o'zbekcha tarjimasi bilan)
bo'yicha test savollari, ball tizimi va reyting.

## ✨ Imkoniyatlar

- 🎯 **Test savollari** — har bir savolda 4 ta variant (A, B, C, D)
- 🔀 **3 xil yo'nalish** — 🇬🇧→🇺🇿, 🇺🇿→🇬🇧 yoki aralash
- 📊 **10 / 20 / 30** ta savoldan iborat testlar
- ⭐ **Ball tizimi** — to'g'ri javob 10 ball, ketma-ket to'g'ri javoblar uchun +2 … +10 bonus 🔥
- 🏆 **Reyting** — umumiy va haftalik (so'nggi 7 kun) TOP-10
- 👤 **Profil** — ball, aniqlik foizi, eng uzun seriya, reytingdagi o'rin
- 🧠 **Xatolarim** — xato qilingan so'zlar saqlanadi va alohida mashq qilinadi
- 🟩 Progress bar, har bir javobdan keyin darhol natija ko'rsatiladi

## 🏷 Brend

Brend nomi va shiori `config.py` faylida (`BRAND_NAME`, `BRAND_SLOGAN`) — bot matnlarida
va Telegram'dagi bot tavsifida avtomatik ishlatiladi.

## 🚀 Ishga tushirish

1. [@BotFather](https://t.me/BotFather) orqali yangi bot yarating va tokenni oling.
2. O'rnatish:

   ```bash
   cd telegram_bot
   python -m venv .venv
   source .venv/bin/activate      # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env           # keyin .env ichiga tokenni yozing
   ```

3. Botni ishga tushiring:

   ```bash
   python bot.py
   ```

Natijalar `quiz.db` (SQLite) faylida saqlanadi — alohida baza o'rnatish shart emas.

## ⌨️ Buyruqlar

| Buyruq  | Vazifasi        |
|---------|-----------------|
| `/start` | Bosh menyu     |
| `/quiz`  | Yangi test     |
| `/top`   | Reyting        |
| `/me`    | Profilim       |
| `/help`  | Yordam         |

## 📖 Lug'atni yangilash

So'zlar `words.json` faylida saqlanadi. Boshqa PDF lug'atdan yangilash uchun
(qatorlar `1. achieve — erishmoq` ko'rinishida bo'lishi kerak):

```bash
python extract_words.py lugat.pdf
```

Yoki `words.json` faylini qo'lda tahrirlang:

```json
[
 {"en": "achieve", "uz": "erishmoq"}
]
```

## 🗂 Tuzilishi

```
telegram_bot/
├── bot.py            # Handlerlar va ishga tushirish
├── quiz.py           # Savollar tuzish, ball hisoblash
├── keyboards.py      # Inline tugmalar
├── database.py       # SQLite: foydalanuvchilar, natijalar, xatolar
├── config.py         # Sozlamalar
├── extract_words.py  # PDF → words.json
└── words.json        # 500 ta so'z
```
