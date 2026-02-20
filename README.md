
# Telegram Server & Docker Monitor Bot

Бот для Telegram, который присылает в указанную тему группы статус сервера (CPU, RAM, HDD) и Docker-контейнеров, а также отправляет критические уведомления при перегрузке или недоступности Docker.

## Возможности

- Периодический отчёт о состоянии сервера:
  - загрузка CPU;
  - использование RAM;
  - использование диска.
- Статус Docker:
  - количество контейнеров (всего / running / stopped);
  - список контейнеров с кратким статусом.
- Критические уведомления:
  - превышение порогов CPU/RAM/HDD;
  - падение Docker и последующее восстановление.
- Отправка всех сообщений в конкретную тему (topic) внутри супергруппы.

## Требования

- Python 3.11+ (поддерживается и 3.13).
- Linux (тестировалось на Ubuntu).
- Установленный Docker и запущенный Docker daemon.
- Созданный Telegram-бот (через BotFather).
- Супергруппа в Telegram с включёнными темами.

## Установка на Ubuntu

### 1. Подготовка системы

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

Убедитесь, что Docker установлен и работает:

```bash
docker ps
```

Если бот будет запускаться не от root, добавьте пользователя в группу `docker`:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Клонирование репозитория

```bash
cd ~
git clone https://github.com/USERNAME/REPO_NAME.git
cd REPO_NAME
```

Замените `USERNAME/REPO_NAME` на свои.

### 3. Создание виртуального окружения и установка зависимостей

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Настройка .env

Создайте файл `.env` в корне проекта:

```env
BOT_TOKEN=ТОКЕН_ОТ_BOTFATHER
CHAT_ID=-100XXXXXXXXXXXXXX
UPDATE_INTERVAL=30

CPU_CRIT=90
RAM_CRIT=90
DISK_CRIT=90
CRIT_CONFIRM_CYCLES=3
```

Где:

- `BOT_TOKEN` — токен бота от BotFather.  
- `CHAT_ID` — ID супергруппы (можно получить через специальных ботов или лог `getUpdates`).  
- `UPDATE_INTERVAL` — интервал обновления статуса в секундах.  
- `CPU_CRIT`, `RAM_CRIT`, `DISK_CRIT` — пороги для критических алертов, в процентах.  
- `CRIT_CONFIRM_CYCLES` — сколько циклов подряд метрика должна быть выше порога, чтобы отправить алерт.

### 5. Получение CHAT_ID

1. Добавьте бота в нужную группу.  
2. Напишите любое сообщение.  
3. Используйте бота `@RawDataBot` или `@getidsbot` — он покажет `chat_id` группы.  

Для супергрупп `chat_id` обычно имеет вид `-100XXXXXXXXXXXXXX`.

### 6. Первый запуск

```bash
cd ~/REPO_NAME
source venv/bin/activate
python bot.py
```

В Telegram:

1. Включите темы в группе (если ещё не включены).  
2. Создайте тему, например `#Server`.  
3. В этой теме отправьте команду `/bind_here` — бот привяжет `message_thread_id`.  
4. В той же теме отправьте `/status` — должен прийти блок со статусом сервера и Docker.

Если всё работает — переходите к автозапуску.

## Автозапуск через systemd

Создайте сервис:

```bash
sudo nano /etc/systemd/system/serverbot.service
```

Пример содержимого:

```ini
[Unit]
Description=Telegram server monitor bot
After=network-online.target docker.service
Wants=network-online.target docker.service

[Service]
Type=simple
User=USERNAME
WorkingDirectory=/home/USERNAME/REPO_NAME
ExecStart=/home/USERNAME/REPO_NAME/venv/bin/python /home/USERNAME/REPO_NAME/bot.py

Restart=always
RestartSec=10
TimeoutStopSec=20
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

Замените `USERNAME` и `REPO_NAME` на свои.

Активируйте сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable serverbot.service
sudo systemctl start serverbot.service
```

Проверка:

```bash
sudo systemctl status serverbot.service
journalctl -u serverbot.service -f
```

## Структура проекта

```text
.
├─ bot.py
├─ monitor.py
├─ config.py
├─ requirements.txt
├─ .env              # не коммитится в Git
└─ topic.txt         # создаётся ботом
```

## Разработка и тестирование локально

- Можно запускать `python bot.py` на локальной машине (long polling, без вебхуков).  
- Для теста удобно завести отдельного «тестового» бота и отдельную тестовую группу.
```