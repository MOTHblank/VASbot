## 2025-05-18 - SkiaSharp P/Invoke Overhead in UI Loops
**Learning:** Native `SkiaSharp.SKBitmap.GetPixel(x, y)` incurs significant P/Invoke overhead when called repeatedly inside high-frequency UI events like `MouseMove` or tight loops. In C#, this can severely degrade UI responsiveness.
**Action:** When accessing individual pixels repeatedly, specifically on 32-bpp BGRA images, bypass `GetPixel` by utilizing `unsafe` direct pointer memory access via `SKBitmap.GetPixels().ToPointer()` combined with raw pointer arithmetic (e.g. `byte* pixelPtr = ptr + y * rowBytes + x * 4;`).
## 2025-05-18 - NumPy Array Construction Loop Overhead
**Learning:** In Python, when constructing a large list of lists (like bounding boxes for NMS) from individual NumPy arrays (like x and y coordinates), using a native `for` loop with `zip()` and `.append()` incurs massive method lookup and interpreter overhead.
**Action:** When converting multiple separate NumPy arrays into a structured list of lists, use `np.column_stack(...)` followed by `.tolist()`. This provides a massive speedup by utilizing C-level vectorization before converting to native Python types.
