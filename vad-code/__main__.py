from time import sleep


class AIOSBridge:
    def run(self) -> None:
        while True:
            sleep(0.1)


if __name__ == '__main__':
    try:
        bridge = AIOSBridge()
        bridge.run()
    except KeyboardInterrupt:
        print('\n\n👋 Выход из системы...')
