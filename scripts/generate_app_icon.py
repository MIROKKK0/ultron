from pathlib import Path
import cairosvg
source = Path("ios/Assets.xcassets/AppIcon.appiconset/AppIcon.svg")
target = source.with_name("AppIcon.png")
cairosvg.svg2png(url=str(source), write_to=str(target), output_width=1024, output_height=1024)
print(f"Generated {target} ({target.stat().st_size} bytes)")
