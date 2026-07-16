## 2025-05-18 - SkiaSharp P/Invoke Overhead in UI Loops
**Learning:** Native `SkiaSharp.SKBitmap.GetPixel(x, y)` incurs significant P/Invoke overhead when called repeatedly inside high-frequency UI events like `MouseMove` or tight loops. In C#, this can severely degrade UI responsiveness.
**Action:** When accessing individual pixels repeatedly, specifically on 32-bpp BGRA images, bypass `GetPixel` by utilizing `unsafe` direct pointer memory access via `SKBitmap.GetPixels().ToPointer()` combined with raw pointer arithmetic (e.g. `byte* pixelPtr = ptr + y * rowBytes + x * 4;`).

## $(date +%Y-%m-%d) - Optimization of numpy array caching for cv2.inRange
**Learning:** In high-frequency computer vision loops involving color filtering, manually maintaining a dictionary cache for OpenCV `inRange` boundaries (numpy arrays) introduces unnecessary Python-level overhead (dictionary lookups, hashing).
**Action:** Extract the bounds-generation logic into a helper function handling standard types, and use Python's built-in `@lru_cache` to offload the caching layer to highly optimized C code, avoiding the manual dictionary completely. Unhashable items like `list` can be safely cast to `tuple` before calling the cached function.
