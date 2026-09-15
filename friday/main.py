"""Friday 入口。"""

from friday.delivery.cli import main as cli_main


def main(argv: list[str] | None = None) -> int:
    """程序入口：默认走 CLI。"""
    return cli_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
