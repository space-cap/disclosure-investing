from app.main import cmd_fetch_disclosures


class Args:
    date = None


if __name__ == "__main__":
    cmd_fetch_disclosures(Args())

