"""独立机器人进程入口：python -m app.qq_bot_worker。"""

from app.services.qq_bot.worker import main

if __name__ == "__main__":
    main()
