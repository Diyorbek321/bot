# 🏫 Shanghai School — English Quiz Bot

**Shanghai School** o'quv markazi o'quvchilari uchun Telegram bot: **B2 darajadagi 500 ta inglizcha so'z** (o'zbekcha tarjimasi bilan)
bo'yicha test savollari, ball tizimi va reyting.

## ✨ Imkoniyatlar

- 🎯 **Test savollari** — har bir savolda 4 ta variant (A, B, C, D)
- ✍️ **Gap to'ldirish** — har bir so'z uchun tayyor gaplar: `After sitting for hours, I went outside to ____.`
- 🔀 **4 xil yo'nalish** — gap to'ldirish, 🇬🇧→🇺🇿, 🇺🇿→🇬🇧 yoki aralash
- ⏱ **Har bir savolga 20 soniya** — vaqt tugasa avtomatik keyingi savolga o'tiladi (poll quizda ham, tugmali testda ham)
- 👥 **Jamoaviy quiz** — guruhda o'quvchilar jamoalarga (🔴 🔵 🟢 🟡) bo'linadi, a'zolar bali jamoaga yig'iladi, oxirida g'olib jamoa e'lon qilinadi
- 📊 **50 / 75 / 100** ta savoldan iborat testlar
- ⚡ **Ball tizimi — tezlikka qarab** — darhol to'g'ri javob 100 ball, 20-soniyada 50 ball, xato yoki vaqt tugasa 0
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

## 🖥 Serverga o'rnatish (systemd)

Linux server (Ubuntu/Debian), Python 3.10+ va `python3-venv` kerak.

```bash
# 1. Kodni serverga yuklang
scp -r telegram_bot user@SERVER:~/

# 2. Serverda o'rnating
ssh user@SERVER
sudo bash ~/telegram_bot/deploy/install.sh

# 3. Tokenni yozing va botni ishga tushiring
sudo nano /opt/shanghai-quiz-bot/.env        # TOKEN=...
sudo systemctl restart shanghai-quiz-bot
```

Skript `quizbot` tizim foydalanuvchisini yaratadi, kodni `/opt/shanghai-quiz-bot` ga
nusxalaydi, venv o'rnatadi va servisni yoqadi. Bot server qayta yoqilganda va xato bilan
to'xtaganda avtomatik qayta ishga tushadi.

**Yangilash:** yangi kodni yuklab, `sudo bash deploy/install.sh` ni qayta ishga tushiring —
`.env` va `quiz.db` saqlanib qoladi.

| Vazifa | Buyruq |
|--------|--------|
| Holati | `systemctl status shanghai-quiz-bot` |
| Loglar (jonli) | `journalctl -u shanghai-quiz-bot -f` |
| Qayta ishga tushirish | `sudo systemctl restart shanghai-quiz-bot` |
| To'xtatish | `sudo systemctl stop shanghai-quiz-bot` |
| Bazaning zaxira nusxasi | `sudo cp /opt/shanghai-quiz-bot/quiz.db ~/quiz-$(date +%F).db` |

> ⚠️ Bitta token bilan faqat bitta nusxa ishlashi mumkin — serverda ishga tushirgach,
> kompyuteringizdagi botni to'xtating, aks holda `Conflict` xatosi chiqadi.

## ⌨️ Buyruqlar

| Buyruq  | Vazifasi        |
|---------|-----------------|
| `/start` | Bosh menyu     |
| `/quiz`  | Yangi test (guruhda — vaqtli quiz) |
| `/stop`  | Vaqtli quizni to'xtatish (boshlagan odam yoki admin) |
| `/top`   | Reyting        |
| `/me`    | Profilim       |
| `/help`  | Yordam         |

## 👥 Guruhda ishlatish

1. Bosh menyudagi **➕ Guruhga qo'shish** tugmasi orqali botni guruhga qo'shing.
2. Guruhda `/quiz` yozing → savol turi → savollar soni.
3. Chiqqan xabarda o'quvchilar jamoasini tanlaydi (jamoani almashtirish ham mumkin).
   Kamida 2 ta jamoada o'yinchi bo'lgach, quizni ochgan odam yoki admin **▶️ Boshlash** ni bosadi.
4. Savollar birin-ketin poll bo'lib chiqadi, har biriga 20 soniya; vaqt tugagach keyingisi yuboriladi.
5. Oxirida g'olib jamoa va eng yaxshi o'yinchilar e'lon qilinadi, har bir qatnashchining bali umumiy reytingga ham qo'shiladi.

Jamoa bali — a'zolar ballari yig'indisi. Jamoa tanlamay javob bergan o'quvchi avtomatik eng kam a'zoli jamoaga qo'shiladi.
Jamoalar ro'yxati `config.py` dagi `TEAMS` da.

Ketma-ket 3 ta savolga hech kim javob bermasa, quiz o'zi to'xtaydi.
Shaxsiy chatda javob berishingiz bilan keyingi savolga o'tiladi (yakka o'yin).

## ✍️ Gaplar banki

`sentences.json` — har bir so'z uchun 2 ta gap, to'g'ri javob (so'zning gapdagi shakli) va 3 ta xato variant:

```json
{"word": "achieve", "sentences": [
  {"text": "She worked hard every day to ____ her goal.", "answer": "achieve", "wrong": ["avoid", "refuse", "delay"]}
]}
```

Yangi gap qo'shgach, `python -m pytest tests` bilan bank to'g'riligini tekshiring.

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
├── poll_game.py      # Vaqtli quiz mantiqi (jamoalar, tezlik bo'yicha ball, reyting)
├── poll_handlers.py  # Vaqtli quiz va guruh handlerlari
├── branding.py       # Umumiy matn bezaklari
├── keyboards.py      # Inline tugmalar
├── database.py       # SQLite: foydalanuvchilar, natijalar, xatolar
├── config.py         # Sozlamalar
├── extract_words.py  # PDF → words.json
├── deploy/           # systemd servis + o'rnatish skripti
├── tests/            # pytest testlari
├── sentences.json    # 1000 ta gap (har so'zga 2 ta)
└── words.json        # 500 ta so'z
```
