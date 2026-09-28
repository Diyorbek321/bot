#!/usr/bin/env bash
# Serverda root sifatida ishga tushiring:  sudo bash deploy/install.sh
# Qayta ishga tushirish xavfsiz: kod yangilanadi, .env va quiz.db tegilmaydi.
set -euo pipefail

APP_DIR=/opt/shanghai-quiz-bot
APP_USER=quizbot
SERVICE=shanghai-quiz-bot
SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [[ $EUID -ne 0 ]]; then
    echo "Root huquqi kerak: sudo bash $0" >&2
    exit 1
fi

command -v python3 >/dev/null || { echo "python3 o'rnatilmagan" >&2; exit 1; }
python3 -c "import venv, ensurepip" 2>/dev/null || {
    echo "python3-venv kerak: apt install python3-venv" >&2
    exit 1
}

id "$APP_USER" &>/dev/null || useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
mkdir -p "$APP_DIR"

# Kodni nusxalash (.env, baza va venv saqlanib qoladi)
for f in bot.py config.py database.py keyboards.py quiz.py words.json requirements.txt; do
    install -m 644 "$SRC_DIR/$f" "$APP_DIR/$f"
done

[[ -d "$APP_DIR/.venv" ]] || python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

if [[ ! -f "$APP_DIR/.env" ]]; then
    install -m 600 /dev/null "$APP_DIR/.env"
    echo "TOKEN=" > "$APP_DIR/.env"
    echo "⚠️  $APP_DIR/.env yaratildi — ichiga TOKEN yozing, keyin: systemctl restart $SERVICE"
fi

chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod 600 "$APP_DIR/.env"

install -m 644 "$SRC_DIR/deploy/$SERVICE.service" "/etc/systemd/system/$SERVICE.service"
systemctl daemon-reload
systemctl enable "$SERVICE" >/dev/null

if grep -qE '^TOKEN=.+' "$APP_DIR/.env"; then
    systemctl restart "$SERVICE"
    sleep 2
    systemctl --no-pager --lines=5 status "$SERVICE" || true
else
    echo "Token yo'q — servis yoqildi, lekin ishga tushirilmadi."
fi
