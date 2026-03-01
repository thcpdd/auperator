"""Auperator CLI"""

import typer

from .collector.cli import app as collector_app

app = typer.Typer(help="Auperator - 智能运维 Agent")

app.add_typer(collector_app, name="collector", help="日志采集器")


def main():
    """CLI 入口点"""
    app()


if __name__ == "__main__":
    main()
