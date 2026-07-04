## $(date +%Y-%m-%d) - Optimize BitBlt screenshot conversion
**Learning:** In C# when converting from `System.Drawing.Bitmap` to `SkiaSharp.SKBitmap`, using `MemoryStream` to save and re-decode an image is very slow and allocation-heavy. `VASbot.Gui` allows `unsafe` code.
**Action:** Use `Bitmap.LockBits` and a direct `Buffer.MemoryCopy` with `BitmapData.Scan0` to bypass encoding/decoding overhead. This is a critical codebase-specific performance pattern for any C# graphics interop.
