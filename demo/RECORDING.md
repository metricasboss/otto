# 🎬 Recording OTTO Demo GIF

## Quick Start (Easiest)

```bash
# 1. Install asciinema
brew install asciinema  # macOS
# or
sudo apt install asciinema  # Linux

# 2. Record demo
cd demo
asciinema rec otto-demo.cast -c "./demo_script.sh"

# 3. Upload to asciinema (creates shareable link)
asciinema upload otto-demo.cast

# 4. Embed in README
# Copy the URL and use:
# [![asciicast](https://asciinema.org/a/XXXXX.svg)](https://asciinema.org/a/XXXXX)
```

---

## Convert to GIF (Better for README)

### Install agg
```bash
# Via cargo (Rust)
cargo install --git https://github.com/asciinema/agg

# Or download from: https://github.com/asciinema/agg/releases
```

### Convert
```bash
agg otto-demo.cast otto-demo.gif \
  --theme monokai \
  --font-size 16 \
  --speed 1.5 \
  --cols 80 \
  --rows 30
```

### Add to README
```bash
# Move GIF to docs
mkdir -p ../docs
mv otto-demo.gif ../docs/

# Commit
git add ../docs/otto-demo.gif
git commit -m "docs: add demo GIF"
git push
```

### Reference in README
```markdown
![OTTO Demo](docs/otto-demo.gif)
```

---

## Alternative: Screen Recording

### macOS (QuickTime)
1. Open QuickTime → File → New Screen Recording
2. Select area around terminal
3. Run `./demo_script.sh`
4. Stop recording → Save as `otto-demo.mov`
5. Convert to GIF:
```bash
brew install gifski
ffmpeg -i otto-demo.mov -f image2pipe -vcodec ppm - | \
  gifski --fps 10 --width 800 -o otto-demo.gif -
```

### Linux (Peek)
```bash
# Install
sudo apt install peek

# Use GUI to record
peek
```

---

## Optimal GIF Settings

**For GitHub README:**
- Width: 800px
- Duration: 20-30s
- FPS: 10-15
- Size: < 5MB

---

## What to Show in Demo

✅ **Good flow:**
1. Dev writes code (with AI)
2. OTTO scans → finds violations
3. Shows specific issues + fines
4. Dev fixes based on suggestions
5. OTTO approves → commit safe
6. Show total fines avoided

❌ **Avoid:**
- Too fast (can't read)
- Too long (>40s)
- Small fonts
- Complex commands

---

## Test Your Demo

```bash
# Run script to preview
./demo_script.sh

# Adjust timing in script if needed
# Then record when happy
```

---

Need help? Open an issue: https://github.com/metricasboss/otto/issues
