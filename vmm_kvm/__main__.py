import sys


def main():
    smoke = "--smoke" in sys.argv
    sys.argv = [a for a in sys.argv if a != "--smoke"]
    from .main import run
    sys.exit(run(smoke=smoke))


if __name__ == "__main__":
    main()
