#!/usr/bin/env pike
/*
Accept up to five arguments:
    text: displayed in center of icon,
    background-color: default white,
    text-color: default black,
    shape: displayed within a square,
    shape-color: default light grey
Produce four matching image.ico files in following sizes:
    16x16
    32x32
    48x48
    64x64
Enhancement: Also output a manifest.json file:
{
  "name": "",
  "short_name": "",
  "icons": [
    {
      "src": "/android-chrome-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/android-chrome-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ],
  "theme_color": "#ffffff",
  "background_color": "#ffffff",
  "display": "standalone"
}
*/

int main(int argc, array(string) argv) {
  if (has_value(argv, "--help")) {
    write("USAGE: %s [text] [bgcolor] [textcolor] [shape (circle, diamond, triangle)] [shapecolor]\n", basename(argv[0]));
    return 0;
  }
  constant IMAGE_SIZE = 64;
  [string text,
  string bgcolor,
  string textcolor,
  string shape,
  string shapecolor] = argv[1..] + ({"D", "#fff", "#000", "circle", "#bbb"})[argc-1..];

  // https://pike.lysator.liu.se/generated/manual/modref/ex/predef_3A_3A/Image/Color.html#Color
  array shapecol = Colors.parse_color(shapecolor); // RGB array
  Image.Image icon = Image.Image(64, 64, @Colors.parse_color(bgcolor));

  switch (shape) {
    case "circle":
      icon->setcolor(@shapecol);
      constant RADIUS = IMAGE_SIZE/2 - 1;
      constant RSQ = RADIUS ** 2;
      for (int x = 0; x < IMAGE_SIZE / 2; ++x)
        for (int y = 0; y < IMAGE_SIZE / 2; ++y)
          if (x*x + y*y < RSQ) {
            icon->setpixel(IMAGE_SIZE / 2 + x, IMAGE_SIZE / 2 + y); // lower right
            icon->setpixel(IMAGE_SIZE / 2 + x, IMAGE_SIZE / 2 - y); // upper right
            icon->setpixel(IMAGE_SIZE / 2 - x, IMAGE_SIZE / 2 + y); // lower left
            icon->setpixel(IMAGE_SIZE / 2 - x, IMAGE_SIZE / 2 - y); // upper left
          }
      break;
    case "none": case "square": break;
    default: exit(1, "Unrecognized shape %O\n", shape);
  }
  Stdio.write_file("favicon.png",Image.PNG.encode(icon));
}
