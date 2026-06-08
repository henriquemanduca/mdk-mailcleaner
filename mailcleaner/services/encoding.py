import base64
import binascii


def encode_base64(text: str) -> str:
    encoded_bytes = base64.b64encode(text.encode("utf-8"))
    return encoded_bytes.decode("utf-8")


def decode_base64(encoded_text: str) -> str:
    try:
        decoded_bytes = base64.b64decode(encoded_text, validate=True)
        return decoded_bytes.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise ValueError("invalid base64 content") from exc
