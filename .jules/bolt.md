## 2025-05-18 - SkiaSharp P/Invoke Overhead in UI Loops
**Learning:** Native `SkiaSharp.SKBitmap.GetPixel(x, y)` incurs significant P/Invoke overhead when called repeatedly inside high-frequency UI events like `MouseMove` or tight loops. In C#, this can severely degrade UI responsiveness.
**Action:** When accessing individual pixels repeatedly, specifically on 32-bpp BGRA images, bypass `GetPixel` by utilizing `unsafe` direct pointer memory access via `SKBitmap.GetPixels().ToPointer()` combined with raw pointer arithmetic (e.g. `byte* pixelPtr = ptr + y * rowBytes + x * 4;`).
