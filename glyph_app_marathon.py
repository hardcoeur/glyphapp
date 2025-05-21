import gi
import cairo
import random
from PIL import Image
from datetime import datetime


gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, Gdk, Gio, Pango, PangoCairo

GLYPH_OVERRIDE = {
    #CEFJMOPQTUVWjkl&/
    'BOX': ['C', 'E', 'F','J','M','O','P','Q','T','U','V','W','j','k','l','&','/','¤','q'],
    #'BOX': ['F', '%', '&','/','(',')','H','I','J','K','L','N','O','P','Q','Å','Ä','Ö','q'],
    'DOT': ['G', 'J','K','L','Q','Y','9'],
    'SYMBOL': ['C', 'D', 'E', 'F','¤'],
    'LIGHT': ['•', '.','r','4','d','c','Z','Ö','%','5','6','s','I']
}

class HybridGlyphCanvas(Gtk.DrawingArea):
    def __init__(self, image_path, font_size=20, font_family="GlyphFont"):
        super().__init__()
        self.image_path = image_path
        self.font_size = font_size
        self.font_family = font_family
        self.show_bands = False
        self.ascii_output = []
        self.scale_factor = 1.0
        self.transparent_background = True
        self.cols = 0
        self.rows = 0
        self.cell_width = 0
        self.cell_height = 0
        self.set_draw_func(self.on_draw)
        self.set_image(image_path)

    def set_image(self, path):
        self.image_path = path

        try:
            img = Image.open(self.image_path).convert("L")
            self.image_width, self.image_height = img.size
        except Exception as e:
            print("Image load error:", e)
            return

        layout_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1)
        layout_cr = cairo.Context(layout_surface)
        layout = PangoCairo.create_layout(layout_cr)
        layout.set_font_description(Pango.FontDescription(f"{self.font_family},{int(self.font_size * self.scale_factor)}"))
        layout.set_text("▣", -1)
        _, logical_rect = layout.get_extents()
        glyph_width = logical_rect.width / Pango.SCALE * 1
        glyph_height = logical_rect.height / Pango.SCALE * 1

        self.cell_width = int(glyph_width)
        self.cell_height = int(glyph_height)
        self.cols = self.image_width // self.cell_width
        self.rows = self.image_height // self.cell_height

        self.set_content_width(self.cols * self.cell_width)
        self.set_content_height(self.rows * self.cell_height)
        self.queue_draw()

    def set_font(self, family, size):
        self.font_family = family
        self.font_size = size
        self.set_image(self.image_path)

    def set_scale(self, scale):
        self.scale_factor = scale
        self.set_image(self.image_path)

    def brightness_to_glyph(self, brightness):
        if brightness < 98:
            return random.choice(GLYPH_OVERRIDE['BOX'])
        elif brightness < 128:
            return random.choice(GLYPH_OVERRIDE['DOT'])
        elif brightness < 200:
            return random.choice(GLYPH_OVERRIDE['SYMBOL'])
        else:
            return random.choice(GLYPH_OVERRIDE['LIGHT'])

    def on_draw(self, area, cr, width, height, *, export_mode=False):
        self.ascii_output = []

        if export_mode and self.transparent_background:
            cr.set_source_rgba(0, 0, 0, 0)
            cr.set_operator(cairo.OPERATOR_SOURCE)
            cr.paint()
            cr.set_operator(cairo.OPERATOR_OVER)
        else:
            cr.set_source_rgb(0.7608, 0.9961, 0.0431)
            cr.paint()

        try:
            img = Image.open(self.image_path).convert("L")
            pixels = img.load()
        except Exception as e:
            print("Image load error:", e)
            return

        for row in range(self.rows):
            line = ''
            for col in range(self.cols):
                cell_x0 = col * self.cell_width
                cell_y0 = row * self.cell_height
                brightness_sum = 0
                count = 0

                for y in range(cell_y0, min(cell_y0 + self.cell_height, self.image_height)):
                    for x in range(cell_x0, min(cell_x0 + self.cell_width, self.image_width)):
                        brightness_sum += pixels[x, y]
                        count += 1

                avg_brightness = brightness_sum // max(1, count)
                glyph = self.brightness_to_glyph(avg_brightness)

                layout = PangoCairo.create_layout(cr)
                layout.set_font_description(Pango.FontDescription(f"{self.font_family},{int(self.font_size * self.scale_factor)}"))
                layout.set_text(glyph, -1)
                _, logical_rect = layout.get_extents()
                w = logical_rect.width / Pango.SCALE
                h = logical_rect.height / Pango.SCALE

                x = col * self.cell_width + (self.cell_width - w) / 2
                y = row * self.cell_height + (self.cell_height - h) / 2

                cr.set_source_rgb(0, 0, 0)
                cr.move_to(x, y)
                PangoCairo.show_layout(cr, layout)
                line += glyph
            self.ascii_output.append(line)

    def export_to_png(self):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.cols * self.cell_width, self.rows * self.cell_height)
        cr = cairo.Context(surface)
        self.on_draw(self, cr, self.cols * self.cell_width, self.rows * self.cell_height, export_mode=True)
        filename = f"glyph_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        surface.write_to_png(filename)
        print(f"Exported PNG: {filename}")

    def export_to_svg(self):
        filename = f"glyph_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.svg"
        surface = cairo.SVGSurface(filename, self.cols * self.cell_width, self.rows * self.cell_height)
        cr = cairo.Context(surface)

        if self.transparent_background:
            cr.set_source_rgba(0, 0, 0, 0)
            cr.set_operator(cairo.OPERATOR_SOURCE)
            cr.paint()
            cr.set_operator(cairo.OPERATOR_OVER)
        else:
            cr.set_source_rgb(1.0, 1.0, 0.8)
            cr.paint()

        try:
            img = Image.open(self.image_path).convert("L")
            pixels = img.load()
        except Exception as e:
            print("Image load error:", e)
            return

        for row in range(self.rows):
            for col in range(self.cols):
                cell_x0 = col * self.cell_width
                cell_y0 = row * self.cell_height
                brightness_sum = 0
                count = 0

                for y in range(cell_y0, min(cell_y0 + self.cell_height, self.image_height)):
                    for x in range(cell_x0, min(cell_x0 + self.cell_width, self.image_width)):
                        brightness_sum += pixels[x, y]
                        count += 1

                avg_brightness = brightness_sum // max(1, count)
                glyph = self.brightness_to_glyph(avg_brightness)

                layout = PangoCairo.create_layout(cr)
                layout.set_font_description(Pango.FontDescription(f"{self.font_family},{int(self.font_size * self.scale_factor)}"))
                layout.set_text(glyph, -1)
                _, logical_rect = layout.get_extents()
                w = logical_rect.width / Pango.SCALE
                h = logical_rect.height / Pango.SCALE

                x = col * self.cell_width + (self.cell_width - w) / 2
                y = row * self.cell_height + (self.cell_height - h) / 2

                cr.save()
                cr.translate(x, y)
                PangoCairo.layout_path(cr, layout)
                cr.set_source_rgb(0, 0, 0)
                cr.fill()
                cr.restore()

        surface.finish()
        print(f"Exported SVG: {filename}")

    def export_to_ascii(self):
        filename = f"glyph_ascii_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.ascii_output))
        print(f"Exported ASCII: {filename}")


