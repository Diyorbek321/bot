# 🏫 Shanghai School — English Quiz Bot

**Shanghai School** o'quv markazi o'quvchilari uchun Telegram bot: **B2 darajadagi 500 ta inglizcha so'z** (o'zbekcha tarjimasi bilan)
bo'yicha test savollari, ball tizimi va reyting.

## ✨ Imkoniyatlar

- 🗳 **Ovoz berish ko'rinishida** — har bir savol Telegram quiz poll: 4 ta variantdan biriga ovoz beriladi, javobdan keyin to'g'risi va izoh ko'rinadi
- ✍️ **Gap to'ldirish** — har bir so'z uchun tayyor gaplar: `After sitting for hours, I went outside to ____.`
- 🔀 **4 xil yo'nalish** — gap to'ldirish, 🇬🇧→🇺🇿, 🇺🇿→🇬🇧 yoki aralash
- ⏱ **Har bir savolga 20 soniya** — vaqt tugasa avtomatik keyingi savolga o'tiladi
- 📚 **Kunlik lug'at (10 kun × 50 so'z)** — har bir so'z: definition, tarjima, sinonim, antonim, kulgili misol va 💡 assotsiatsiya; kartochkalar, PDF jadval va har kunga 50 savollik test
- 👥 **Jamoaviy quiz** — guruhda o'quvchilar jamoalarga (🔴 🔵 🟢 🟡) bo'linadi, a'zolar bali jamoaga yig'iladi, oxirida g'olib jamoa e'lon qilinadi
- 📊 **50 / 75 / 100** ta savoldan iborat testlar
- ⚡ **Ball tizimi — tezlikka qarab** — darhol to'g'ri javob 100 ball, 20-soniyada 50 ball, xato yoki vaqt tugasa 0
- 🏆 **Reyting** — umumiy va haftalik (so'nggi 7 kun) TOP-10
- 👤 **Profil** — ball, aniqlik foizi, eng uzun seriya, reytingdagi o'rin
- 🧠 **Xatolarim** — xato qilingan so'zlar saqlanadi va alohida mashq qilinadi

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
| `/quiz`  | Yangi quiz (guruhda — jamoaviy) |
| `/lugat` | Kunlik lug'at: kartochkalar, PDF, Day 1–10 testlari |
| `/stop`  | Quizni to'xtatish (boshlagan odam yoki admin) |
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

**Kunlik test guruhda:** `/lugat` → **Day N** → **🎯 Testni boshlash** — yoki `/quiz` → **📅 Kunlik testlar**.
Jamoa tanlash va o'yin xuddi yuqoridagidek, faqat savollar o'sha kunning 50 ta so'zidan.

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

## 📚 Kunlik lug'at

`vocab.json` — 500 ta so'z (`words.json` bilan bir xil tartibda), har biri PDF andozasi bo'yicha:

```json
{"en": "achieve", "uz": "erishmoq", "definition": "To succeed in reaching a goal.",
 "synonym": "Reach", "antonym": "Fail",
 "example": "I finally **achieved** my dream: I woke up before my alarm. Once.",
 "association": "\"A-chiv\" — jo'ja \"chiv-chiv\" deb tinmay urinib, oxiri donga ERISHDI."}
```

So'zlar tartib bo'yicha 10 kunga bo'linadi (1–50 → Day 1, 51–100 → Day 2, …). Kunlik test — kunning
har bir so'zidan bittadan savol, 5 xil tur navbat bilan: gap to'ldirish, definition, sinonim, 🇬🇧→🇺🇿, 🇺🇿→🇬🇧.
Javobdan keyin poll izohida so'z tarjimasi va assotsiatsiyasi chiqadi.

`vocab.json` o'zgargach PDF'larni qayta yarating (`fpdf2` va DejaVu shrifti kerak, serverda shart emas):

```bash
pip install fpdf2
python build_pdfs.py      # pdf/day01.pdf … pdf/day10.pdf
```

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
├── poll_game.py      # Quiz mantiqi (jamoalar, tezlik bo'yicha ball, reyting)
├── poll_handlers.py  # Quiz, jamoa tanlash va javob handlerlari
├── vocab.py          # Kunlik lug'at: kartochkalar, kunlik test savollari
├── day_handlers.py   # /lugat: kunlar, kartochkalar, PDF, kunlik test
├── build_pdfs.py     # vocab.json → pdf/dayNN.pdf
├── branding.py       # Umumiy matn bezaklari
├── keyboards.py      # Inline tugmalar
├── database.py       # SQLite: foydalanuvchilar, natijalar, xatolar
├── config.py         # Sozlamalar
├── extract_words.py  # PDF → words.json
├── deploy/           # systemd servis + o'rnatish skripti
├── tests/            # pytest testlari
├── sentences.json    # 1000 ta gap (har so'zga 2 ta)
├── vocab.json        # 500 ta so'z kartochkasi (definition, sinonim, antonim, misol, assotsiatsiya)
├── pdf/              # Kunlik lug'at PDF'lari (Day 1–10)
└── words.json        # 500 ta so'z
```
