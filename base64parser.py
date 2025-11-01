import argparse
import base64
import sys

def encode_to_base64(clear_text):
    return base64.b64encode(clear_text.encode()).decode()

def decode_from_base64(base64_text):
    return base64.b64decode(base64_text.encode()).decode()

def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-e', '--encode', action='store_true')
    group.add_argument('-d', '--decode', action='store_true')
    args = parser.parse_args()

    input_text = ''
    for line in sys.stdin:
        input_text += line
    input_text = input_text.strip()
    result = ''
    if args.encode:
        result = encode_to_base64(input_text)
    elif args.decode:
        result = decode_from_base64(input_text)

    sys.stdout.write(result)

if __name__ == '__main__':
    main()
