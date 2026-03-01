"""Generate favicon.ico from the SVG favicon.
Run: python generate_favicon.py
Requires: pip install Pillow cairosvg
"""
import struct
import io

def create_simple_ico():
    """Create a minimal 32x32 favicon.ico with a ballot box icon."""
    size = 32
    
    # Create pixel data for a 32x32 image (BGRA format for ICO)
    pixels = bytearray(size * size * 4)
    
    def set_pixel(x, y, r, g, b, a=255):
        if 0 <= x < size and 0 <= y < size:
            idx = (y * size + x) * 4
            pixels[idx] = b      # Blue
            pixels[idx+1] = g    # Green
            pixels[idx+2] = r    # Red
            pixels[idx+3] = a    # Alpha
    
    def fill_circle(cx, cy, radius, r, g, b):
        for y in range(size):
            for x in range(size):
                dx = x - cx
                dy = y - cy
                if dx*dx + dy*dy <= radius*radius:
                    # Gradient from blue to red
                    t = x / size
                    cr = int(30 + (220-30) * t)   # 1E -> DC
                    cg = int(144 + (20-144) * t)  # 90 -> 14
                    cb = int(255 + (60-255) * t)   # FF -> 3C
                    set_pixel(x, y, cr, cg, cb)
    
    def fill_rect(x1, y1, x2, y2, r, g, b, a=255):
        for y in range(y1, y2):
            for x in range(x1, x2):
                set_pixel(x, y, r, g, b, a)
    
    # Background circle (blue-to-red gradient)
    fill_circle(16, 16, 15, 0, 0, 0)
    
    # Ballot box body (white)
    fill_rect(8, 14, 24, 25, 255, 255, 255)
    
    # Ballot slot
    fill_rect(11, 13, 21, 15, 255, 255, 255)
    fill_rect(13, 13, 19, 14, 60, 60, 60)
    
    # Ballot paper
    fill_rect(12, 6, 20, 14, 245, 245, 245)
    
    # Checkmark (green) - simple V shape
    for i in range(3):
        set_pixel(13+i, 10+i, 46, 125, 50)
        set_pixel(14+i, 10+i, 46, 125, 50)
    for i in range(4):
        set_pixel(16+i, 12-i, 46, 125, 50)
        set_pixel(17+i, 12-i, 46, 125, 50)
    
    # Star (gold) at center of box
    star_cx, star_cy = 16, 20
    set_pixel(star_cx, star_cy-2, 255, 215, 0)
    set_pixel(star_cx, star_cy-1, 255, 215, 0)
    set_pixel(star_cx, star_cy, 255, 215, 0)
    set_pixel(star_cx, star_cy+1, 255, 215, 0)
    set_pixel(star_cx-1, star_cy, 255, 215, 0)
    set_pixel(star_cx+1, star_cy, 255, 215, 0)
    set_pixel(star_cx-2, star_cy-1, 255, 215, 0)
    set_pixel(star_cx+2, star_cy-1, 255, 215, 0)
    set_pixel(star_cx-1, star_cy+1, 255, 215, 0)
    set_pixel(star_cx+1, star_cy+1, 255, 215, 0)
    
    # Build ICO file
    ico = io.BytesIO()
    
    # ICO Header
    ico.write(struct.pack('<HHH', 0, 1, 1))  # Reserved, Type (ICO), Count
    
    # ICO Directory Entry
    bmp_size = 40 + len(pixels) + (size * size // 8)  # header + pixels + mask
    ico.write(struct.pack('<BBBBHHII',
        size if size < 256 else 0,  # Width
        size if size < 256 else 0,  # Height
        0,    # Color palette
        0,    # Reserved
        1,    # Color planes
        32,   # Bits per pixel
        bmp_size,  # Size of BMP data
        22    # Offset to BMP data (6 header + 16 directory)
    ))
    
    # BMP Info Header (BITMAPINFOHEADER)
    ico.write(struct.pack('<IiiHHIIiiII',
        40,           # Header size
        size,         # Width
        size * 2,     # Height (doubled for ICO format)
        1,            # Planes
        32,           # Bits per pixel
        0,            # Compression
        0,            # Image size
        0,            # X pixels per meter
        0,            # Y pixels per meter
        0,            # Colors used
        0             # Important colors
    ))
    
    # Pixel data (bottom-up for BMP)
    for y in range(size - 1, -1, -1):
        for x in range(size):
            idx = (y * size + x) * 4
            ico.write(bytes([pixels[idx], pixels[idx+1], pixels[idx+2], pixels[idx+3]]))
    
    # AND mask (transparency mask, all zeros = fully opaque where alpha says so)
    mask_row_size = ((size + 31) // 32) * 4
    for y in range(size):
        row = bytearray(mask_row_size)
        for x in range(size):
            idx = ((size - 1 - y) * size + x) * 4
            if pixels[idx+3] == 0:  # If alpha is 0, set mask bit
                row[x // 8] |= (0x80 >> (x % 8))
        ico.write(bytes(row))
    
    return ico.getvalue()

if __name__ == '__main__':
    ico_data = create_simple_ico()
    
    # Write to public folder
    with open('public/favicon.ico', 'wb') as f:
        f.write(ico_data)
    print(f"Created public/favicon.ico ({len(ico_data)} bytes)")
