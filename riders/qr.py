from io import BytesIO

import qrcode
import qrcode.image.svg


def qr_svg(data):
    """Return a QR code for `data` as an inline <svg> string (no image files)."""
    image = qrcode.make(
        data, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=1
    )
    buffer = BytesIO()
    image.save(buffer)
    svg = buffer.getvalue().decode("utf-8")
    return svg[svg.index("<svg"):]  # drop the XML header so it embeds in HTML
