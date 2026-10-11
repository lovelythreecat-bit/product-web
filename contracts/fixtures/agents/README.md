# TEST_ONLY Agent fixtures

These are locally synthesized solid terracotta color samples, not model outputs or public customer cases.
The PNG is 32×32. The MP4 is a silent one-second, two-frame H.264 constrained-baseline video in yuv420p.
They have no external source or credentials. `mock_server.py` embeds the exact bytes so Compose can
continue mounting only that script. The checked-in fixture files are provenance and comparison inputs.

Generated locally with FFmpeg 8.1.2, without network or Agent calls:

```powershell
ffmpeg -f lavfi -i 'color=c=0xb76e4b:s=32x32:d=1:r=2' -frames:v 1 -c:v png -fflags +bitexact -flags:v +bitexact -update 1 TEST_ONLY-orange.png
ffmpeg -f lavfi -i 'color=c=0xb76e4b:s=32x32:d=1:r=2' -an -c:v libx264 -profile:v baseline -level 3.0 -pix_fmt yuv420p -movflags +faststart -fflags +bitexact -flags:v +bitexact -map_metadata -1 TEST_ONLY-orange.mp4
```

The contract tests retrieve the bytes over real HTTP, compare MIME, SHA-256 and length, check PNG
chunks/decompression and MP4 box structure, and decode the HTTP bytes with local FFmpeg when installed.
No runtime FFmpeg dependency is needed to serve the fixed bytes. Actual Agent quality and D-01/D-04
production acceptance remain unconfirmed. Partial fixtures keep `complete=false` and a missing item.