class HybridGlyphWindow(Gtk.ApplicationWindow):
    def __init__(self, app, image_path):
        super().__init__(application=app)
        self.set_title("Glyph Mapper")
        self.set_default_size(800, 600)

        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.set_child(outer)

        control = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        control.set_size_request(240, -1)
        outer.append(control)

        self.font_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 8, 40, 1)
        self.font_scale.set_value(20)
        self.font_scale.set_hexpand(True)
        control.append(Gtk.Label(label="Font Size"))
        control.append(self.font_scale)

        self.zoom_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.25, 3.0, 0.05)
        self.zoom_scale.set_value(1.0)
        self.zoom_scale.set_hexpand(True)
        control.append(Gtk.Label(label="Zoom Scale"))
        control.append(self.zoom_scale)

        self.font_selector = Gtk.ComboBoxText()
        for name in ["GlyphFont", "Segoe UI Emoji", "DejaVu Sans Mono", "Sans"]:
            self.font_selector.append_text(name)
        self.font_selector.set_active(0)
        control.append(Gtk.Label(label="Font Family"))
        control.append(self.font_selector)

        self.toggle_transparency = Gtk.CheckButton(label="Transparent Background")
        self.toggle_transparency.set_active(True)
        control.append(self.toggle_transparency)

        self.export_png_button = Gtk.Button(label="Export PNG")
        self.export_svg_button = Gtk.Button(label="Export SVG")
        self.export_txt_button = Gtk.Button(label="Export ASCII")
        btn_box = Gtk.Box(spacing=6)
        btn_box.append(self.export_png_button)
        btn_box.append(self.export_svg_button)
        btn_box.append(self.export_txt_button)
        control.append(btn_box)

        self.canvas = HybridGlyphCanvas(image_path)
        outer.append(self.canvas)

        self.font_scale.connect("value-changed", self.update_canvas)
        self.zoom_scale.connect("value-changed", self.update_canvas)
        self.font_selector.connect("changed", self.update_canvas)
        self.toggle_transparency.connect("toggled", self.update_canvas)
        self.export_png_button.connect("clicked", self.on_export_png)
        self.export_svg_button.connect("clicked", self.on_export_svg)
        self.export_txt_button.connect("clicked", self.on_export_txt)

        drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        drop_target.connect("drop", self.on_file_dropped)
        self.canvas.add_controller(drop_target)

    def update_canvas(self, *args):
        font_family = self.font_selector.get_active_text()
        font_size = int(self.font_scale.get_value())
        zoom = self.zoom_scale.get_value()
        self.canvas.transparent_background = self.toggle_transparency.get_active()
        self.canvas.set_font(font_family, font_size)
        self.canvas.set_scale(zoom)

    def on_export_png(self, button):
        self.canvas.export_to_png()

    def on_export_svg(self, button):
        self.canvas.export_to_svg()

    def on_export_txt(self, button):
        self.canvas.export_to_ascii()

    def on_file_dropped(self, drop_target, file, x, y):
        path = file.get_path()
        if path:
            print(f"Dropped: {path}")
            self.canvas.set_image(path)
        return True

class HybridGlyphApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.example.GlyphMapper")

    def do_activate(self):
        import sys
        if len(sys.argv) < 2:
            print("Usage: python glyph_app.py path_to_image")
            self.quit()
            return

        win = HybridGlyphWindow(self, sys.argv[1])
        win.present()

if __name__ == "__main__":
    app = HybridGlyphApp()
    app.run()