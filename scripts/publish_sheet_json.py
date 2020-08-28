import argparse
from util.publish_google_sheet import SheetPublishHandler

parser = argparse.ArgumentParser()
parser.add_argument('-t', '--title')
parser.add_argument('-j', '--json_file')

if __name__ == "__main__":
    args = parser.parse_args()

    handler = SheetPublishHandler()
    handler.load_and_publish(json_file=args.json_file, title=args.title)
    print(f"Published {args.title}")