## $(date +%Y-%m-%d) - Optimize BitBlt screenshot conversion
**Learning:** In C# when converting from `System.Drawing.Bitmap` to `SkiaSharp.SKBitmap`, using `MemoryStream` to save and re-decode an image is very slow and allocation-heavy. `VASbot.Gui` allows `unsafe` code.
**Action:** Use `Bitmap.LockBits` and a direct `Buffer.MemoryCopy` with `BitmapData.Scan0` to bypass encoding/decoding overhead. This is a critical codebase-specific performance pattern for any C# graphics interop.
## $(date +%Y-%m-%d) - Optimize SKBitmap Pixel Access
**Learning:** In C#, using `SKBitmap.GetPixel(x, y)` inside a tight rendering loop is incredibly slow due to virtual method overhead and per-pixel bounds checking. The `VASbot.Gui` allows `unsafe` blocks.
**Action:** Always replace nested loops using `GetPixel(x, y)` on `SKBitmap` with direct memory pointer access (`unsafe` block + `GetPixels().ToPointer()`). Always validate `BytesPerPixel` (e.g., `== 4`) before performing pointer arithmetic.
